import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PUBLISH = ROOT / 'deploy/qianhao-site-publish.sh'
WRAPPER = ROOT / 'deploy/qianhao-site-deploy-ssh.sh'
FILES = ('index.html', 'styles.css', 'index.md', 'robots.txt', 'sitemap.xml')
SHA = 'a' * 40


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.site = self.root / 'site'
        self.site.mkdir()
        self.backups = self.root / 'backups'
        for f in FILES:
            (self.site / f).write_text('old ' + f)
        (self.site / 'assets').mkdir()
        (self.site / 'assets/keep').write_text('keep')
        self.env = dict(os.environ, SITE_ROOT=str(self.site), BACKUP_ROOT=str(self.backups))

    def archive(self, extra=None, missing=None, gzip=False):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz' if gzip else 'w') as tar:
            for name in FILES:
                if name == missing:
                    continue
                body = ('new ' + name).encode()
                info = tarfile.TarInfo(name)
                info.size = len(body)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(body))
            if extra is not None:
                tar.addfile(extra, io.BytesIO(b'x' * extra.size))
        return data.getvalue()

    def run_publish(self, data=None, env=None):
        return subprocess.run([str(PUBLISH), 'publish', SHA], input=data or self.archive(),
                              env=env or self.env, capture_output=True)

    def assert_old(self):
        for f in FILES:
            self.assertEqual((self.site / f).read_text(), 'old ' + f)
        self.assertEqual((self.site / 'assets/keep').read_text(), 'keep')

    def test_publish_backup_and_rollback(self):
        result = self.run_publish(self.archive(gzip=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        backup = next(self.backups.iterdir())
        self.assertIn(('BACKUP=' + str(backup)).encode(), result.stdout)
        self.assertEqual((backup / 'assets/keep').read_text(), 'keep')
        for f in FILES:
            self.assertEqual((self.site / f).read_text(), 'new ' + f)
            self.assertEqual((self.site / f).stat().st_mode & 0o777, 0o644)
            self.assertIn(hashlib.sha256(('new ' + f).encode()).hexdigest().encode(), result.stdout)
        result = subprocess.run([str(PUBLISH), 'rollback', backup.name], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_old()

    def test_hash_failure_restores_backup(self):
        # Test-only Python startup hook corrupts one installed file exactly once.
        hook = self.root / 'hook'
        hook.mkdir()
        (hook / 'sitecustomize.py').write_text('''import os
from pathlib import Path
original = os.replace
fired = False
def replace(src, dst, *args, **kwargs):
    global fired
    original(src, dst, *args, **kwargs)
    if not fired and str(dst) == os.environ['SITE_ROOT'] + '/index.md':
        fired = True
        Path(dst).write_text('corrupt')
os.replace = replace
''')
        result = self.run_publish(env=dict(self.env, PYTHONPATH=str(hook)))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'hash mismatch', result.stderr)
        self.assertEqual(len(list(self.backups.iterdir())), 1)
        self.assert_old()

    def test_missing_artifact_is_rejected_before_changes(self):
        self.assertNotEqual(self.run_publish(self.archive(missing='index.md')).returncode, 0)
        self.assert_old()

    def test_hostile_archives(self):
        for name, kind in [('..', tarfile.REGTYPE), ('../escape', tarfile.REGTYPE),
                           ('/absolute', tarfile.REGTYPE), ('extra.txt', tarfile.REGTYPE),
                           ('index.html', tarfile.SYMTYPE), ('styles.css', tarfile.LNKTYPE),
                           ('assets', tarfile.DIRTYPE), ('./index.html', tarfile.REGTYPE)]:
            with self.subTest(name=name, kind=kind):
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '/etc/passwd' if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ''
                self.assertNotEqual(self.run_publish(self.archive(extra=member)).returncode, 0)
                self.assert_old()
        member = tarfile.TarInfo('index.html')
        member.mode = 0o755
        self.assertNotEqual(self.run_publish(self.archive(extra=member)).returncode, 0)

    def test_unsafe_rollback(self):
        self.assertEqual(self.run_publish().returncode, 0)
        backup = next(self.backups.iterdir())
        outside = self.root / backup.name
        outside.symlink_to(backup, target_is_directory=True)
        linked = self.backups / ('qianhao.ai-pre-' + 'b' * 40 + '-20260101-000000')
        linked.symlink_to(backup, target_is_directory=True)
        for target in ['/tmp', '../' + backup.name, str(outside), str(linked), 'bad;id']:
            result = subprocess.run([str(PUBLISH), 'rollback', target], env=self.env, capture_output=True)
            self.assertNotEqual(result.returncode, 0, target)
        (backup / 'index.md').unlink()
        result = subprocess.run([str(PUBLISH), 'rollback', str(backup)], env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        for f in FILES:
            self.assertEqual((self.site / f).read_text(), 'new ' + f)

    def test_forced_command(self):
        fake = self.root / 'publisher'
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        fake.chmod(0o755)
        backup = 'qianhao.ai-pre-' + SHA + '-20261119-120000'
        accepted = ['publish ' + SHA, 'rollback ' + backup, 'rollback ' + str(self.backups / backup)]
        rejected = ['', 'sh', 'publish ' + SHA.upper(), 'publish ' + SHA + '; id',
                    'publish ' + SHA + '\n', 'rollback /tmp/' + backup,
                    'rollback ' + str(self.backups / '..' / backup), 'rollback ' + backup + ' extra',
                    'rollback $(id)', 'publish ' + SHA + ' extra']
        for command in accepted + rejected:
            env = dict(self.env, SSH_ORIGINAL_COMMAND=command, PUBLISH_BIN=str(fake), SUDO='')
            result = subprocess.run([str(WRAPPER)], env=env, capture_output=True)
            self.assertEqual(result.returncode == 0, command in accepted, command)
            if command in accepted:
                self.assertEqual(result.stdout.decode().splitlines(), command.split(' '))


if __name__ == '__main__':
    unittest.main()
