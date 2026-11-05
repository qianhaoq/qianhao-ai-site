#!/usr/bin/env python3
"""Credential-free pull deployment. Remote content is data; this program never self-updates."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

REPO = "qianhaoq/qianhao-ai-site"
SITE = "https://qianhao.ai/"
API = "https://api.github.com/repos/" + REPO
ASSETS = ("styles.css", "robots.txt", "sitemap.xml", "index.html")
LIMIT = 262144
BASE_COMMIT = "a780087b56da04f235cce49a7c06136e0e4c4785"
BASE_SUMS = {
    "index.html": "f2cad150a5ec8026ff75b38e2fbe1d07a0f6f5347d11149a5957a4f4c785fcc3",
    "styles.css": "ac20c9ddd7de40d94890bde4cd2400aba5e785d87bae61b26c61db199a21c975",
    "robots.txt": "dd0198f29ff98351c207d4551c86ea1ea5069b24882cb1428963d9cf06b917bf",
    "sitemap.xml": "ef53e05e6c6489c25cf270c8539d3d5dd25688ce02bb47a9c56f8e975404d5ba",
}

class DeployError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def require(value, code):
    if not value:
        raise DeployError(code)

def utcnow():
    return dt.datetime.now(dt.timezone.utc)

def stamp(value=None):
    return (value or utcnow()).isoformat()

def parse_time(value):
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(result.tzinfo is not None, "INVALID_TIMESTAMP")
        return result
    except (AttributeError, TypeError, ValueError):
        raise DeployError("INVALID_TIMESTAMP") from None

def commit_id(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{40}", value), "INVALID_COMMIT")
    return value

def sums(data):
    return {name: hashlib.sha256(data[name]).hexdigest() for name in ASSETS}

def blob_id(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

class HtmlCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = []
        self.styles = []
        self.h1 = 0
    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        require(tag not in {"script", "iframe", "object", "embed", "base"}, "ACTIVE_HTML")
        require(not any(k.lower().startswith("on") for k in attrs), "ACTIVE_HTML")
        for key in ("href", "src", "action"):
            value = (attrs.get(key) or "").strip().lower()
            require(not re.match(r"(javascript|vbscript|data):", value), "ACTIVE_HTML")
        require(not (tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh"), "ACTIVE_HTML")
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical.append(attrs.get("href"))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.styles.append(attrs.get("href"))
        self.h1 += tag == "h1"

def validate_assets(data):
    require(set(data) == set(ASSETS), "ASSET_ALLOWLIST")
    require(all(isinstance(body, bytes) and 0 < len(body) <= LIMIT for body in data.values()), "ASSET_SIZE")
    try:
        text = {k: v.decode("utf-8") for k, v in data.items()}
        html = HtmlCheck()
        html.feed(text["index.html"])
        require(html.canonical == [SITE] and html.h1 == 1, "HTML_IDENTITY")
        version = hashlib.sha256(data["styles.css"]).hexdigest()
        expected_styles = ["styles.css?v=" + version]
        legacy = sums(data) == BASE_SUMS and html.styles in (["styles.css"], ["/styles.css"])
        require(html.styles == expected_styles or html.styles == ["/" + expected_styles[0]] or legacy, "STYLESHEET_IDENTITY")
        require("Sitemap: " + SITE + "sitemap.xml" in text["robots.txt"], "ROBOTS_IDENTITY")
        sitemap = ET.fromstring(text["sitemap.xml"])
        locations = [e.text for e in sitemap.iter() if e.tag.endswith("}loc") or e.tag == "loc"]
        require(SITE in locations and all(isinstance(x, str) and x.startswith(SITE) for x in locations), "SITEMAP_IDENTITY")
        require("expression(" not in text["styles.css"].lower(), "ACTIVE_CSS")
    except (UnicodeError, ET.ParseError):
        raise DeployError("INVALID_ASSET_ENCODING") from None

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise DeployError("REDIRECT_REFUSED")

class PublicClient:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    def get(self, url, limit=2097152):
        # All callers construct URLs from fixed origins and validated commit IDs.
        require(url.startswith(("https://api.github.com/repos/" + REPO + "/",
                                "https://raw.githubusercontent.com/" + REPO + "/",
                                SITE)), "URL_ALLOWLIST")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "qianhao-site-pull-deploy/1",
                                                       "Accept": "application/vnd.github+json",
                                                       "Cache-Control": "no-cache"})
            with self.opener.open(req, timeout=15) as response:
                require(response.status == 200, "HTTP_STATUS")
                body = response.read(limit + 1)
                require(len(body) <= limit, "RESPONSE_SIZE")
                return body
        except urllib.error.HTTPError as error:
            raise DeployError("HTTP_404" if error.code == 404 else "HTTP_UPSTREAM") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise DeployError("NETWORK_UNAVAILABLE") from None
    def json(self, url):
        try:
            return json.loads(self.get(url))
        except (ValueError, UnicodeError):
            raise DeployError("INVALID_UPSTREAM_JSON") from None
    def head(self):
        branch = self.json(API + "/branches/main")
        try:
            commit = branch["commit"]
            return {"sha": commit_id(commit["sha"]), "tree": commit_id(commit["commit"]["tree"]["sha"]),
                    "date": stamp(parse_time(commit["commit"]["committer"]["date"]))}
        except (KeyError, TypeError):
            raise DeployError("INVALID_HEAD") from None
    def ready(self, sha):
        result = self.json(API + "/actions/workflows/site-checks.yml/runs?event=push&head_sha=" + commit_id(sha) + "&per_page=10")
        return any(run.get("head_sha") == sha and run.get("head_branch") == "main"
                   and run.get("event") == "push" and run.get("status") == "completed"
                   and run.get("conclusion") == "success"
                   for run in result.get("workflow_runs", []))
    def snapshot(self, head):
        tree = self.json(API + "/git/trees/" + commit_id(head["tree"]) + "?recursive=1")
        require(tree.get("truncated") is False, "TRUNCATED_TREE")
        entries = {}
        for item in tree.get("tree", []):
            if item.get("path") in ASSETS:
                require(item["path"] not in entries, "DUPLICATE_ASSET")
                entries[item["path"]] = item
        require(set(entries) == set(ASSETS), "ASSET_ALLOWLIST")
        data = {}
        for name in ASSETS:
            entry = entries[name]
            require(entry.get("mode") == "100644" and entry.get("type") == "blob", "REMOTE_ASSET_TYPE")
            require(isinstance(entry.get("size"), int) and 0 < entry["size"] <= LIMIT, "ASSET_SIZE")
            expected = commit_id(entry.get("sha"))
            data[name] = self.get("https://raw.githubusercontent.com/" + REPO + "/" + commit_id(head["sha"]) + "/" + name, LIMIT)
            require(blob_id(data[name]) == expected, "GIT_BLOB_MISMATCH")
        validate_assets(data)
        return data
    def verify_live(self, sha, expected):
        for name in ASSETS:
            url = SITE + ("" if name == "index.html" else name) + "?release=" + commit_id(sha)
            require(hashlib.sha256(self.get(url, LIMIT)).hexdigest() == expected[name], "PUBLIC_ASSET_MISMATCH")
    def status(self):
        try:
            return self.json(SITE + "deploy-status.json")
        except DeployError as error:
            if error.code == "HTTP_404":
                return None
            raise

def atomic_bytes(path, body, mode):
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(body)
            os.fchmod(output.fileno(), mode)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def write_json(path, value, mode=0o600):
    atomic_bytes(path, (json.dumps(value, sort_keys=True) + "\n").encode(), mode)

def read_assets(root):
    require(root.is_dir() and not root.is_symlink(), "LOCAL_ROOT_TYPE")
    data = {}
    for name in ASSETS:
        path = root / name
        require(path.is_file() and not path.is_symlink(), "LOCAL_ASSET_TYPE")
        require(path.stat().st_size <= LIMIT, "ASSET_SIZE")
        data[name] = path.read_bytes()
    return data

@contextmanager
def exclusive(state_dir):
    require(not state_dir.is_symlink(), "STATE_DIRECTORY_TYPE")
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(state_dir / "deploy.lock", os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DeployError("DEPLOY_BUSY") from None
        yield

class Publisher:
    def __init__(self, root, state_dir, backups, client=None, now=utcnow):
        self.root, self.state_dir, self.backups = map(Path, (root, state_dir, backups))
        self.client, self.now = client or PublicClient(), now
        self.state_file = self.state_dir / "state.json"
        self.transaction = self.state_dir / "transaction.json"
    def load(self):
        if not self.state_file.exists():
            return {"served_commit": BASE_COMMIT, "sums": BASE_SUMS, "blocked_commit": None, "last_success": None}
        require(not self.state_file.is_symlink(), "STATE_FILE_TYPE")
        state = json.loads(self.state_file.read_text())
        commit_id(state["served_commit"])
        require(set(state["sums"]) == set(ASSETS) and
                all(re.fullmatch(r"[a-f0-9]{64}", value) for value in state["sums"].values()), "INVALID_STATE")
        return state
    def status(self, phase, state, desired, code=None):
        result = {"schema": "qianhao.ai/deploy-status@1", "phase": phase,
                  "desired_commit": desired, "served_commit": state["served_commit"],
                  "checked_at": stamp(self.now()), "last_success": state.get("last_success"), "error_code": code}
        write_json(self.root / "deploy-status.json", result, 0o644)
        fd = os.open(self.state_dir / "history.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as history:
            history.write(json.dumps(result) + "\n")
            history.flush()
            os.fsync(history.fileno())
        print(json.dumps(result), flush=True)
        return result
    def backup(self, state, target):
        require(not self.backups.is_symlink(), "BACKUP_DIRECTORY_TYPE")
        self.backups.mkdir(parents=True, exist_ok=True, mode=0o700)
        name = self.now().strftime("%Y%m%dT%H%M%SZ") + "-" + commit_id(target) + "-" + uuid.uuid4().hex[:8]
        backup = self.backups / name
        backup.mkdir(mode=0o700)
        for asset in ASSETS:
            shutil.copy2(self.root / asset, backup / asset, follow_symlinks=False)
        require(sums(read_assets(backup)) == state["sums"], "BACKUP_MISMATCH")
        write_json(backup / "manifest.json", {"schema": 1, "state": state})
        return name
    def backup_data(self, name):
        require(isinstance(name, str) and re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{40}-[a-f0-9]{8}", name), "BACKUP_NAME")
        backup = self.backups / name
        require(not backup.is_symlink() and backup.resolve().parent == self.backups.resolve(), "BACKUP_PATH")
        manifest = json.loads((backup / "manifest.json").read_text())
        require(manifest.get("schema") == 1, "BACKUP_SCHEMA")
        state, data = manifest["state"], read_assets(backup)
        commit_id(state["served_commit"])
        require(sums(data) == state["sums"], "BACKUP_MISMATCH")
        return state, data
    def restore(self, transaction, state, code="RECOVERED_AFTER_INTERRUPTION"):
        previous, data = self.backup_data(transaction["backup"])
        actual = sums(read_assets(self.root))
        require(all(actual[k] in {previous["sums"][k], transaction["target_sums"][k]} for k in ASSETS), "RECOVERY_DRIFT")
        for name in ASSETS:
            atomic_bytes(self.root / name, data[name], 0o644)
        require(sums(read_assets(self.root)) == previous["sums"], "ROLLBACK_MISMATCH")
        previous["blocked_commit"] = commit_id(transaction["target_commit"])
        write_json(self.state_file, previous)
        self.transaction.unlink(missing_ok=True)
        return self.status("failed", previous, transaction["target_commit"], code)
    def sync(self):
        with exclusive(self.state_dir):
            state, desired = self.load(), None
            try:
                if self.transaction.exists():
                    tx = json.loads(self.transaction.read_text())
                    if state["served_commit"] == tx["target_commit"] and sums(read_assets(self.root)) == state["sums"] == tx["target_sums"]:
                        self.transaction.unlink()
                    else:
                        return self.restore(tx, state)
                require(sums(read_assets(self.root)) == state["sums"], "LOCAL_DRIFT")
                head = self.client.head()
                desired = head["sha"]
                if state.get("blocked_commit") == desired:
                    return self.status("blocked", state, desired, "FAILED_COMMIT_BLOCKED")
                if desired == state["served_commit"]:
                    self.client.verify_live(desired, state["sums"])
                    state["last_success"] = stamp(self.now())
                    write_json(self.state_file, state)
                    return self.status("success", state, desired)
                if not self.client.ready(desired):
                    return self.status("pending_checks", state, desired)
                data = self.client.snapshot(head)
                target = sums(data)
                latest = self.client.head()
                if latest["sha"] != desired:
                    return self.status("superseded", state, latest["sha"])
                if target != state["sums"]:
                    name = self.backup(state, desired)
                    tx = {"target_commit": desired, "target_sums": target, "backup": name}
                    write_json(self.transaction, tx)
                    try:
                        for asset in ASSETS:
                            atomic_bytes(self.root / asset, data[asset], 0o644)
                        require(sums(read_assets(self.root)) == target, "LOCAL_PUBLISH_MISMATCH")
                        self.client.verify_live(desired, target)
                    except Exception as error:
                        code = error.code if isinstance(error, DeployError) else "LOCAL_PUBLISH_ERROR"
                        return self.restore(tx, state, "ROLLED_BACK_" + code)
                else:
                    self.client.verify_live(desired, target)
                state = {"served_commit": desired, "sums": target, "blocked_commit": None, "last_success": stamp(self.now())}
                write_json(self.state_file, state)
                self.transaction.unlink(missing_ok=True)
                return self.status("success", state, desired)
            except (DeployError, OSError, ValueError, KeyError, TypeError) as error:
                code = error.code if isinstance(error, DeployError) else "LOCAL_STATE_ERROR"
                return self.status("failed", state, desired, code)
    def rollback(self, name):
        with exclusive(self.state_dir):
            require(not self.transaction.exists(), "RECOVERY_REQUIRED")
            state = self.load()
            require(sums(read_assets(self.root)) == state["sums"], "LOCAL_DRIFT")
            tx = {"backup": name, "target_commit": state["served_commit"], "target_sums": state["sums"]}
            return self.restore(tx, state, "MANUAL_ROLLBACK")
    def retry(self, sha):
        with exclusive(self.state_dir):
            require(not self.transaction.exists(), "RECOVERY_REQUIRED")
            state = self.load()
            require(sums(read_assets(self.root)) == state["sums"], "LOCAL_DRIFT")
            require(commit_id(sha) == state.get("blocked_commit") == self.client.head()["sha"], "RETRY_COMMIT_CHANGED")
            state["blocked_commit"] = None
            write_json(self.state_file, state)
            return self.status("retry_requested", state, sha)

def monitor(client=None, now=utcnow, grace=900, stale=1200):
    client = client or PublicClient()
    head = client.head()
    data = client.snapshot(head)
    expected = sums(data)
    status = client.status()
    if status is not None:
        require(status.get("schema") == "qianhao.ai/deploy-status@1", "STATUS_SCHEMA")
        require((now() - parse_time(status.get("checked_at"))).total_seconds() <= stale, "CONTROLLER_STALE")
        require(not (status.get("desired_commit") == head["sha"] and status.get("phase") in {"failed", "blocked"}), "CONTROLLER_FAILED")
    try:
        client.verify_live(head["sha"], expected)
        if status is not None:
            require(status.get("served_commit") == head["sha"] and status.get("phase") == "success", "VERSION_UNREPORTED")
    except DeployError:
        latest = client.head()
        if latest["sha"] != head["sha"]:
            return {"phase": "superseded"}
        if (now() - parse_time(head["date"])).total_seconds() < grace:
            return {"phase": "pending_grace", "desired_commit": head["sha"]}
        raise
    return {"phase": "success" if status else "awaiting_controller", "commit": head["sha"], "assets_verified": True}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["sync", "rollback", "retry", "validate-source", "inspect-commit", "monitor"])
    parser.add_argument("--root", type=Path, default=Path("/var/www/qianhao.ai"))
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/qianhao-site-deploy"))
    parser.add_argument("--backups", type=Path, default=Path("/var/backups/qianhao.ai/auto"))
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--commit")
    parser.add_argument("--backup")
    args = parser.parse_args()
    try:
        if args.mode == "validate-source":
            data = read_assets(args.source)
            validate_assets(data)
            result = {"phase": "valid_source", "sha256": sums(data)}
        elif args.mode == "inspect-commit":
            client = PublicClient()
            sha = commit_id(args.commit)
            commit = client.json(API + "/git/commits/" + sha)
            data = client.snapshot({"sha": sha, "tree": commit_id(commit["tree"]["sha"])})
            result = {"phase": "valid_commit", "commit": sha, "sha256": sums(data)}
        elif args.mode == "monitor":
            result = monitor()
        else:
            publisher = Publisher(args.root, args.state_dir, args.backups)
            result = publisher.sync() if args.mode == "sync" else publisher.retry(args.commit) if args.mode == "retry" else publisher.rollback(args.backup)
        print(json.dumps(result), flush=True)
        if result.get("phase") in {"failed", "blocked"}:
            raise SystemExit(1)
    except (DeployError, OSError, ValueError, KeyError, TypeError) as error:
        code = error.code if isinstance(error, DeployError) else "LOCAL_STATE_ERROR"
        print(json.dumps({"phase": "failed", "error_code": code}), flush=True)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
