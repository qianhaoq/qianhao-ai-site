# qianhao.ai

钱浩（Qian Hao）的个人站：<https://qianhao.ai/>

一个单页静态网站，用于介绍本人、展示在做的项目、开源工具和写作入口。只有手写的 HTML 和 CSS：没有构建步骤、没有 JavaScript、没有外部字体或图片，打开文件就是最终产物。

## 目录

| 文件 | 作用 |
| --- | --- |
| `index.html` | 唯一的页面，全部内容都在这里 |
| `styles.css` | 全部样式，包括浅色和深色两套配色 |
| `robots.txt`、`sitemap.xml` | 搜索引擎配置，指向 `https://qianhao.ai/` |
| `deploy/` | nginx / Caddy 配置**示例**，仅供参考，不会被自动使用 |
| `AGENTS.md`、`CLAUDE.md` | 给 AI 编码代理看的协作约定 |

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

然后打开 <http://127.0.0.1:8080>。改完文件刷新浏览器即可，不需要重启。

## 页面结构

宽屏（≥1024px）分两栏：

- **左栏**固定不动：姓名、一句话身份、所在地与公司、页内导航、GitHub 和博客链接。
- **右栏**随页面滚动，依次是：
  1. **精选项目**：Dota2.ai、千浩翻译、DuoRead 三张大卡片。每张顶部有一块用 HTML/CSS 画的示意图（终端输出、双语网页、阅读笔记双栏），不使用截图。
  2. **更多产品**：拼好运、求职聚合。
  3. **近期在做（Now）**：带更新日期的时间线。
  4. **开源工具**：公开仓库的小卡片。
  5. **写作**：个人博客和 AI DevFlow Weekly。

窄屏（<1024px）变为单栏，左栏内容放在最上面，导航变成一排可点的标签。

几个需要知道的实现细节：

- **整张卡片可点击**：卡片标题的链接带 `class="card-link"`，它的 `::after` 伪元素铺满整张卡片。卡片里的其他链接放在 `.sub-links` 中，层级更高，所以可以单独点击。
- **外链箭头**由 CSS 画出：在链接文字后加 `<span class="arrow" aria-hidden="true"></span>`。
- **导航高亮**用 CSS 的 `:has(:target)` 实现，不需要脚本。
- **深色模式**跟随系统设置，颜色都在 `styles.css` 顶部的 `:root` 变量里。

## 常见修改

**改文案或链接**：直接编辑 `index.html`。所有内容只取自公开来源（公开仓库的 README、已上线的网站），不写未经确认的履历或数据，也不展示私有仓库的细节。

**新增一个开源工具**：在 `#open-source` 区块的 `<ul class="grid">` 里复制一个 `<li class="card mini">`，改名称、链接、一句描述和语言标签。语言圆点的颜色类有 `py`、`js`、`ts`，需要其他语言时在 `styles.css` 里补一个 `.lang-dot.xx`。

**更新“近期在做”**：编辑 `#now` 区块的列表，同时把 `<time datetime="...">` 改成当前年月。

**改样式**：编辑 `styles.css` 后，**必须**同步更新 `index.html` 中 `styles.css?v=` 后面的值，否则访问者的浏览器可能继续用旧缓存。这个值是文件内容的 SHA-256：

```sh
python3 -c "import hashlib; print(hashlib.sha256(open('styles.css','rb').read()).hexdigest())"
```

**路径要用相对路径**：样式写 `styles.css`、首页链接写 `./`，不要以 `/` 开头，这样页面在域名根路径和子路径下都能正常显示。

## 提交前检查

改动布局后，在关闭 JavaScript 的浏览器里，浅色和深色模式各看一遍：

- 宽度 320、375、390、768、1024、1440 下没有横向滚动条；
- 手机首屏能看到第一张项目卡片；
- 390px 宽度下放大到 200% 也没有横向滚动；
- 只用键盘按 Tab：先出现“跳到正文”，焦点框清晰可见，每张卡片只占一个焦点；
- 页面里所有外链都能打开（可以用下面的命令批量检查）：

```sh
grep -o 'href="https[^"]*"' index.html | sort -u | cut -d'"' -f2 \
  | while read u; do echo "$(curl -s -o /dev/null -w '%{http_code}' -L -m 15 "$u") $u"; done
```

最近一次检查于 2026-11-18：上述各项均通过，19 个外链都返回 200。

## 部署

正式站 `qianhao.ai` 运行在 AWS Lightsail（东京）的 nginx 上，网站文件放在服务器的 `/var/www/qianhao.ai`。**合并到 `main` 不会自动更新正式站**，仓库里也没有自动发布流程，需要手动发布：

1. 确认要发布的提交已合并到 `main`；
2. 在服务器上先备份 `/var/www/qianhao.ai` 当前的文件；
3. 上传 `styles.css`，再上传 `index.html`、`robots.txt`、`sitemap.xml`（先传样式，避免新页面配旧样式）；
4. 在公网检查四个文件都返回 200、内容哈希与提交一致，并在手机宽度下看一遍页面。

只替换静态文件即可，不需要改 DNS、证书或 nginx 配置，也不需要重启服务。上一次正式发布的记录与回滚方法见 PR #2。

GitHub Pages 预览地址 <https://qianhaoq.github.io/qianhao-ai-site/> 目前返回 404，仓库没有开启 Pages。

修改 DNS、证书、服务器或购买 AWS 资源都需要钱浩确认。

## 设计参考

布局参考 [Brittany Chiang](https://brittanychiang.com/) 的“左侧固定简介 + 右侧滚动内容”，排版参考 [Lee Robinson](https://leerob.com/) 的克制风格。只借鉴了结构思路，没有复制代码或视觉素材。
