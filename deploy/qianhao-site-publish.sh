#!/usr/bin/env bash
set -euo pipefail
# Python's tar reader validates members before writing any archive bytes to disk.
exec python3 -c '
import hashlib, os, pathlib, re, shutil, subprocess, sys, tarfile, tempfile
FILES = ("styles.css", "index.html", "index.md", "robots.txt", "sitemap.xml")
site = pathlib.Path(os.environ.get("SITE_ROOT", "/var/www/qianhao.ai")).resolve()
backups = pathlib.Path(os.environ.get("BACKUP_ROOT", "/var/www/backups")).resolve()
pattern = r"qianhao\.ai-pre-[0-9a-f]{40}-[0-9]{8}-[0-9]{6}"
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def restore(source):
    for f in FILES:
        p = source / f
        if not p.is_file() or p.is_symlink():
            raise ValueError("backup must contain five regular files")
    for f in FILES:
        install(source / f, site / f)
def install(src, dst):
    # Replace the directory entry atomically; never follow a live-file symlink.
    fd, name = tempfile.mkstemp(prefix=".qianhao-", dir=site)
    try:
        with os.fdopen(fd, "wb") as out, src.open("rb") as inp:
            shutil.copyfileobj(inp, out)
            os.fchmod(out.fileno(), 0o644)
        os.replace(name, dst)
    finally:
        if os.path.exists(name): os.unlink(name)
def main():
    if len(sys.argv) != 3: raise ValueError("usage: publish SHA | rollback BACKUP")
    verb, arg = sys.argv[1:]
    if (site == pathlib.Path("/var/www/qianhao.ai") or backups == pathlib.Path("/var/www/backups")) and os.geteuid() != 0:
        raise ValueError("real roots require root")
    if verb == "rollback":
        candidate = pathlib.Path(arg)
        if not candidate.is_absolute(): candidate = backups / candidate
        if candidate.is_symlink(): raise ValueError("symlink backup rejected")
        source = candidate.resolve()
        if source.parent != backups or not re.fullmatch(pattern, source.name):
            raise ValueError("unsafe backup path")
        restore(source)
        print("ROLLBACK=" + str(source))
        return
    if verb != "publish" or not re.fullmatch(r"[0-9a-f]{40}", arg):
        raise ValueError("invalid command or SHA")
    with tempfile.TemporaryDirectory(dir=os.environ.get("WORK_ROOT")) as work:
        stage = pathlib.Path(work)
        # Spool stdin so both tar and gzip work without streaming extraction.
        archive = stage / "input.tar"
        with archive.open("wb") as out: shutil.copyfileobj(sys.stdin.buffer, out)
        with tarfile.open(archive, "r:*") as tar:
            seen = set()
            members = []
            for m in tar.getmembers():
                if m.name == "." and m.isdir(): continue
                if m.name not in FILES or not m.isfile() or m.name in seen or m.mode & 0o7111:
                    raise ValueError("unsafe archive member: " + m.name)
                seen.add(m.name)
                members.append(m)
            if seen != set(FILES): raise ValueError("archive must contain exactly five files")
            for m in members:
                with tar.extractfile(m) as inp, (stage / m.name).open("wb") as out:
                    shutil.copyfileobj(inp, out)
        expected = {f: digest(stage / f) for f in FILES}
        site.mkdir(parents=True, exist_ok=True)
        backups.mkdir(parents=True, exist_ok=True)
        # mkdir is exclusive: a same-second collision fails before touching live files.
        stamp = subprocess.check_output(["date", "+%Y%m%d-%H%M%S"], env={**os.environ, "TZ": "Asia/Shanghai"}, text=True).strip()
        backup = backups / ("qianhao.ai-pre-" + arg + "-" + stamp)
        shutil.copytree(site, backup, symlinks=True)
        # Refuse an incomplete backup before changing anything: rollback needs all five.
        for f in FILES:
            if not (backup / f).is_file() or (backup / f).is_symlink():
                raise ValueError("current site needs five regular files for rollback")
        try:
            for f in FILES: install(stage / f, site / f)
            for f in FILES:
                if digest(site / f) != expected[f]: raise ValueError("installed hash mismatch: " + f)
        except BaseException:
            restore(backup)
            raise
        print("SHA=" + arg)
        print("BACKUP=" + str(backup))
        for f in FILES: print(expected[f] + "  " + f)
try:
    main()
except Exception as exc:
    print("publish: " + str(exc), file=sys.stderr)
    sys.exit(1)
' "$@"
