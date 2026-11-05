# qianhao.ai

钱浩的个人站，使用纯 HTML / CSS，无构建链、脚本或外部字体。

本轮以已上线的 [GitHub Pages](https://qianhaoq.github.io/qianhao-ai-site/) 为基线，准备新的精简设计供评审。该基线对应合并版本 `a780087b56da04f235cce49a7c06136e0e4c4785`。本分支尚未合入或发布；Lightsail 自动发布工作暂缓。

## 本地预览

```sh
python3 -m http.server 8080 --bind 127.0.0.1
```

访问 <http://127.0.0.1:8080>。GitHub Pages 项目子路径与域名根路径均使用相对样式、首页链接。

## 这次的设计取舍

- 简短个人介绍之后直接展示三个精选项目：Dota2.ai、千浩翻译和 DuoRead。
- 其余项目保留在原生“更多项目”展开项中，写作保留博客与 AI DevFlow Weekly。
- 移除整屏 hero、重复口号、六张等权大卡和逐项重复的 GitHub 链接。
- 使用单栏、细分隔线、中性色和少量淡蓝；外链箭头由 CSS 绘制。
- DuoRead 的链接明确标注“隐私与支持”，不将支持页当作产品入口。
- 保留跳到正文、清晰焦点、减少动态效果、键盘可展开列表和现有 canonical。没有新增履历、数据或社交账号。

实际浏览并截图参考了 [Paco Coursey](https://paco.me/) 的短介绍与项目索引、[Brian Lovin](https://brianlovin.com/) 的直接信息层级，以及 [Lee Robinson](https://leerob.com/) 的简洁栏目结构。这里采用独立的中文排版和内容取舍，没有复制参考站代码或视觉素材。

## 浏览器验收

2026-11-05 使用隔离 Chrome 156.0.8078.80，关闭页面 JavaScript，完成：

| 宽度 | 横向溢出 | 首个项目顶部 | 第三个项目底部 |
| --- | --- | --- | --- |
| 320 | 无 | 277px | 575px |
| 375 | 无 | 277px | 546px |
| 390 | 无 | 277px | 546px |
| 768 | 无 | 310px | 599px |
| 1440 | 无 | 310px | 599px |

跳到正文、导航锚点、展开项的 Enter/Space、展开后 Tab 顺序、可见焦点均通过。390px 下 200% CSS 放大检查通过，无横向溢出。三个精选项目在手机首屏可见。

真实截图与浏览器 JSON 已保存到本次任务工作区 `evidence/site-editorial/`。执行环境随后断开，截图暂未上传到仓库，Mac 上最后一轮外链 HTTP 复核尚未执行。云端替代检查已确认 GitHub 账户及两个公开仓库；其余七个站外地址被云端访问器限制，不能据此认定链接失效或验收通过。最终代码额外为样式链接添加内容哈希查询参数，样式及页面正文与截图验收版本相同。

## 页面与发布

公开链接沿用已核对的既有项目地址。修改样式时，同步把 index.html 的 styles.css 查询参数更新为该文件的 SHA-256：

```sh
python3 -c "import hashlib; print(hashlib.sha256(open('styles.css','rb').read()).hexdigest())"
```

站点资源为 index.html、styles.css、robots.txt、sitemap.xml。正式站的 Lightsail nginx 与 GitHub Pages 是独立发布路径，deploy/ 中仍保留原配置示例。本轮只准备 draft PR，未修改部署流程、DNS、证书、服务器或权限设置。
