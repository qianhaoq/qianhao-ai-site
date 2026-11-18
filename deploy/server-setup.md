# One-time server setup

These are operator instructions, not an instruction to change production now.
Obtain Qian Hao's confirmation before changing the production server. Use the
existing admin access only for this setup, never its ubuntu Lightsail PEM in CI.
Target SSH at **43.207.221.125**, not the public hostname (which may be proxied).
The examples in this directory are not live nginx/Caddy configuration.

The host needs bash, Python 3, coreutils, sudo and OpenSSH. Keep the existing
nginx configuration and all live assets. Verify all five current site files
exist and are regular files before enabling publishing. The publisher runs as
root against `/var/www/qianhao.ai`, with full backups in `/var/www/backups`.

1. Create a dedicated `qianhao-deploy` user with a locked password and no
   interactive SSH access. OpenSSH needs an executable login shell (e.g.
   `/bin/sh`) to launch a forced command; `/usr/sbin/nologin` would also block
   deployment. Enforce the noninteractive policy with the root-owned authorized
   key below and, preferably, an sshd `Match User qianhao-deploy` block with
   `ForceCommand /usr/local/bin/qianhao-site-deploy-ssh`, `DisableForwarding yes`,
   `PermitTTY no`, `PasswordAuthentication no`, and
   `KbdInteractiveAuthentication no`. Validate with `sshd -t` before reloading;
   retain the existing admin session while testing.
2. Make the user's home and `.ssh` directory root-owned and not writable by the
   deploy user (home 755, `.ssh` 755). Make `authorized_keys` root-owned, mode
   644: it contains only a public key, and sshd must be able to read it. Add the
   **dedicated public key** as one line, replacing the placeholder:

   ```text
   restrict,command="/usr/local/bin/qianhao-site-deploy-ssh",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 <DEDICATED_PUBLIC_KEY> qianhao-actions
   ```

3. Install reviewed scripts from this repository, root-owned and mode 755:

   ```sh
   sudo install -o root -g root -m 755 deploy/qianhao-site-publish.sh /usr/local/bin/qianhao-site-publish
   sudo install -o root -g root -m 755 deploy/qianhao-site-deploy-ssh.sh /usr/local/bin/qianhao-site-deploy-ssh
   ```

   Neither script, its parent directories nor the backup/web roots may be
   writable by `qianhao-deploy`. Do not configure sudo `SETENV`; the test-only
   environment overrides must not be supplied through SSH or sudo in production.
4. Using `visudo -f /etc/sudoers.d/qianhao-site-deploy`, install this root-owned
   mode 440 drop-in; validate with `sudo visudo -c`:

   ```sudoers
   qianhao-deploy ALL=(root) NOPASSWD: /usr/local/bin/qianhao-site-publish
   ```

5. Generate a fresh dedicated key on a trusted operator machine. Add its private
   key **only** to the GitHub repository Actions secret **DEPLOY_SSH_KEY** (private
   key text only). Never put private keys in this repository or reuse the ubuntu
   admin PEM. The workflow hardcodes the deploy user and IP and pins the supplied
   public host keys in `deploy/known_hosts`; verify fingerprints with trusted
   admin access before use. Do not replace pins with a runtime keyscan.

Publish accepts a tar/tgz containing exactly the five site files. Output includes
`SHA=`, `BACKUP=` and the five SHA-256 hashes. Rollback accepts the printed backup
path or basename, restoring only those five files. Keep backups until an operator
chooses a retention policy. CI serializes deployment; do not run manual publish
or rollback concurrently with CI. Check public HTTPS and the `.md` MIME type as
described in README; MIME changes require review of the actual nginx config.

To undo setup, first disable the workflow/remove its secret, remove the dedicated
public key and sudoers drop-in, revert the sshd Match block (validate/reload), then
remove the dedicated user and two installed scripts. Keep live files and backups;
removing deployment access does not roll back the site. To undo a release, invoke
`rollback <printed-backup-basename>` through the same forced SSH entry first.
