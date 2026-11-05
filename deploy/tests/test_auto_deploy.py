import contextlib
import copy
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("auto_deploy", ROOT / "deploy/auto_deploy.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
OLD = {name: (ROOT / "deploy/tests/fixtures/bootstrap" / name).read_bytes() for name in m.ASSETS}
NOW = dt.datetime(2026, 11, 5, 1, 0, tzinfo=dt.timezone.utc)
SHA = "b" * 40
TREE = "c" * 40

def updated():
    data = dict(OLD)
    data["styles.css"] += b"\n/* next tested release */\n"
    version = hashlib.sha256(data["styles.css"]).hexdigest()
    data["index.html"] = data["index.html"].replace(b'href="styles.css"', ('href="styles.css?v=' + version + '"').encode())
    return data

class Fake:
    def __init__(self, root, data=None, sha=SHA):
        self.root, self.data, self.sha = root, data or updated(), sha
        self.ready_value, self.fail_live, self.fail_head, self.advance = True, False, False, False
        self.snapshots, self.heads = 0, 0
        self.date = m.stamp(NOW - dt.timedelta(hours=1))
    def head(self):
        self.heads += 1
        if self.fail_head:
            raise m.DeployError("NETWORK_UNAVAILABLE")
        sha = "d" * 40 if self.advance and self.heads > 1 else self.sha
        return {"sha": sha, "tree": TREE, "date": self.date}
    def ready(self, sha):
        return self.ready_value
    def snapshot(self, head):
        self.snapshots += 1
        return dict(self.data)
    def verify_live(self, sha, expected):
        if self.fail_live or m.sums(m.read_assets(self.root)) != expected:
            raise m.DeployError("PUBLIC_ASSET_MISMATCH")
    def status(self):
        path = self.root / "deploy-status.json"
        return json.loads(path.read_text()) if path.exists() else None

class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root, self.state, self.backups = base / "qianhao.ai", base / "state", base / "backups"
        self.root.mkdir()
        for name, body in OLD.items():
            (self.root / name).write_bytes(body)
        self.client = Fake(self.root)
        self.publisher = m.Publisher(self.root, self.state, self.backups, self.client, lambda: NOW)
    def sync(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.publisher.sync()
    def assertCode(self, expected, function, *args):
        with self.assertRaises(m.DeployError) as error:
            function(*args)
        self.assertEqual(error.exception.code, expected)

class DeployTests(Fixture):
    def test_bootstrap_fixture_matches_verified_production_and_git_blob(self):
        self.assertEqual(m.sums(OLD), m.BASE_SUMS)
        self.assertEqual(m.blob_id(OLD["index.html"]), "05753cfc1cfaf8aab1c89d105bf0dfbf7dfad9e5")
        m.validate_assets(OLD)
    def test_only_checked_exact_commit_is_published_and_repeats_are_idempotent(self):
        self.assertEqual(self.sync()["phase"], "success")
        self.assertEqual(m.sums(m.read_assets(self.root)), m.sums(self.client.data))
        state = json.loads((self.state / "state.json").read_text())
        self.assertEqual(state["served_commit"], SHA)
        self.assertEqual(self.sync()["phase"], "success")
        self.assertEqual(len(list(self.backups.iterdir())), 1)
        self.assertEqual(self.client.snapshots, 1)
        self.assertTrue(all((self.root / n).stat().st_mode & 0o777 == 0o644 for n in m.ASSETS))
        self.assertEqual((self.state / "state.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(len((self.state / "history.jsonl").read_text().splitlines()), 2)
    def test_checks_pending_never_download_or_modify_assets(self):
        self.client.ready_value = False
        self.assertEqual(self.sync()["phase"], "pending_checks")
        self.assertEqual(self.client.snapshots, 0)
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
        self.assertFalse(self.backups.exists())
    def test_branch_advance_discards_staged_older_commit(self):
        self.client.advance = True
        self.assertEqual(self.sync()["phase"], "superseded")
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
        self.assertFalse(self.backups.exists())
    def test_docs_only_commit_records_exact_version_without_an_asset_rewrite(self):
        self.client.data = OLD
        self.assertEqual(self.sync()["phase"], "success")
        self.assertFalse(self.backups.exists())
        self.assertEqual(json.loads((self.state / "state.json").read_text())["served_commit"], SHA)
    def test_manual_file_drift_stops_before_network_or_overwrite(self):
        (self.root / "styles.css").write_bytes(b"manual local change")
        result = self.sync()
        self.assertEqual(result["error_code"], "LOCAL_DRIFT")
        self.assertEqual((self.root / "styles.css").read_bytes(), b"manual local change")
        self.assertEqual(self.client.heads, 0)
    def test_local_symlink_is_not_followed(self):
        outside = Path(self.tmp.name) / "outside"
        outside.write_bytes(b"untouched")
        (self.root / "styles.css").unlink()
        (self.root / "styles.css").symlink_to(outside)
        self.assertEqual(self.sync()["error_code"], "LOCAL_ASSET_TYPE")
        self.assertEqual(outside.read_bytes(), b"untouched")
    def test_prepublication_network_failure_preserves_files_and_can_retry(self):
        self.client.fail_head = True
        self.assertEqual(self.sync()["error_code"], "NETWORK_UNAVAILABLE")
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
        self.assertFalse(self.backups.exists())
        self.client.fail_head = False
        self.assertEqual(self.sync()["phase"], "success")
    def test_public_verification_failure_rolls_back_and_blocks_automatic_repetition(self):
        self.client.fail_live = True
        result = self.sync()
        self.assertEqual(result["error_code"], "ROLLED_BACK_PUBLIC_ASSET_MISMATCH")
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
        self.client.fail_live = False
        self.assertEqual(self.sync()["phase"], "blocked")
        self.assertEqual(self.client.snapshots, 1)
        self.assertEqual(len(list(self.backups.iterdir())), 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.publisher.retry(SHA)
        self.assertEqual(self.sync()["phase"], "success")
    def test_failure_after_first_write_restores_original_assets(self):
        original, count = m.atomic_bytes, [0]
        def once(path, body, mode):
            if path.parent == self.root and path.name in m.ASSETS:
                count[0] += 1
                if count[0] == 2:
                    raise OSError("simulated write failure")
            return original(path, body, mode)
        with patch.object(m, "atomic_bytes", side_effect=once):
            result = self.sync()
        self.assertEqual(result["error_code"], "ROLLED_BACK_LOCAL_PUBLISH_ERROR")
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
        self.assertFalse((self.state / "transaction.json").exists())
    def test_interrupted_promotion_recovers_from_durable_journal(self):
        self.state.mkdir()
        state = self.publisher.load()
        name = self.publisher.backup(state, SHA)
        tx = {"target_commit": SHA, "target_sums": m.sums(self.client.data), "backup": name}
        m.write_json(self.state / "transaction.json", tx)
        m.atomic_bytes(self.root / "styles.css", self.client.data["styles.css"], 0o644)
        result = self.sync()
        self.assertEqual(result["error_code"], "RECOVERED_AFTER_INTERRUPTION")
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
        self.assertEqual(json.loads((self.state / "state.json").read_text())["blocked_commit"], SHA)
    def test_committed_journal_is_not_mistaken_for_failed_publication(self):
        self.state.mkdir()
        old = self.publisher.load()
        name = self.publisher.backup(old, SHA)
        target = m.sums(self.client.data)
        m.write_json(self.state / "transaction.json", {"target_commit": SHA, "target_sums": target, "backup": name})
        for asset in m.ASSETS:
            m.atomic_bytes(self.root / asset, self.client.data[asset], 0o644)
        m.write_json(self.state / "state.json", {"served_commit": SHA, "sums": target, "blocked_commit": None})
        self.assertEqual(self.sync()["phase"], "success")
        self.assertEqual(len(list(self.backups.iterdir())), 1)
    def test_rollback_is_verified_and_cannot_escape_backup_directory(self):
        self.sync()
        backup = next(self.backups.iterdir())
        with contextlib.redirect_stdout(io.StringIO()):
            self.publisher.rollback(backup.name)
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
        self.assertEqual(self.sync()["phase"], "blocked")
        self.assertCode("BACKUP_NAME", self.publisher.backup_data, "../../other-site")
        self.assertCode("RETRY_COMMIT_CHANGED", self.publisher.retry, "e" * 40)
    def test_repeated_manual_rollback_keeps_the_failed_commit_blocked(self):
        self.sync()
        backup = next(self.backups.iterdir())
        with contextlib.redirect_stdout(io.StringIO()):
            self.publisher.rollback(backup.name)
            repeated = self.publisher.rollback(backup.name)
        self.assertEqual(repeated["phase"], "already_rolled_back")
        self.assertEqual(repeated["blocked_commit"], SHA)
        self.assertEqual(self.sync()["phase"], "blocked")
        self.assertEqual(self.client.snapshots, 1)
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
    def test_successful_rollback_cli_is_not_reported_as_an_operation_failure(self):
        self.sync()
        backup = next(self.backups.iterdir())
        with patch.object(m, "Publisher", return_value=self.publisher), patch("sys.argv", ["auto_deploy.py", "rollback", "--backup", backup.name]), contextlib.redirect_stdout(io.StringIO()) as output:
            m.main()
        result = json.loads(output.getvalue().splitlines()[-1])
        self.assertTrue(result["operation_succeeded"])
        self.assertEqual(m.sums(m.read_assets(self.root)), m.BASE_SUMS)
    def test_competing_publisher_cannot_enter(self):
        with m.exclusive(self.state):
            self.assertCode("DEPLOY_BUSY", self.publisher.sync)
    def test_static_validation_rejects_active_content_missing_files_and_stale_cache_keys(self):
        script = dict(OLD)
        script["index.html"] += b"<script>alert(1)</script>"
        self.assertCode("ACTIVE_HTML", m.validate_assets, script)
        missing = dict(OLD)
        del missing["robots.txt"]
        self.assertCode("ASSET_ALLOWLIST", m.validate_assets, missing)
        stale = dict(OLD)
        stale["styles.css"] += b"\n/* changed without cache version */"
        self.assertCode("STYLESHEET_IDENTITY", m.validate_assets, stale)
        m.validate_assets(updated())

class WireTests(unittest.TestCase):
    BLOBS = {"index.html": "05753cfc1cfaf8aab1c89d105bf0dfbf7dfad9e5",
             "styles.css": "04c78e3293e61e4c0f94f492ad03f661c20751b0",
             "robots.txt": "458ea1decab964bbf4f448643439b670bfedf42f",
             "sitemap.xml": "72e77b39156bb9b13d0bde792f0652e962270bfa"}
    class Wire(m.PublicClient):
        def __init__(self, owner):
            self.entries = [{"path": n, "type": "blob", "mode": "100644", "size": len(OLD[n]), "sha": owner.BLOBS[n]} for n in m.ASSETS]
            self.corrupt, self.runs, self.urls = False, [], []
        def json(self, url):
            if "/actions/workflows/" in url:
                return {"workflow_runs": self.runs}
            return {"truncated": False, "tree": self.entries}
        def get(self, url, limit=m.LIMIT):
            self.urls.append(url)
            data = OLD[url.rsplit("/", 1)[-1]]
            return data + b"corruption" if self.corrupt else data
    def test_pinned_downloads_match_git_blob_ids(self):
        wire = self.Wire(self)
        self.assertEqual(wire.snapshot({"sha": SHA, "tree": TREE}), OLD)
        self.assertTrue(all("/" + SHA + "/" in url for url in wire.urls))
    def test_symlink_or_corrupt_remote_blob_is_rejected(self):
        wire = self.Wire(self)
        wire.entries[0]["mode"] = "120000"
        with self.assertRaisesRegex(m.DeployError, "REMOTE_ASSET_TYPE"):
            wire.snapshot({"sha": SHA, "tree": TREE})
        wire = self.Wire(self)
        wire.corrupt = True
        with self.assertRaisesRegex(m.DeployError, "GIT_BLOB_MISMATCH"):
            wire.snapshot({"sha": SHA, "tree": TREE})
    def test_gate_requires_successful_push_run_on_the_exact_main_commit(self):
        wire = self.Wire(self)
        run = {"head_sha": SHA, "head_branch": "main", "event": "push", "status": "completed", "conclusion": "success"}
        for field, value in [("head_sha", "e" * 40), ("head_branch", "another"), ("event", "pull_request"), ("conclusion", "failure"), ("status", "in_progress")]:
            wire.runs = [{**run, field: value}]
            self.assertFalse(wire.ready(SHA))
        wire.runs = [run]
        self.assertTrue(wire.ready(SHA))

class MonitorTests(Fixture):
    def test_monitor_reports_missing_controller_without_claiming_it_is_enabled(self):
        self.client.data, self.client.sha = OLD, m.BASE_COMMIT
        result = m.monitor(self.client, lambda: NOW)
        self.assertEqual(result["phase"], "awaiting_controller")
        self.assertTrue(result["assets_verified"])
    def test_failed_and_stale_controller_status_produce_monitor_failures(self):
        self.sync()
        self.assertEqual(m.monitor(self.client, lambda: NOW)["phase"], "success")
        self.assertCode("CONTROLLER_STALE", m.monitor, self.client, lambda: NOW + dt.timedelta(hours=1))
        self.client.fail_live = True
        self.client.sha = "e" * 40
        self.sync()
        self.assertCode("CONTROLLER_FAILED", m.monitor, self.client, lambda: NOW)
    def test_recent_commit_has_a_grace_period_but_old_drift_fails(self):
        self.client.date = m.stamp(NOW)
        self.assertEqual(m.monitor(self.client, lambda: NOW)["phase"], "pending_grace")
        self.client.date = m.stamp(NOW - dt.timedelta(hours=1))
        self.assertCode("PUBLIC_ASSET_MISMATCH", m.monitor, self.client, lambda: NOW)
    def test_cli_failure_exits_nonzero_for_github_actions_notifications(self):
        with patch.object(m, "PublicClient", return_value=self.client), patch("sys.argv", ["auto_deploy.py", "monitor"]), contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as result:
                m.main()
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["phase"], "failed")

if __name__ == "__main__":
    unittest.main()
