# qianhao.ai

钱浩个人站的静态源，使用纯 HTML / CSS，无构建链。正式目标为 AWS Lightsail 东京自托管。

在仓库根目录本地预览：

```sh
python3 -m http.server 8080
```

访问 <http://localhost:8080>。

`deploy/` 提供 nginx 和 Caddy 配置示例，部署时二选一，并按实际路径调整。nginx 示例需先用 Certbot / Let's Encrypt 准备证书；Caddy 可自动管理 HTTPS。静态根目录只需放置 `index.html`、`styles.css`、`robots.txt`。

当前未挂域名、未切 qianhao.ai DNS；可选 GitHub Pages 仅作预览。DuoRead 隐私与支持仍指向现有 GitHub Pages，正式 `/duoread` 尚未切到本域。

生产切流、下单 AWS 须钱浩确认。
