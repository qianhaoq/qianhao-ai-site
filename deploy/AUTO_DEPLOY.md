# Lightsail 主动拉取发布

## 当前状态

正式站已发布 a780087。这里准备从 main 到正式站的持续发布流程，服务器安装和定时启用尚未执行。GitHub Pages 仍是独立预览站。

本方案不把 SSH 私钥、AWS 凭证或 GitHub token 放到服务器发布程序或 Actions 中，也不创建新用户、调整站点目录属主、开放端口或更改 DNS/TLS。服务器只匿名读取公开仓库；Actions 只读监测公开站点。

## 信任与权限边界

发布程序安装后固定为 root 所有、0555 的本地文件，不自动更新。它只把仓库的 index.html、styles.css、robots.txt、sitemap.xml 当作数据读取，绝不执行仓库中的脚本、安装依赖或运行构建命令。增加发布资源或升级发布程序需再次审查本机安装版本。

现有站点目录归 root 所有，因此 service 使用 root UID，能力集为空，禁止提权，系统文件只读，屏蔽 home，允许写入的持久路径仅为：

- /var/www/qianhao.ai：四个资源及不含凭证/内部路径的 deploy-status.json。
- /var/lib/qianhao-site-deploy：锁、状态、事务恢复记录和 history.jsonl。
- /var/backups/qianhao.ai/auto：每次有资源变化时的备份与指纹。

这是新增的常驻发布配置，安装并启用 service/timer 需要逐次明确确认。它不授予 GitHub 登录服务器的能力。systemd 限制的含义见官方 [执行环境文档](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)，计时语义见 [timer 文档](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)。

## 一轮发布

1. 定时器每五分钟唤醒一次固定的本地程序，带少量随机延迟。文件锁拒绝并发，重复执行保持幂等。
2. 读取 main 的完整 SHA；只有该 SHA 在 main 的 push 事件上通过 site-checks.yml，才准备新版本。
3. 读取该提交的 tree 和固定 SHA 的四个原始文件。拒绝符号链接、超限文件、损坏 Git blob、脚本内容及错误 canonical/robots/sitemap。原始文件始终按精确提交读取。
4. 提交更改在准备期间前进时放弃旧轮次。生产文件有手工漂移时停止，不覆盖未知改动。
5. 资源有变化时，先保存并核验完整四文件备份和旧状态，fsync 每个备份文件、manifest、备份子目录和备份父目录，之后才写入持久事务记录。每个文件用同目录临时文件和 replace 发布，样式先于首页；不声称四文件作为一个目录原子切换。
6. 核对磁盘和正式 HTTPS 四文件指纹，成功后记录 served_commit。无资源变化的文档提交只更新版本记录；相同提交只进行健康核验。
7. 写入或上线校验失败则恢复旧文件。中途被终止时，下轮从事务记录恢复；已经提交完成的事务不会被错误回滚。失败提交被阻止重复发布，新 main 或明确 retry 才能继续。

失败记录使用固定错误码，日志不打印凭证、请求环境或任意上游正文。发布文件上限为每份 256 KiB，HTTP 请求有大小和时间上限，拒绝重定向，固定访问 GitHub API、raw.githubusercontent.com 与 qianhao.ai。

## CSS 缓存

HTML 的 stylesheet 查询参数必须等于 styles.css 的 SHA-256，例如 styles.css?v=完整哈希。修改样式时一并更新该参数，CI 会拒绝过期缓存标记。这样返回用户也会请求对应版本样式，无需改 nginx 缓存配置或引入构建链。

~~~sh
python3 -c "import hashlib; print(hashlib.sha256(open('styles.css','rb').read()).hexdigest())"
~~~

唯一兼容例外是已人工验收的 a780087 四文件指纹，用于初次接管和回滚测试，不允许其他未带缓存版本的发布。

## 测试与非写入检查

~~~sh
python3 -m unittest discover -s deploy/tests -v
python3 deploy/auto_deploy.py validate-source --source .
systemd-analyze verify deploy/systemd/qianhao-site-deploy.service deploy/systemd/qianhao-site-deploy.timer
~~~

在生产安装前，把评审过的程序暂存到 ubuntu 用户的临时目录，先执行以下非写入检查；它只读取公开提交，不修改生产文件：

~~~sh
python3 /path/to/reviewed/auto_deploy.py inspect-commit --commit 完整已合并SHA
~~~

PR 的 CI 另做匿名只读公网检查。控制器尚未启用且状态为 404 时，固定核对已人工验收的 a780087 四文件；即使 main 已前进，也不会把待发布版本误当已发布版本。控制器存在后，检查其心跳、版本和当前 main 的资源。此检查只在 PR 事件执行；main 的 push 检查不能要求新版本已经上线，否则会与发布器等待 CI 形成循环依赖。

还需在实际服务器核对 Python/systemd 版本、四文件指纹和 unit 兼容性。此步骤不能用 CI 上的静态 unit 校验代替。

## 待确认的安装与启用动作

下面是一份安装清单，不是已经执行的记录。须先批准新增 root oneshot/timer 的限定用途与三个可写路径。所有来源文件来自同一个已评审提交，对照该提交成功 CI 日志中的三安装文件 SHA-256 校验后再复制；不从 main 动态下载程序直接执行。

~~~sh
test -d /usr/local/libexec || sudo install -d -m 0755 /usr/local/libexec
sudo install -d -m 0700 /var/lib/qianhao-site-deploy /var/backups/qianhao.ai/auto
sudo python3 - <<'PY'
import os
for path in ("/var/lib/qianhao-site-deploy", "/var/lib",
             "/var/backups/qianhao.ai/auto", "/var/backups/qianhao.ai", "/var/backups"):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
PY
sudo install -m 0555 deploy/auto_deploy.py /usr/local/libexec/qianhao-site-deploy.py
sudo install -m 0644 deploy/systemd/qianhao-site-deploy.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/qianhao-site-deploy.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/qianhao-site-deploy.service /etc/systemd/system/qianhao-site-deploy.timer
sudo systemctl daemon-reload
sudo systemctl start qianhao-site-deploy.service
sudo systemctl status qianhao-site-deploy.service --no-pager
~~~

仅当首次发布与公网验收成功后，再启用定时器：

~~~sh
sudo systemctl enable --now qianhao-site-deploy.timer
sudo systemctl list-timers qianhao-site-deploy.timer --all
~~~

预先创建并落盘状态与备份目录的父目录项，避免首次运行时仅有子目录数据已落盘。程序在受限 service 内不写这些父目录。/usr/local/libexec 如已存在则保留其权限；如不存在，须在同次确认的安装动作中以 root:root 0755 创建。程序、unit 和状态目录须保持 root 所有，不授予 www-data、ubuntu 或 CI 新的写入权限。启动失败时先查 journal 和事务记录，不重复覆盖文件或清除状态。

## 回滚与重试

auto 备份目录名为 UTC时间-目标SHA-随机后缀，manifest 包含此前 served_commit 和全部指纹。先列出并核对目标备份，再执行；不能传任意路径：

~~~sh
sudo python3 -I /usr/local/libexec/qianhao-site-deploy.py rollback --backup 备份目录名
~~~

程序校验当前文件、备份指纹及目录边界，先落盘 kind=rollback 事务，再恢复四文件，标记刚回滚的提交为 blocked。回滚在首次写入前或部分写入后中断时，下次运行都会完成回滚，不会将它当成已提交成功的发布。定时器不会重新发布同一失败提交；新的 main 可正常发布。确认故障原因已消除且 main 仍是同一 SHA 时，可明确重试：

~~~sh
sudo python3 -I /usr/local/libexec/qianhao-site-deploy.py retry --commit 完整失败SHA
sudo systemctl start qianhao-site-deploy.service
~~~

并发操作会被锁拒绝。存在未恢复事务或手工文件漂移时停止，由操作者先核查，不绕过保护。a780087 上线前的三文件备份仍使用 README 中记录的原始 rollback.py，此流程不改动或删除那份备份。

## 验证和失败通知

site-production-monitor.yml 每十五分钟先读取仓库内 deploy/monitor-config.json，初始 enabled=false，因此持续核验任务明确跳过。服务器安装、首次发布和公网验收完成后，再通过普通评审提交将 enabled 改为 true；无需仓库管理权限、secret 或新凭证。手动运行会始终执行严格监测，供启用验收使用。\n\n正式监测固定本轮 main，独立从公网核对四文件哈希；新提交有十五分钟发布宽限期，还校验 served_commit、失败状态及二十分钟心跳。

启用后的持续监测要求控制器状态存在；缺失、过期或失败都令任务失败。只有 PR 对既有站点的只读检查显式传入 --allow-missing-controller，才会在状态 404 时固定核对已批准 a780087，输出 awaiting_controller；不会宣称控制器已启用。定时监测不使用这个例外。\n\n启用顺序：合入经评审的流程代码（监测开关保持 false）→ 在服务器完成只读环境检查 → 经逐次确认安装受限 service/timer → 首次精确版本发布与公网验收 → 合入 enabled=true 的监测开关提交并验证其自动发布 → 手动严格监测及通知探针验收。启动时若 CI 工作流尚未进入 main 则等待，不绕过门禁。公开状态无需认证且不含内部路径。

监测失败会令 GitHub Actions 任务失败，使用仓库/账户已有的 Actions 失败通知机制；是否发邮件取决于当前通知设置，送达需启用时实际验证。普通监测通过后，可在 workflow_dispatch 手动选择 notification_probe：它只制造一个明确标注的失败运行，不改生产文件，用于检查现有通知送达。没有配置 SMTP、Slack/webhook 或新增通知密钥。服务器还保留 journal、状态和本地审计记录。源 API 暂时不可读时保留现有站点并报告，绝不为凑绿发布未经确认的版本。

如不批准常驻服务，继续使用已验证的逐次 SSH 发布。改用 GitHub 推送部署则需要另行确认受限部署身份及信任关系，不能把当前默认 Lightsail 私钥直接塞进 Actions。
