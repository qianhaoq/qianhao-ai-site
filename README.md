# qianhao.ai

钱浩个人站的静态源，使用纯 HTML / CSS，无构建链。正式目标为 AWS Lightsail 东京自托管。

在仓库根目录本地预览：

```sh
python3 -m http.server 8080
```

访问 <http://localhost:8080>。

`deploy/` 提供 nginx 和 Caddy 配置示例，部署时二选一，并按实际路径调整。nginx 示例需先用 Certbot / Let's Encrypt 准备证书；Caddy 可自动管理 HTTPS。静态根目录只需放置 `index.html`、`styles.css`、`robots.txt`。

## 内容与发布状态

首页包含个人介绍、六个产品与开源项目、写作及公开仓库入口。页面使用系统字体，无脚本、外部字体或构建依赖，支持手机布局、键盘焦点、跳到正文与减少动态效果偏好。

正式域名为 <https://qianhao.ai/>，现有站点已可通过 HTTPS 访问。仓库更新、PR 合入与生产部署是独立步骤；本次改版尚未部署。DuoRead 隐私与支持仍指向现有 GitHub Pages，未迁移至 `/duoread`。

部署静态根目录还应包含 `sitemap.xml`。发布前检查 375、390、768、1440 像素布局、键盘导航、内部锚点和公开链接。上线后核对首页、样式、robots、sitemap 的状态码及 canonical；保留上一版本静态目录，以便恢复文件后重新加载服务。

生产切流、下单 AWS 须钱浩确认。
