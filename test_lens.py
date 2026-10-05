import json
import tempfile
import unittest
from pathlib import Path
import lens


class TestClassify(unittest.TestCase):
    def test_heartbeat(self):
        self.assertEqual(lens.classify_line("heartbeat: agent-1 alive"), "heartbeat")
        self.assertEqual(lens.classify_line("still here, ping ok"), "heartbeat")

    def test_did_presence(self):
        text = "Ed25519 identity verified presence did:example:abc"
        self.assertEqual(lens.classify_line(text), "did_presence")

    def test_flop_question_protocol(self):
        text = "which FLOP area is in focus: protocol, coordination, or identity/auth?"
        self.assertEqual(lens.classify_line(text), "flop_question")

    def test_flop_question_coordination(self):
        text = "is anyone else working on FLOP today?"
        self.assertEqual(lens.classify_line(text), "flop_question")

    def test_peering_invite(self):
        text = "peering invite: join us at flop_labs forum for peering"
        self.assertEqual(lens.classify_line(text), "peering_invite")

    def test_other(self):
        self.assertEqual(lens.classify_line("hello world"), "other")


class TestIntent(unittest.TestCase):
    def test_protocol_tag(self):
        tags = lens.tag_flop_intent("FLOP protocol design and spec question")
        self.assertIn("protocol-design", tags)

    def test_coordination_tag(self):
        tags = lens.tag_flop_intent("anyone working on FLOP tasks today?")
        self.assertIn("agent-coordination", tags)

    def test_identity_tag(self):
        tags = lens.tag_flop_intent("identity and coordination matter most")
        self.assertIn("identity-auth", tags)

    def test_empty(self):
        self.assertEqual(lens.tag_flop_intent("hello"), [])


class TestDedup(unittest.TestCase):
    def test_verbatim_duplicates_grouped(self):
        records = lens.process_lines(
            [
                "peering invite: join us at flop_labs forum",
                "peering invite: join us at flop_labs forum",
                "which FLOP area is in focus: protocol?",
            ]
        )
        groups = lens.deduplicate_invites(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["count"], 2)
        self.assertEqual(groups[0]["first_seen_seq"], 1)

    def test_near_duplicate_case_punct(self):
        records = lens.process_lines(
            [
                "Peering Invite: Join us at flop_labs forum!",
                "peering invite join us at flop_labs forum",
            ]
        )
        groups = lens.deduplicate_invites(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["count"], 2)


class TestDigestReport(unittest.TestCase):
    def test_digest_and_report_with_tempfile(self):
        sample = [
            "heartbeat: agent alive",
            "Ed25519 identity verified presence did:example:1",
            "which FLOP area is in focus: protocol?",
            "peering invite: join us at flop_labs forum",
            "peering invite: join us at flop_labs forum",
        ]
        records = lens.process_lines(sample)
        groups = lens.deduplicate_invites(records)
        digest = lens.build_digest(records, groups)
        self.assertEqual(len(digest["questions"]), 1)
        self.assertEqual(len(digest["unique_invites"]), 1)
        self.assertEqual(digest["counts"]["heartbeat"], 1)
        markdown = lens.build_markdown(records, groups, digest)
        self.assertIn("FLOP questions", markdown)
        self.assertIn("peering invites", markdown.lower())
        with tempfile.TemporaryDirectory() as tmp:
            digest_path = Path(tmp) / "digest.json"
            md_path = Path(tmp) / "digest.md"
            digest_path.write_text(json.dumps(digest), encoding="utf-8")
            md_path.write_text(markdown, encoding="utf-8")
            back = json.loads(digest_path.read_text(encoding="utf-8"))
            self.assertEqual(back["counts"]["heartbeat"], 1)
            raw = "\n".join(sample).encode("utf-8")
            report = lens.build_report(records, groups, raw)
            self.assertEqual(report["rule_version"], lens.RULE_VERSION)
            self.assertTrue(len(report["sha256"]) == 64)


if __name__ == "__main__":
    unittest.main()
