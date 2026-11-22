"""Record failure evidence without model transcription or invented timestamps."""

import asyncio
import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
import cli
from core import deepwiki
from core.records import evidence_hashes, index_explanations, record_verification
from core.snapshot import load_review, seal, write_json


class EvidenceRecords(unittest.TestCase):
    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli.main(list(args))
        return code, json.loads(output.getvalue())

    def review(self, folder):
        write_json(folder / "data.json", {"schema": "oss-gate.review/2"})
        write_json(folder / "api-responses.json", {"public": "evidence"})
        seal(folder, ["data.json", "api-responses.json"])
        (folder / "review.en.md").write_text("# Evidence-backed review\n", encoding="utf-8")
        check = folder / "check-input.json"
        write_json(
            check,
            {
                "status": "WARN",
                "checked_fields": ["version, license and narrative references"],
                "mismatches": [],
                "unresolved": ["communication not independently verified"],
            },
        )
        return check

    def response(self, folder, topic="overview", error=False):
        path = folder / f"deepwiki.{topic}.json"
        write_json(
            path,
            {
                "schema": "oss-gate.explanation/1",
                "repository": "owner/repo",
                "topic": topic,
                "isError": error,
                "content": [{"type": "text", "text": "Repository not found" if error else "Answer"}],
            },
        )
        return path

    def test_cli_preserves_remote_failure_and_nonzero_exit(self):
        remote = {"isError": True, "content": [{"type": "text", "text": "Repository not found\nexact reply"}]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(deepwiki, "_call", AsyncMock(return_value=remote)):
            path = Path(tmp) / "deepwiki.overview.json"
            before = datetime.now(timezone.utc)
            code, result = self.run_cli("explain", "owner/repo", "--out", str(path))
            saved = json.loads(path.read_text())
            self.assertEqual(code, 1)
            self.assertEqual(saved["content"], remote["content"])
            self.assertEqual(saved["capture_kind"], "tool_response")
            self.assertTrue(result["isError"])
            self.assertGreaterEqual(datetime.fromisoformat(saved["recorded_at"]), before)
            self.assertLessEqual(datetime.fromisoformat(saved["recorded_at"]), datetime.now(timezone.utc))

    def test_local_failure_is_saved_without_exception_secret(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(deepwiki, "_call", AsyncMock(side_effect=RuntimeError("private credential must not escape"))),
        ):
            path = Path(tmp) / "deepwiki.overview.json"
            code, result = self.run_cli("explain", "owner/repo", "--out", str(path))
            self.assertEqual(code, 1)
            self.assertEqual(result["capture_kind"], "local_failure")
            self.assertEqual(result["code"], "upstream_unavailable")
            self.assertNotIn("private credential", path.read_text())

    def test_success_and_exclusive_output(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(deepwiki, "_call", AsyncMock(return_value={"isError": False, "content": []})) as call,
        ):
            path = Path(tmp) / "deepwiki.overview.json"
            self.assertEqual(self.run_cli("explain", "owner/repo", "--out", str(path))[0], 0)
            original = path.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.run_cli("explain", "owner/repo", "--out", str(path))
            self.assertEqual(call.call_count, 1)
            self.assertEqual(path.read_bytes(), original)

    def test_mcp_response_gets_same_capture_metadata(self):
        with patch.object(deepwiki, "_call", AsyncMock(return_value={"isError": True, "content": []})):
            result = json.loads(asyncio.run(deepwiki.invoke("owner/repo")))
        self.assertEqual(result["schema"], "oss-gate.explanation/1")
        self.assertIsNotNone(datetime.fromisoformat(result["recorded_at"]).tzinfo)

    def test_index_keeps_multiple_responses_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            paths = [self.response(folder), self.response(folder, "maintenance", True)]
            original = [p.read_bytes() for p in paths]
            code, _ = self.run_cli("index-explanations", str(folder), *(p.name for p in paths))
            self.assertEqual(code, 0)
            index = json.loads((folder / "deepwiki.json").read_text())
            self.assertEqual([e["status"] for e in index["responses"]], ["response", "error"])
            self.assertEqual([p.read_bytes() for p in paths], original)
            with self.assertRaises(FileExistsError):
                index_explanations(folder, [paths[0].name])

    def test_index_rejects_paths_duplicates_and_mixed_repositories(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = self.response(folder)
            for names in (["../outside.json"], [str(path)], [path.name, path.name], ["deepwiki.json"]):
                with self.assertRaises(ValueError):
                    index_explanations(folder, names)
            other = self.response(folder, "maintenance")
            value = json.loads(other.read_text())
            value["repository"] = "other/repo"
            other.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                index_explanations(folder, [path.name, other.name])

    def test_record_binds_check_to_time_evidence_and_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            check = self.review(folder)
            response = self.response(folder, error=True)
            index_explanations(folder, [response.name])
            before = datetime.now(timezone.utc)
            code, result = self.run_cli("record-verification", str(folder), "--input", str(check))
            self.assertEqual(code, 0)
            self.assertFalse(result["automated_verification"])
            record = load_review(folder / "data.json")["verification"]
            self.assertGreaterEqual(datetime.fromisoformat(record["recorded_at"]), before)
            self.assertEqual(record["files_sha256"], evidence_hashes(folder))
            (folder / "review.en.md").write_text("changed")
            with self.assertRaisesRegex(ValueError, "fresh agent check"):
                load_review(folder / "data.json")

    def test_added_translation_or_changed_indexed_response_invalidates_check(self):
        for change in ("translation", "response"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                check = self.review(folder)
                response = self.response(folder)
                index_explanations(folder, [response.name])
                record_verification(folder, check)
                if change == "translation":
                    (folder / "review.ko.md").write_text("번역", encoding="utf-8")
                else:
                    response.write_text("{}")
                with self.assertRaises(ValueError):
                    load_review(folder / "data.json")

    def test_rejects_guessed_time_false_pass_and_malformed_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            check = self.review(folder)
            original = json.loads(check.read_text())
            for update in (
                {"recorded_at": "guessed"},
                {"status": "PASS"},
                {"checked_fields": []},
                {"unresolved": "none"},
            ):
                check.write_text(json.dumps({**original, **update}))
                self.assertEqual(self.run_cli("record-verification", str(folder), "--input", str(check))[0], 1)
                self.assertFalse((folder / "verification.json").exists())

    def test_existing_record_and_sealed_fail_cannot_be_silently_cleared(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            check = self.review(folder)
            record_verification(folder, check)
            original = (folder / "verification.json").read_bytes()
            with self.assertRaises(FileExistsError):
                record_verification(folder, check)
            self.assertEqual((folder / "verification.json").read_bytes(), original)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_json(folder / "data.json", {"schema": "oss-gate.review/2", "verification": {"status": "FAIL"}})
            seal(folder, ["data.json"])
            (folder / "review.en.md").write_text("review")
            check = folder / "check.json"
            write_json(check, {"status": "PASS", "checked_fields": ["version"], "mismatches": [], "unresolved": []})
            record_verification(folder, check)
            self.assertEqual(load_review(folder / "data.json")["verification"]["status"], "FAIL")

    def test_legacy_record_is_still_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.review(folder)
            write_json(folder / "verification.json", {"status": "WARN"})
            self.assertEqual(load_review(folder / "data.json")["verification"]["status"], "WARN")

    def test_explicit_recheck_archives_old_record_and_binds_new_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            check = self.review(folder)
            record_verification(folder, check)
            previous = (folder / "verification.json").read_bytes()
            (folder / "review.en.md").write_text("corrected review")
            code, result = self.run_cli("record-verification", str(folder), "--input", str(check), "--replace")
            self.assertEqual(code, 0)
            self.assertEqual(Path(result["previous"]).read_bytes(), previous)
            self.assertEqual(load_review(folder / "data.json")["verification"]["status"], "WARN")

    def test_transcription_is_bound_and_symlink_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            check = self.review(folder)
            transcription = folder / "deepwiki-transcription.md"
            transcription.write_text("Labelled agent transcription")
            record_verification(folder, check)
            transcription.unlink()
            with self.assertRaises(ValueError):
                load_review(folder / "data.json")
            try:
                transcription.symlink_to(check)
            except OSError:
                return  # Windows may require elevated privileges for symlinks.
            with self.assertRaises(ValueError):
                evidence_hashes(folder)
