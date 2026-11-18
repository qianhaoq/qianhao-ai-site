# qianhao.ai

钱浩的个人站，使用纯 HTML / CSS，无构建链、脚本或外部字体。

当前首页为作品集卡片式改版（2026-11-18），替换此前的单栏编辑式设计。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

访问 <http://127.0.0.1:8080>。GitHub Pages 项目子路径与域名根路径均使用相对样式、首页链接。

## 这次的设计取舍

- 桌面端（≥1024px）两栏：左栏固定显示简介、所在地与公司、页内导航和外链，右栏滚动展示内容；平板与手机为单栏，导航改为横向标签。
- 三个精选项目用大卡片，每张带一块纯 HTML/CSS 示意窗代替截图：Dota2.ai 为 README 中的命令行复盘输出节选，千浩翻译为双语对照网页，DuoRead 为阅读与笔记双栏。
- 新增“近期 Now”（标注更新日期，依据 GitHub 近期提交）和“开源工具”（codex-usage、codexignore-gen、devflow-gates、DSH 微信插件）。
- 中文为主，标题和项目一句话附英文。
- 文案只取自公开仓库 README 和已上线站点；不展示私有仓库细节、fork 和早期练习仓库。DuoRead 链接仍标注“隐私与支持”。
- 浅色与深色跟随系统；不加载外部字体、图片或脚本。整卡可点，卡内的次级链接独立可聚焦。
- 布局参考了 [Brittany Chiang](https://brittanychiang.com/) 的左侧固定简介 + 右侧滚动内容，以及 [Lee Robinson](https://leerob.com/) 的克制排版；没有复制参考站代码或视觉素材。

## 浏览器验收

2026-11-18 使用 Playwright 驱动的 Chromium headless shell，关闭页面 JavaScript 截图，并分别检查浅色与深色：

| 宽度 | 横向溢出 | 首张项目卡顶部（视口高 800 / 900） |
| --- | --- | --- |
| 320 | 无 | 538px |
| 375 | 无 | 511px |
| 390 | 无 | 511px |
| 768 | 无 | 546px |
| 1024 | 无 | 115px |
| 1440 | 无 | 115px |

390px 下 200% 放大（等效 195px 视口）无横向溢出。键盘 Tab 顺序：跳到正文 → 首页 → 页内导航 → GitHub / 博客 → 各卡片（每张卡片主链接一个焦点，次级链接各一个）→ 列表 → 回到顶部。页内全部外链在 2026-11-18 用 `curl` 核对，均返回 200。截图未提交到仓库。

## 页面与发布

公开链接沿用已核对的既有项目地址。修改样式时，同步把 index.html 的 styles.css 查询参数更新为该文件的 SHA-256：

```sh
python3 -c "import hashlib; print(hashlib.sha256(open('styles.css','rb').read()).hexdigest())"
```

站点资源为 index.html、styles.css、robots.txt、sitemap.xml。正式站的 Lightsail nginx 与 GitHub Pages 是独立发布路径，deploy/ 中仍保留原配置示例。本轮未修改部署流程、DNS、证书、服务器或权限设置。
