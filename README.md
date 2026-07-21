# 微信公众号文章下载助手

<p align="center">
  <strong>告诉 Codex 公众号名称和时间，它帮你把文章整理好。</strong><br>
  不用写代码，不用学命令，也不用一篇一篇复制。
</p>

<p align="center">
  可以同时查多个公众号 · 可以选最近几天 · 自动生成标题汇总和完整网页
</p>

## 微信交流

<table align="center">
  <tr>
    <td align="center">
      <img src="./docs/images/wechat-qr.png" alt="公众号文章下载 Skill 微信交流群二维码" width="220"><br>
      <sub>微信群：扫码加入交流</sub>
    </td>
    <td align="center">
      <img src="./docs/images/wechat.png" alt="作者个人微信二维码" width="220"><br>
      <sub>个人微信：添加时请备注“公众号 Skill”</sub>
    </td>
  </tr>
</table>

> 微信群二维码有时效性。如果群码已失效，请添加右侧个人微信，备注“公众号 Skill”，邀请进群。

## 它能帮你做什么

你可以直接对 Codex 说：

> 帮我找“家松AI智能体”最近 7 天的公众号文章。

它会自动帮你：

- 找到正确的公众号。
- 只收集你指定时间内的文章。
- 保存每篇文章的完整网页。
- 整理一份“标题、发布时间、原文链接”汇总。
- 把结果文件直接发给你。

也可以一次找多个公众号：

> 帮我找“AI私域文姐”、“玺树AI”和“家松AI智能体”最近 3 天的文章，生成一份标题汇总。

## 30 秒开始

### 第一步：让 Codex 安装

把下面这句话复制到 Codex 对话框：

> 请帮我安装这个 Skill：https://github.com/aiwenjie777/download-wechat-articles-skill/tree/main/download-wechat-articles

Codex 会自动帮你完成安装。安装成功后，下一条消息就可以直接使用。

### 第二步：告诉 Codex 你要找什么

例如：

> 找“家松AI智能体”最近 7 天的文章。

或者：

> 找“AI私域文姐”、“玺树AI”和“家松AI智能体”最近 3 天的文章。

也可以选具体日期：

> 找“家松AI智能体”从 2026 年 7 月 1 日到 7 月 15 日发布的文章。

就这么简单。

## 第一次使用时，你需要做什么

第一次运行时，Codex 会请求你同意安装必要组件，并打开 Chrome。

你只需要：

1. 点击同意。
2. 在打开的微信公众平台官方页面中扫码或登录。
3. 等待 Codex 整理完成。

不需要把微信密码发给 Codex。

登录成功后，以后会自动复用本地登录状态，不需要每次扫码。只有微信要求重新登录时，才需要再扫一次。

## 你会得到什么

### 1. 标题汇总

一份可以直接打开的 Markdown 文档，按公众号分组，里面有：

- 文章标题。
- 发布时间。
- 可点击的微信原文链接。
- 每个公众号发了多少篇。

文件名会像这样：

```text
2026-07-21（最近3天）.md
```

### 2. 每篇文章的完整网页

每篇文章会单独保存，方便你查看、归档和后续整理。

### 3. 一个简单索引

打开 `index.html`，就能看到这次收集的文章列表。

## 常见用法

### 找一个公众号

> 找“家松AI智能体”最近 7 天的文章。

### 同时找多个公众号

> 找“AI私域文姐”、“玺树AI”和“家松AI智能体”最近 3 天的文章。

### 自定义时间

> 找“家松AI智能体”从 7 月 1 日到 7 月 15 日的文章。

### 只想整理标题

> 找这 5 个公众号最近 3 天的文章，把标题、时间和原文链接整理成一份 Markdown。

## 使用前需要知道

- 你需要有一个能登录微信公众平台的账号，个人订阅号也可以。
- 要收集的目标公众号不需要是你自己的。
- 这个工具只收集公开文章，不能获取粉丝、私信、草稿或其他后台隐私数据。
- 请遵守微信平台规则和著作权要求。
- 微信页面或规则发生变化时，工具可能需要更新。

## 常见问题

### 需要会编程吗？

不需要。安装好 Skill 以后，直接用普通话告诉 Codex 你想找哪些公众号和哪段时间。

### 需要目标公众号的密码吗？

不需要。你只需要登录自己的微信公众平台账号。

### 每次都要扫码吗？

不用。第一次登录后会保存本地登录状态。失效后，Codex 会提示你重新登录。

### 可以一次找多个公众号吗？

可以。直接在一句话中写出多个公众号名称即可。结果会按公众号分组。

### 某个公众号显示 0 篇，是失败了吗？

不一定。如果没有错误提示，通常表示该公众号在指定时间内没有发布新文章。

### 出现“访问频繁”怎么办？

先停一会再试。不要连续反复点击，也不要用多个账号轮换尝试。

## 隐私与安全

- 登录状态只保存在你自己的电脑上。
- 不要把 `.wechat-mp-auth.json` 或 `cookie.json` 发给其他人。
- Codex 不需要知道你的微信密码。
- 对文章进行转载、再发布或商业使用前，请自行确认授权。

<details>
<summary><strong>开发者与命令行说明（普通用户不需要打开）</strong></summary>

### 环境要求

- Python 3.9 或更高版本。
- Google Chrome。
- 可登录微信公众平台的账号。

### 手动安装

```bash
git clone https://github.com/aiwenjie777/download-wechat-articles-skill.git
cd download-wechat-articles-skill
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r download-wechat-articles/scripts/requirements.txt
```

Windows PowerShell 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
```

### 手动登录

```bash
python download-wechat-articles/scripts/wechat_articles.py login \
  --auth .wechat-mp-auth.json
```

### 手动下载

```bash
python download-wechat-articles/scripts/wechat_articles.py download \
  --account "AI私域文姐" \
  --account "玺树AI" \
  --account "家松AI智能体" \
  --days 3 \
  --auth .wechat-mp-auth.json \
  --output downloads/wechat
```

指定日期：

```bash
python download-wechat-articles/scripts/wechat_articles.py download \
  --account "公众号名称" \
  --start 2026-07-01 \
  --end 2026-07-15 \
  --auth .wechat-mp-auth.json \
  --output downloads/wechat
```

### 运行测试

```bash
python download-wechat-articles/scripts/test_wechat_articles.py
```

### 工作原理

Skill 通过 Selenium 打开微信公众平台官方页面，由用户完成登录，然后使用已授权的后台会话搜索公众号和文章列表。按北京时间过滤文章后，保存 HTML 并生成汇总文件。

微信后台接口不是公开稳定 API，平台改版后可能需要更新脚本。

### 项目结构

```text
download-wechat-articles-skill/
├── README.md
├── docs/images/
└── download-wechat-articles/
    ├── SKILL.md
    ├── agents/openai.yaml
    └── scripts/
        ├── requirements.txt
        ├── test_wechat_articles.py
        └── wechat_articles.py
```

</details>

## 致谢

公众号搜索和文章列表思路参考了 [`1061700625/WeChat_Article`](https://github.com/1061700625/WeChat_Article)。

---

请只用于收集公开文章，并遵守微信平台规则、著作权要求和当地法律。
