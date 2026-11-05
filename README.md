# qianhao.ai

钱浩个人站的静态源，使用纯 HTML / CSS，无构建链。生产环境为 AWS Lightsail 东京上的 nginx；GitHub Pages 提供独立预览站。

在仓库根目录本地预览：

```sh
python3 -m http.server 8080
```

访问 <http://localhost:8080>。

`deploy/` 提供 nginx 和 Caddy 配置示例，按实际路径调整。生产当前使用 nginx 与已有的 Certbot / Let's Encrypt 证书；Caddy 仅为替代方案示例。静态根目录包含 `index.html`、`styles.css`、`robots.txt`、`sitemap.xml`。

## 内容与发布状态

首页包含个人介绍、六个产品与开源项目、写作及公开仓库入口。页面使用系统字体，无脚本、外部字体或构建依赖，支持手机布局、键盘焦点、跳到正文与减少动态效果偏好。

正式域名为 <https://qianhao.ai/>。PR #1 的合并版本 `a780087b56da04f235cce49a7c06136e0e4c4785` 已于 2026-11-05 00:46 UTC 部署至 `/var/www/qianhao.ai`。公网四个资源的 SHA-256 均与该合并版本一致；375、390、768、1440 像素布局、键盘和导航检查通过，15 个唯一公开外链均返回 200。DuoRead 隐私与支持仍指向现有 GitHub Pages，未迁移至 `/duoread`。

## 两条发布路径

- [GitHub Pages 预览](https://qianhaoq.github.io/qianhao-ai-site/)随 `main` 更新自动构建。该版本的[部署运行](https://github.com/qianhaoq/qianhao-ai-site/actions/runs/41942199100)已成功。
- 正式域名由独立的 Lightsail nginx 服务提供。Pages 成功不会同步正式服务器；本次通过现有 SSH 身份执行有备份和文件指纹校验的发布。仓库当前没有 GitHub Actions 到 Lightsail 的持续发布工作流。

今后发布时，从确认过的提交打包上述四个资源，核实生产当前版本，备份站点后再发布；样式先于首页替换。发布后从公网核对四个资源的状态码、哈希、canonical、手机布局和导航。本次只更新静态文件，沿用现有 DNS、证书及 nginx 配置，无需重启服务。

## 本次回滚

上一版本保存在生产服务器的 `/var/backups/qianhao.ai/pre-a780087-20261105T004623Z-_lv5c1tn`。目录内有受限的 `rollback.py` 和指纹记录。在服务器执行：

```sh
sudo python3 /var/backups/qianhao.ai/pre-a780087-20261105T004623Z-_lv5c1tn/rollback.py rollback /var/backups/qianhao.ai/pre-a780087-20261105T004623Z-_lv5c1tn
```

回滚脚本先确认线上仍为该次发布，再恢复旧版三份文件并移除当时不存在的 sitemap，随后核验旧版指纹；若线上已是其他版本则停止。本次已在临时目录演练正常发布、幂等重复执行、主动回滚及首次写入后失败恢复。

生产切流、下单 AWS 须钱浩确认。
