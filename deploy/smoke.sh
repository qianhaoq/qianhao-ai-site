#!/usr/bin/env bash
set -euo pipefail
artifact=${1:?artifact directory required}
body=$(mktemp)
trap 'rm -f "$body"' EXIT
check() {
  local path=$1 file=$2 code expected actual
  code=$(curl --silent --show-error --fail --max-time 30 --retry 2 -H 'Cache-Control: no-cache' -o "$body" -w '%{http_code}' "https://qianhao.ai/$path")
  [[ $code == 200 ]] || return 1
  expected=$(sha256sum "$artifact/$file" | cut -d' ' -f1)
  actual=$(sha256sum "$body" | cut -d' ' -f1)
  [[ $expected == "$actual" ]] || { echo "HTTPS hash mismatch: $path" >&2; return 1; }
}
# Explicit returns matter because this script is also useful inside conditionals.
check '' index.html || exit 1
for file in index.html styles.css index.md robots.txt sitemap.xml; do
  check "$file" "$file" || exit 1
done
while IFS= read -r css; do
  check "$css" styles.css || exit 1
done < <(python3 - "$artifact/index.html" <<'PY'
from html.parser import HTMLParser
import re, sys
class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == 'href' and value and re.fullmatch(r'(?:\./)?styles\.css\?v=[A-Za-z0-9._~-]+', value):
                print(value)
Links().feed(open(sys.argv[1]).read())
PY
)
