# qianhao.ai

钱浩（Qian Hao）的个人主页，线上地址 <https://qianhao.ai/>。

这是一个单页静态网站，介绍本人，并列出在做的项目、开源工具和写作入口。整个站只有手写的 HTML 和 CSS：

- 没有构建步骤，仓库里的文件就是线上的文件；
- 没有 JavaScript，也不加载外部字体、图片或第三方服务；
- 浅色和深色模式跟随访问者的系统设置；
- 唯一的视觉记号是左上角的朱红印章“钱浩”，强调色也只有这一种朱红。

## 快速上手

```sh
git clone https://github.com/qianhaoq/qianhao-ai-site.git
cd qianhao-ai-site
python3 -m http.server 8080 --bind 127.0.0.1
```

浏览器打开 <http://127.0.0.1:8080>。修改文件后刷新页面就能看到效果。

## 仓库里有什么

| 文件 | 用途 |
| --- | --- |
| `index.html` | 唯一的页面，所有文字和链接都在这里 |
| `styles.css` | 全部样式。颜色写在文件开头的 `:root` 变量中，深色模式在紧跟其后的 `prefers-color-scheme: dark` 里 |
| `index.md` | 首页的 Markdown 版，给 AI 和脚本读；首页内容变了要同步改这里 |
| `robots.txt`、`sitemap.xml` | 给搜索引擎用，指向 `https://qianhao.ai/` |
| `deploy/` | nginx 和 Caddy 的配置**示例**，不会被自动使用，服务器上的实际配置以服务器为准 |
| `AGENTS.md`、`CLAUDE.md` | 给 AI 编码代理的协作约定 |

## 页面长什么样

电脑上（宽度 ≥1024px）分左右两栏：

- **左栏固定不动**（`.side`）：印章和域名、`00 / 写在前面`（第一人称简介）、近期在做（2 条，标注年月）、底部的 GitHub / 博客 / index.md 链接。
- **右栏随页面滚动**（`main`）：

| 编号 | 区块 | 内容 |
| --- | --- | --- |
| 01 | 作品 | Dota2.ai、千浩翻译两张大卡片，顶部各有一块 HTML/CSS 画的示意图（终端输出、双语网页） |
| 02 | 更多 | 一张索引表：拼好运、求职聚合、DuoRead 和 4 个开源工具，每行标注类型 |
| 03 | 写作 | AI DevFlow Weekly（列出最近 3 期和 RSS），下面是个人博客入口 |

手机和平板上（宽度 <1024px）是单栏，按页面源码顺序从上到下排列：简介 → 近期 → 链接 → 01 → 02 → 03。视觉顺序和 Tab 键顺序保持一致，所以不要用 CSS 的 `order` 打乱顺序。

## 怎么改内容

**原则：文案只取自公开来源**，比如公开仓库的 README 和已经上线的网站。不写未经确认的履历或数据，不展示私有仓库的细节。

### 改文字或链接

直接编辑 `index.html`。外链文字后面的箭头由 CSS 画出，新增外链时照抄这个写法：

```html
<a class="external" href="https://example.com">名称<span class="arrow" aria-hidden="true"></span></a>
```

### 在“更多”里加一项

在 `02 / 更多` 的 `<ul class="index">` 里复制一行 `<li>`，改链接、名称（`.name`）、类型（`.kind`，例如“开源 · Python”）和一句描述（`.desc`）。

### 更新“近期”和周刊

- **近期**：在左栏 `.now` 里改，最多保留 2 条，不要和“作品”重复；同时把 `<time datetime="2026-11">` 改成当前年月。
- **周刊**：每出一期新周刊，在 `03 / 写作` 的 `<ol class="issues">` 顶部加一行，删掉最后一行，保持 3 期。期号和链接从 <https://qianhaoq.github.io/ai-devflow-weekly/> 抄。

### 新增一张作品卡片

“作品”只放有公开入口、能直接用的产品，目前是两张。复制一个 `<article class="card">`。整张卡片能点击，原理是：标题链接带 `class="card-link"`，它的 `::after` 伪元素铺满整张卡片。所以：

- 每张卡片只能有**一个** `card-link`；
- 卡片里的其他链接要放进 `<ul class="sub-links">`，它们层级更高，可以单独点击；
- 只起装饰作用的示意图加 `aria-hidden="true"`，避免读屏软件读出无意义的内容。

### 同步 index.md

改了首页的文字或链接后，把同样的改动写进 `index.md`。

### 改样式

编辑 `styles.css` 之后，**一定要**同步更新 `index.html` 里 `styles.css?v=` 后面的那串字符。它是样式文件内容的 SHA-256，用来让访问者的浏览器丢掉旧缓存：

```sh
python3 -c "import hashlib; print(hashlib.sha256(open('styles.css','rb').read()).hexdigest())"
```

另外，样式和首页链接要用相对路径（`styles.css`、`./`），不要写成以 `/` 开头。

## 提交前检查

只改了文字的话，本地预览看一眼即可。改了布局或样式，请在**关闭 JavaScript** 的浏览器里，浅色和深色模式各检查一遍：

- [ ] 宽度 320、375、390、768、1024、1440 下都没有横向滚动条
- [ ] 手机首屏能看到第一张项目卡片
- [ ] 390px 宽度放大到 200% 仍没有横向滚动条
- [ ] 只用 Tab 键浏览：第一个焦点是“跳到正文”，焦点框清晰可见，每张卡片只占一个焦点
- [ ] 所有外链都能打开，可以用下面的命令批量检查，每行开头应为 `200`：

```sh
grep -o 'href="https[^"]*"' index.html | sort -u | cut -d'"' -f2 \
  | while read u; do echo "$(curl -s -o /dev/null -w '%{http_code}' -L -m 15 "$u") $u"; done
```

2026-11-18 对当前版本做过上述全部检查，均通过，22 个外链都返回 200。

## 发布到正式站

正式站跑在 AWS Lightsail（东京）的 nginx 上，网站根目录为 `/var/www/qianhao.ai`，备份放在 `/var/www/backups/`。

完成 [一次性服务器设置](deploy/server-setup.md) 并配置仓库 secret `DEPLOY_SSH_KEY` 后，推送到 `main` 会通过 GitHub Actions 自动发布。PR 只跑本地检查，不发布。工作流下载触发提交 SHA 的归档，无构建，只发布 `index.html`、`styles.css`、`index.md`、`robots.txt`、`sitemap.xml`；排队期间已被新提交取代的任务会成功跳过。不会删除已有的 `assets/` 等额外文件，也不用重启 nginx。

发布前完整备份到 `/var/www/backups/qianhao.ai-pre-<sha>-<北京时间 YYYYMMDD-HHMMSS>`，先替换样式，再替换其余四个文件，权限均为 644。服务器核对五个文件的 SHA-256，失败自动恢复；CI 随后从公网 HTTPS 检查状态码和正文哈希（包括首页及带版本号的样式 URL），失败会请求回滚并标记发布失败。

手动发布也使用相同入口。在要发布的提交下运行（密钥必须是专用部署密钥，主机密钥使用仓库固定值）：

```sh
SHA=$(git rev-parse HEAD)
git archive "$SHA" index.html styles.css index.md robots.txt sitemap.xml |
  ssh -i /path/to/deploy-key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile=deploy/known_hosts -o BatchMode=yes \
    qianhao-deploy@43.207.221.125 "publish $SHA"
```

保存输出中的 `BACKUP=` 路径。需要回滚时，使用相同 SSH 选项，将远端命令改为 `rollback qianhao.ai-pre-<sha>-<stamp>`。回滚只恢复五个站点文件，不清除额外资产。手动发布后也需核对公网正文哈希，并用手机打开 <https://qianhao.ai/> 检查。

nginx 默认 MIME 表可能不包含 `.md`。检查 `curl -sI https://qianhao.ai/index.md` 的 `Content-Type`；如需改为 `text/markdown` 或 `text/plain`，应由操作员核实服务器实际配置。`deploy/nginx.conf.example` 和 `deploy/Caddyfile.example` 只是示例，不是线上配置。

自动发布只在完成一次性服务器设置、配置好 `DEPLOY_SSH_KEY`、并且本工作流已合入 `main` 之后才会触发。在 GitHub Actions 首次成功运行、且公网文件哈希与该提交产物一致之前，不要默认正式站已经自动更新。

GitHub Pages（<https://qianhaoq.github.io/qianhao-ai-site/>）目前没有开启，访问会返回 404。

生产切流、修改 DNS、证书或服务器配置，以及购买 AWS 资源，仍须钱浩确认。

## 设计取舍

参考了 [杨攀](https://yangpan.com/) 的“名片 + 索引”结构（第一人称开头、编号区块、给 AI 读的 `index.md`），并请一位独立评审对比了 yangpan.com、qiaomu.ai、guizang.ai 和 nexttoken.tv。结论：

- 内容体量小（几个产品、一份周刊、博客刚起步），所以不做乔木式的数据墙和多栏门户，也不做歸藏式的资讯流；
- 只保留有真实入口的两个产品作为大卡片，其他产品和开源工具合并成一张索引表；
- 周刊是持续更新的内容，放到写作区最显眼的位置，博客只留入口；
- 去掉逐行英文副标题、技术标签胶囊和重复条目；
- 视觉上只用一个朱红强调色和一枚印章，字体全部使用系统字体（正文无衬线、标签等宽、印章宋体），不加载外部字体。

只借鉴了结构思路，没有复制参考站的代码或视觉素材。
