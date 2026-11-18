# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

仓库协作约定见 @AGENTS.md（编码代理选择、PR 合并流程、哪些事必须找钱浩确认），以下不重复。

## 概览

qianhao.ai 个人站的静态源：纯 HTML / CSS，无构建链、无 JavaScript、无外部字体，没有测试或 lint 工具。站点资源只有 `index.html`、`styles.css`、`robots.txt`、`sitemap.xml`；`deploy/` 下是 nginx / Caddy 的**示例**配置，不是实际在用的部署。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

## 改样式时必须同步的缓存参数

`index.html` 引用 `styles.css?v=<sha256>`，查询参数必须等于 `styles.css` 当前内容的 SHA-256。每次改 `styles.css` 后重新计算并更新 `index.html`：

```sh
python3 -c "import hashlib; print(hashlib.sha256(open('styles.css','rb').read()).hexdigest())"
```

## 结构与约束

- 页面需同时在 GitHub Pages 项目子路径（`qianhaoq.github.io/qianhao-ai-site/`）和域名根路径下工作，所以样式与首页链接都用相对路径（`styles.css`、`./`），不要改成以 `/` 开头。
- canonical、`og:url`、`sitemap.xml`、`robots.txt` 指向 `https://qianhao.ai/`。
- 页面结构：≥1024px 两栏，左栏 `.side` sticky（印章字标、00 写在前面、近期 2 条、外链），右栏 `main` 为 01 作品（Dota2.ai、千浩翻译两张卡片，带纯 CSS 示意窗）→ 02 更多（`.index` 索引表，含其他产品与开源工具）→ 03 写作（周刊最近 3 期 + 博客入口）；<1024px 单栏，按 DOM 顺序排列，不要用 `order` 让视觉顺序和 Tab 顺序不一致。
- 整卡可点：卡片标题 `.card-link::after` 覆盖整卡，卡内其他链接（`.sub-links`）和终端示意窗用 `z-index: 1` 浮在覆盖层之上。
- `index.md` 是首页的 Markdown 版，改首页文字或链接时同步改它。
- 视觉记号是朱红印章（`.seal`），全站只有一个强调色 `--accent`；不加逐行英文副标题。
- 内容只取公开来源（公开仓库 README、已上线站点）；私有仓库不展示细节。“近期 Now”带更新日期，改内容时同步更新。
- 外链箭头由 CSS 绘制（`.external` + `<span class="arrow" aria-hidden="true">`）；DuoRead 链接标注为“隐私与支持”，不要当作产品入口。
- 无障碍要求需保持：跳到正文链接、可见焦点、`prefers-reduced-motion`、可见文字与可访问名称一致（不要用 `aria-label` 覆盖掉可见标签文字）。
- 所在地与公司（上海 · 美团）已经钱浩确认可展示；不新增其他履历、数据或社交账号等未经确认的内容。
- 正式站（Lightsail nginx）与 GitHub Pages 是两条独立发布路径；不要改部署流程、DNS、证书或服务器配置。

## 验收方式（参考 README）

改版式后在关闭 JavaScript 的浏览器中，按浅色和深色两种模式检查 320 / 375 / 390 / 768 / 1024 / 1440 宽度：无横向溢出、手机首屏能看到第一张项目卡片、Tab 顺序正确（每张卡片只占一个焦点），以及 390px 下 200% 放大无横向溢出。
