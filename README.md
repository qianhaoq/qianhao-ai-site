# qianhao.ai

钱浩（Qian Hao）的个人主页，线上地址 <https://qianhao.ai/>。

这是一个单页静态网站，介绍本人，并列出在做的项目、开源工具和写作入口。整个站只有手写的 HTML 和 CSS：

- 没有构建步骤，仓库里的文件就是线上的文件；
- 没有 JavaScript，也不加载外部字体、图片或第三方服务；
- 浅色和深色模式跟随访问者的系统设置。

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
| `robots.txt`、`sitemap.xml` | 给搜索引擎用，指向 `https://qianhao.ai/` |
| `deploy/` | nginx 和 Caddy 的配置**示例**，不会被自动使用，服务器上的实际配置以服务器为准 |
| `AGENTS.md`、`CLAUDE.md` | 给 AI 编码代理的协作约定 |

## 页面长什么样

电脑上（宽度 ≥1024px）分左右两栏：

- **左栏固定不动**：姓名、一句话身份（中英文）、上海 · 美团、页内导航、GitHub 和博客链接。
- **右栏随页面滚动**，从上到下依次是：

| 区块 | 锚点 | 内容 |
| --- | --- | --- |
| 精选项目 | `#projects` | Dota2.ai、千浩翻译、DuoRead 三张大卡片，每张顶部有一块用 HTML/CSS 画的示意图（终端输出、双语网页、阅读与笔记双栏），不用截图 |
| 更多产品 | `#projects` 内 | 拼好运 · 好运贴、求职聚合 |
| 近期在做 | `#now` | 标有更新日期的时间线 |
| 开源工具 | `#open-source` | codex-usage、codexignore-gen、devflow-gates、DSH 微信插件 |
| 写作 | `#writing` | 个人博客、AI DevFlow Weekly |

手机和平板上（宽度 <1024px）变成单栏：左栏内容排在最上面，导航变成一排可点的标签。

## 怎么改内容

**原则：文案只取自公开来源**，比如公开仓库的 README 和已经上线的网站。不写未经确认的履历或数据，不展示私有仓库的细节。

### 改文字或链接

直接编辑 `index.html`。外链文字后面的箭头由 CSS 画出，新增外链时照抄这个写法：

```html
<a class="external" href="https://example.com">名称<span class="arrow" aria-hidden="true"></span></a>
```

### 新增一个开源工具

在 `#open-source` 区块的 `<ul class="grid">` 里复制一个 `<li class="card mini">`，然后改名称、链接、一句话描述和语言。语言圆点颜色目前有 `py`、`js`、`ts` 三种，其他语言在 `styles.css` 里照着 `.lang-dot.py` 加一条即可。

### 更新“近期在做”

编辑 `#now` 区块的列表，同时把上方 `<time datetime="2026-11">` 的日期改成当前年月。

### 新增一张精选项目卡片

复制一个 `<article class="card feature">`。整张卡片能点击，原理是：标题链接带 `class="card-link"`，它的 `::after` 伪元素铺满整张卡片。所以：

- 每张卡片只能有**一个** `card-link`；
- 卡片里的其他链接要放进 `<ul class="sub-links">`，它们层级更高，可以单独点击；
- 只起装饰作用的示意图加 `aria-hidden="true"`，避免读屏软件读出无意义的内容。

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

2026-11-18 对当前版本做过上述全部检查，均通过，19 个外链都返回 200。

## 发布到正式站

正式站跑在 AWS Lightsail（东京）的 nginx 上，网站文件放在服务器的 `/var/www/qianhao.ai`。

**合并到 `main` 不会自动更新正式站**，仓库里也没有自动发布流程，需要在能 SSH 到服务器的机器上手动发布。只替换静态文件，不需要改 DNS、证书或 nginx 配置，也不用重启服务。

在本仓库的 `main` 分支下运行（把 `user` 换成服务器上的用户名）：

```sh
git pull
SERVER=user@43.207.221.125

# 1. 把四个文件传到服务器的临时目录
ssh $SERVER 'mkdir -p ~/qianhao-release'
scp styles.css index.html robots.txt sitemap.xml $SERVER:~/qianhao-release/

# 2. 先备份线上文件，再替换（先换样式，再换页面）
ssh $SERVER 'set -e
  B=/var/backups/qianhao.ai/pre-$(date -u +%Y%m%dT%H%M%SZ)
  sudo mkdir -p "$B" && sudo cp -a /var/www/qianhao.ai/. "$B"/
  cd ~/qianhao-release
  sudo install -m 644 styles.css /var/www/qianhao.ai/
  sudo install -m 644 index.html robots.txt sitemap.xml /var/www/qianhao.ai/
  echo "备份在 $B"'

# 3. 从公网核对：每行应为 200，且线上与本地的哈希一致
for f in index.html styles.css robots.txt sitemap.xml; do
  printf '%s  ' "$(curl -s -o /dev/null -w '%{http_code}' https://qianhao.ai/$f)"
  printf '线上 %s  ' "$(curl -s https://qianhao.ai/$f | sha256sum | cut -c1-12)"
  echo "本地 $(sha256sum $f | cut -c1-12)  $f"
done
```

最后用手机打开 <https://qianhao.ai/> 看一遍。如果还是旧页面，先强制刷新再看。

**回滚**：第 2 步会打印备份目录，把里面的文件拷回去即可：

```sh
ssh $SERVER 'sudo cp -a <备份目录>/. /var/www/qianhao.ai/'
```

更早一次正式发布的完整记录和回滚脚本见 PR #2。

修改 DNS、证书或服务器配置，或者购买 AWS 资源，都需要钱浩确认。

### 发布状态

截至 2026-11-18，`main` 上是作品集卡片式改版（PR #5、#6），正式站还停留在 PR #1 的版本（`a780087`），尚未发布。发布完成后请更新这一段。

GitHub Pages（<https://qianhaoq.github.io/qianhao-ai-site/>）目前没有开启，访问会返回 404。

## 设计参考

布局借鉴了 [Brittany Chiang](https://brittanychiang.com/) 的“左侧固定简介 + 右侧滚动内容”，排版借鉴了 [Lee Robinson](https://leerob.com/) 的克制风格。只参考了结构思路，没有复制代码或视觉素材。
