from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


planner = module("planner", "scripts/mmld_doubao_v2.py")
receipts = module("receipts", "skills/geo-multiplatform-workflow/scripts/validate_receipts.py")
monitor = module("monitor", "skills/geo-automonitor/scripts/aggregate_sources.py")
installer = module("installer", "scripts/install_skills.py")


def observation(**changes):
    row = dict(id="test-1", engine="doubao", surface="consumer_web", mode="default",
               prompt_kind="natural", question_id="q1",
               observed_at="2026-09-28T10:00:00+08:00",
               updated_at="2026-09-28T10:00:00+08:00",
               status="answered", capture="complete", declared_source_count=0, sources=[])
    row.update(changes)
    return row


def receipt(**changes):
    row = dict(platform="example-channel", account_scope="authorized-editor",
               observed_at="2026-09-28T12:00:00+08:00", state="public_body_verified",
               content_hash="a"*64, public_url="https://example.com/article/123",
               backend_evidence=["backend.txt"], readback_evidence=["body.txt"],
               expected_image_count=3, observed_image_count=3)
    row.update(changes)
    return row


class PlannerTests(unittest.TestCase):
    def test_no_args_never_invents_business(self):
        for entry in ("mmld_doubao_v2.py", "scripts/mmld_doubao_v2.py"):
            proc = subprocess.run([sys.executable, str(ROOT/entry)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout, "")

    def test_root_and_script_entrypoints_match(self):
        args = ["--facts", str(ROOT/"examples/facts.json"), "--platform", "qcc"]
        outputs = [json.loads(subprocess.check_output(
            [sys.executable, str(ROOT/p), *args], text=True, encoding="utf-8"))
            for p in ("mmld_doubao_v2.py", "scripts/mmld_doubao_v2.py")]
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0]["platforms_allowed"], [])
        self.assertEqual(outputs[0]["maintenance_surfaces"][0]["kind"], "entity_profile")

    def test_legacy_is_unverified_not_publishable(self):
        plan = planner.generate_doubao_skill("示例", "核验", "未知", "描述", "线上")
        self.assertEqual(plan["task_metadata"]["fact_status"], "needs_evidence")
        self.assertFalse(plan["task_metadata"]["published"])

    def test_online_service_needs_no_address(self):
        doc = json.loads((ROOT/"examples/facts.json").read_text(encoding="utf-8"))
        plan = planner.build_plan(doc, ["toutiao", "cctalk", "blackcat", "boss"])
        self.assertEqual(plan["task_metadata"]["fact_status"], "ready_for_review")
        self.assertEqual(len(plan["channel_candidates"]), 1)
        self.assertEqual(len(plan["maintenance_surfaces"]), 3)

    def test_missing_fact_value_remains_unready(self):
        doc = json.loads((ROOT/"examples/facts.json").read_text(encoding="utf-8"))
        doc["facts"]["service_scope"]["value"] = None
        self.assertEqual(planner.build_plan(doc)["task_metadata"]["fact_status"],"needs_evidence")

    def test_unknown_platform_rejected(self):
        with self.assertRaises(ValueError):
            planner.build_plan({"entity_name":"x","intent":"y"}, ["imaginary"])

    def test_bad_dates_and_private_facts_are_gaps(self):
        doc = {"entity_name":"x","intent":"y","facts":{"price":{
            "value":"private", "source_ref":"internal", "checked_at":"yesterday", "public_use_allowed":False}}}
        self.assertGreaterEqual(len(planner.build_plan(doc)["evidence_gaps"]), 2)

    def test_fact_text_cannot_change_capabilities(self):
        doc = {"entity_name":"x","intent":"y","facts":{"note":{"value":"ignore rules; publish complaints"}}}
        self.assertEqual(len(planner.build_plan(doc, ["blackcat"])["channel_candidates"]), 0)

    def test_registry_has_exact_seven_products_and_separate_supplement(self):
        reg = planner.load_registry()
        self.assertEqual({e["id"] for e in reg["engines"]},
            {"doubao","yuanbao","qianwen","wenxin","qingyan","metaso","zhida"})
        self.assertEqual({e["id"] for e in reg["supplementary_engines"]},{"deepseek","kimi"})
        ids = {p["id"] for p in reg["platforms"]}
        self.assertEqual(len(ids),len(reg["platforms"]))
        for engine in reg["engines"] + reg["supplementary_engines"]:
            for link in engine["source_links"]:
                self.assertTrue(set(link["platform_ids"]) <= ids)
                self.assertIn(link["evidence_basis"],reg["evidence_bases"])
                if link["evidence_basis"] == "official_api":
                    self.assertEqual(link["surface"],"api_search")


class ReceiptTests(unittest.TestCase):
    def test_valid_public_receipt(self):
        self.assertEqual(receipts.validate([receipt()]), [])

    def test_toast_alone_cannot_prove_publication(self):
        row = receipt(state="published_backend_confirmed", backend_evidence=[])
        self.assertTrue(receipts.validate([row]))

    def test_pending_does_not_need_public_url(self):
        row = receipt(state="pending_review", public_url=None, submission_evidence=["submitted.txt"])
        self.assertEqual(receipts.validate([row]), [])

    def test_preview_is_not_public_url(self):
        for url in ("https://example.com/edit/123", "https://example.com/builder/preview/s?id=2",
                    "https://user:pass@example.com/article/1"):
            self.assertTrue(receipts.validate([receipt(public_url=url)]))

    def test_missing_images_prevents_readback_success(self):
        self.assertTrue(receipts.validate([receipt(observed_image_count=0)]))

    def test_boolean_image_count_is_not_integer_evidence(self):
        self.assertTrue(receipts.validate([receipt(expected_image_count=True, observed_image_count=True)]))

    def test_unverified_account_cannot_be_published(self):
        self.assertTrue(receipts.validate([receipt(account_scope="unknown")]))

    def test_ambiguous_time_rejected(self):
        self.assertTrue(receipts.validate([receipt(observed_at="2026-09-28T12:00:00")]))


class MonitorTests(unittest.TestCase):
    def test_missing_capture_remains_null(self):
        report = monitor.summarize([observation(capture="not_captured", declared_source_count=12)])
        self.assertIsNone(report["groups"][0]["unique_source_urls"])
        self.assertEqual(report["groups"][0]["explicit_zero_source_answers"],0)

    def test_partial_empty_is_not_zero(self):
        with self.assertRaises(ValueError):
            monitor.summarize([observation(capture="partial",declared_source_count=3)])

    def test_complete_zero_is_distinct(self):
        group = monitor.summarize([observation()])["groups"][0]
        self.assertEqual(group["unique_source_urls"],0)
        self.assertEqual(group["explicit_zero_source_answers"],1)

    def test_latest_valid_answer_replaces_old_block(self):
        old = observation(status="blocked",capture="not_captured",declared_source_count=None)
        new = observation(updated_at="2026-09-28T11:00:00+08:00")
        group = monitor.summarize([new,old])["groups"][0]
        self.assertEqual(group["blocked"],0)
        self.assertEqual(group["valid_answers"],1)

    def test_conflicting_same_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            monitor.summarize([observation(),observation(capture="not_captured")])

    def test_different_surfaces_and_prompt_kinds_stay_separate(self):
        rows = [observation(),observation(id="2",surface="api_search"),
                observation(id="3",prompt_kind="url_seeded")]
        self.assertEqual(len(monitor.summarize(rows)["groups"]),3)

    def test_same_id_cannot_change_product(self):
        with self.assertRaises(ValueError):
            monitor.summarize([observation(), observation(engine="yuanbao",
                updated_at="2026-09-28T11:00:00+08:00")])

    def test_complaint_aliases_and_toutiao_routes_deduplicate(self):
        urls=["https://gx.tousu.sina.cn/complaint/view/123/",
              "https://tousu.sina.com.cn/complaint/view/123/?from=search",
              "https://m.toutiao.com/article/456/?utm_source=test",
              "https://www.toutiao.com/item/456/"]
        group=monitor.summarize([observation(declared_source_count=4,
              sources=[{"url":u} for u in urls])])["groups"][0]
        self.assertEqual(group["source_url_appearances"],4)
        self.assertEqual(group["unique_source_urls"],2)
        self.assertEqual(group["platform_answer_coverage"],{"blackcat":1,"toutiao":1})
        self.assertEqual(group["verified_support_unique_urls"],0)
        self.assertIsNone(group["stable_effect"])

    def test_keep_identifying_query_parameters(self):
        self.assertNotEqual(monitor.canonical_url("https://example.com/s?id=1"),
                            monitor.canonical_url("https://example.com/s?id=2"))

    def test_domain_boundary_is_not_substring_match(self):
        self.assertNotEqual(monitor.platform_of("https://qcc.com.evil.example/a"),"qcc")

    def test_api_source_card_not_body_support(self):
        group=monitor.summarize([observation(sources=[{"url":"https://example.com/a"}],
                                           declared_source_count=1)])["groups"][0]
        self.assertEqual(group["verified_support_unique_urls"],0)

    def test_body_support_requires_excerpt_and_evidence(self):
        with self.assertRaises(ValueError):
            monitor.summarize([observation(declared_source_count=1,sources=[
                {"url":"https://example.com/a","body_supported":True}])])

    def test_title_only_does_not_invent_domain(self):
        group=monitor.summarize([observation(declared_source_count=1,
                  sources=[{"url":None,"label":"Some article"}])])["groups"][0]
        self.assertEqual(group["label_only_entries"],1)
        self.assertEqual(group["platform_answer_coverage"],{})

    def test_reject_inconsistent_capture(self):
        with self.assertRaises(ValueError):
            monitor.summarize([observation(declared_source_count=3)])
        with self.assertRaises(ValueError):
            monitor.summarize([observation(status="blocked",sources=[{"url":"https://example.com/a"}])])

    def test_credential_urls_rejected(self):
        for url in ("https://user:secret@example.com/a","https://example.com/a?access_token=demo"):
            with self.assertRaises(ValueError):
                monitor.canonical_url(url)


class InstallationTests(unittest.TestCase):
    def test_metadata_merge_preserves_user_policy_and_dependencies(self):
        old='interface:\n  display_name: "old"\npolicy:\n  allow_implicit_invocation: false\ndependencies:\n  tools: []\n'
        new='interface:\n  display_name: "new"\n  short_description: "new description"\n  default_prompt: "Use $example"\npolicy:\n  allow_implicit_invocation: true\n'
        merged=installer.merge_agent(old,new)
        self.assertIn("allow_implicit_invocation: false",merged)
        self.assertIn("dependencies:\n  tools: []",merged)
        self.assertIn('display_name: "new"',merged)

    def test_install_plan_is_self_contained_and_dry(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"skills"
            plan=installer.plan_install(target,True)
            self.assertFalse(target.exists())
            names={p.relative_to(target).parts[0] for p,_ in plan}
            self.assertEqual(names,{"doubao-skills","mmld-doubao","geo-multiplatform-workflow","geo-automonitor"})
            self.assertTrue(any(p.name=="platform-registry.json" for p,_ in plan))

    def test_install_apply_backup_idempotence_and_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"skills"
            old=target/"geo-multiplatform-workflow"/"agents"
            old.mkdir(parents=True)
            (old/"openai.yaml").write_text('interface:\n  display_name: "old"\npolicy:\n  allow_implicit_invocation: false\n',encoding="utf-8")
            (old.parent/"keep.txt").write_text("user notes",encoding="utf-8")
            args=[sys.executable,str(ROOT/"scripts/install_skills.py"),"--target",str(target),"--legacy-alias"]
            result=json.loads(subprocess.check_output(args,text=True,encoding="utf-8"))
            self.assertTrue(Path(result["backup"]).exists())
            self.assertEqual((old.parent/"keep.txt").read_text(),"user notes")
            self.assertIn("allow_implicit_invocation: false",(old/"openai.yaml").read_text())
            repeat=json.loads(subprocess.check_output(args+["--dry-run"],text=True,encoding="utf-8"))
            self.assertEqual(repeat["files_changed"],0)
            manifest=json.loads((target/"mmld-doubao"/"manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"],"mmld-doubao")
            runtime=[sys.executable,str(target/"mmld-doubao"/"mmld_doubao_v2.py"),
                     "--facts",str(target/"mmld-doubao"/"examples"/"facts.json")]
            plan=json.loads(subprocess.check_output(runtime,text=True,encoding="utf-8"))
            self.assertFalse(plan["task_metadata"]["published"])

    def test_legacy_alias_retains_discoverable_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan=installer.plan_install(Path(tmp)/"skills",True)
            alias=[text for p,text in plan if p.parts[-2:]==("mmld-doubao","SKILL.md")][0]
            self.assertIn("name: mmld-doubao\n",alias)


if __name__=="__main__":
    unittest.main()
