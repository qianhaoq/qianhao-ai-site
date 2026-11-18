#!/usr/bin/env bash
set -euo pipefail
command=${SSH_ORIGINAL_COMMAND:-}
backup_root=${BACKUP_ROOT:-/var/www/backups}
backup_pattern='qianhao\.ai-pre-[0-9a-f]{40}-[0-9]{8}-[0-9]{6}'
if [[ $command =~ ^publish\ ([0-9a-f]{40})$ ]]; then
  args=(publish "${BASH_REMATCH[1]}")
elif [[ $command =~ ^rollback\ (.+)$ ]]; then
  target=${BASH_REMATCH[1]}
  name=${target##*/}
  if [[ ! $name =~ ^${backup_pattern}$ ]] || [[ $target != "$name" && $target != "$backup_root/$name" ]]; then
    echo 'Rejected backup path' >&2; exit 1
  fi
  args=(rollback "$target")
else
  echo 'Rejected SSH command' >&2; exit 1
fi
publish_bin=${PUBLISH_BIN:-/usr/local/bin/qianhao-site-publish}
if [[ ${SUDO-sudo} == '' ]]; then
  exec "$publish_bin" "${args[@]}"
fi
exec "${SUDO:-sudo}" -n -- "$publish_bin" "${args[@]}"
