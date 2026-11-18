import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SmokeTests(unittest.TestCase):
    def test_public_urls_and_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            artifact = work / 'artifact'
            artifact.mkdir()
            (artifact / 'index.html').write_text('<link href="styles.css?v=123" rel="stylesheet">')
            for f in ('styles.css', 'index.md', 'robots.txt', 'sitemap.xml'):
                (artifact / f).write_text(f)
            curl = work / 'curl'
            curl.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
from urllib.parse import urlsplit
args = sys.argv[1:]
url = args[-1]
with open(os.environ['REQUEST_LOG'], 'a') as log: log.write(url + '\\n')
file = urlsplit(url).path.lstrip('/') or 'index.html'
mode = os.environ.get('FAIL_MODE', '')
if mode == 'network': sys.exit(22)
body = (pathlib.Path(os.environ['ARTIFACT']) / file).read_bytes()
pathlib.Path(args[args.index('-o') + 1]).write_bytes(b'wrong' if mode == 'hash' else body)
print('404' if mode == 'status' else '200', end='')
''')
            curl.chmod(0o755)
            log = work / 'requests'
            env = dict(os.environ, PATH=str(work) + os.pathsep + os.environ['PATH'],
                       ARTIFACT=str(artifact), REQUEST_LOG=str(log))
            result = subprocess.run(['bash', str(ROOT / 'deploy/smoke.sh'), str(artifact)],
                                    env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log.read_text().splitlines(), [
                'https://qianhao.ai/', 'https://qianhao.ai/index.html',
                'https://qianhao.ai/styles.css', 'https://qianhao.ai/index.md',
                'https://qianhao.ai/robots.txt', 'https://qianhao.ai/sitemap.xml',
                'https://qianhao.ai/styles.css?v=123'])
            for mode in ('network', 'status', 'hash'):
                with self.subTest(mode=mode):
                    result = subprocess.run(['bash', str(ROOT / 'deploy/smoke.sh'), str(artifact)],
                                            env=dict(env, FAIL_MODE=mode), capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
