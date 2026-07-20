# Download WeChat Articles Skill

<p align="center">
  <strong>输入公众号名称，按时间范围批量归档公开文章。</strong><br>
  支持单账号、多账号、最近 N 天和指定日期，输出完整 HTML 与 Markdown 标题汇总。
</p>

<p align="center">
  Codex Skill + Python CLI · 登录态仅保存在本地 · 不需要目标公众号管理权限
</p>

## 微信交流

<table align="center">
  <tr>
    <td align="center">
      <img src="./docs/images/wechat-qr.png" alt="公众号文章下载 Skill 微信交流群二维码" width="220"><br>
      <sub>微信群：扫码加入 Codex Skill 与公众号采集交流</sub>
    </td>
    <td align="center">
      <img src="./docs/images/wechat.png" alt="作者个人微信二维码" width="220"><br>
      <sub>个人微信：添加时请备注“公众号 Skill”</sub>
    </td>
  </tr>
</table>

这个仓库同时提供：

- 可独立运行的 Python CLI。
- 可安装到 Codex 项目或全局目录的 `download-wechat-articles` Skill。
- 不需要目标公众号的管理权限，但需要你自己拥有一个可登录的微信公众平台账号。

> 请只用于归档公开文章，并遵守微信平台规则、著作权要求和当地法律。

## 功能

- 按公众号昵称或微信号搜索目标账号。
- 支持最近 1、3、7 天等任意天数。
- 支持 `YYYY-MM-DD` 起止日期。
- 同一条命令可重复传入多个 `--account`。
- 下载每篇文章的完整服务器 HTML 响应。
- 自动生成按公众号分组的 Markdown 标题汇总。
- 自动生成 `index.html` 和 `manifest.json`。
- 复用登录 Cookie，无需每次扫码。
- 兼容 [`1061700625/WeChat_Article`](https://github.com/1061700625/WeChat_Article) 生成的 `cookie.json`。
- 兼容旧版正文容器和微信新版客户端渲染 HTML。
- 一个公众号失败时，其他公众号仍会继续处理。

## 实现原理

1. 通过 Selenium 打开微信公众平台官网，由用户亲自扫码或登录。
2. 在本地保存后台 `token` 和 Cookie，文件权限尽量设为仅当前用户可读写。
3. 调用微信公众平台后台的公众号搜索和文章列表接口。
4. 按北京时间过滤文章发布时间，越过开始日期后提前停止翻页。
5. 下载命中文章并生成索引、清单和标题汇总。

微信后台接口并非公开稳定 API，平台改版后可能需要更新脚本。

## 环境要求

- Python 3.9 或更高版本。
- Google Chrome。
- 可登录 [微信公众平台](https://mp.weixin.qq.com/) 的账号，个人订阅号即可。
- 首次安装依赖和登录时需要网络连接。

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/aiwenjie777/download-wechat-articles-skill.git
cd download-wechat-articles-skill
```

### 2. 创建虚拟环境

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```bash
python -m pip install -r download-wechat-articles/scripts/requirements.txt
```

### 4. 首次登录

```bash
python download-wechat-articles/scripts/wechat_articles.py login \
  --auth .wechat-mp-auth.json
```

Chrome 打开后，在微信公众平台完成登录。脚本检测到后台首页后会自动保存登录态并关闭 Chrome。

`.wechat-mp-auth.json` 包含敏感 Cookie，已被本仓库的 `.gitignore` 忽略。不要将它发给其他人或提交到 Git。

### 5. 下载文章

下载单个公众号最近 7 天的文章：

```bash
python download-wechat-articles/scripts/wechat_articles.py download \
  --account "梁靠谱" \
  --days 7 \
  --auth .wechat-mp-auth.json \
  --output downloads/wechat
```

同时下载多个公众号最近 3 天的文章：

```bash
python download-wechat-articles/scripts/wechat_articles.py download \
  --account "梁靠谱" \
  --account "宝玉AI" \
  --account "数字生命卡兹克" \
  --days 3 \
  --auth .wechat-mp-auth.json \
  --output downloads/wechat
```

## 指定日期范围

```bash
python download-wechat-articles/scripts/wechat_articles.py download \
  --account "公众号名称" \
  --start 2026-07-01 \
  --end 2026-07-15 \
  --auth .wechat-mp-auth.json \
  --output downloads/wechat
```

- `--start` 必须与 `--days` 二选一。
- 只传 `--start` 时，结束日期默认为当天。
- “最近 N 天”按 `Asia/Shanghai` 时区的自然日包含计算。例如 7 月 21 日运行 `--days 3`，范围为 7 月 19 日 00:00:00 至 7 月 21 日 23:59:59。

## 登录态查找顺序

下载命令会按以下顺序查找登录文件：

1. `--auth PATH` 显式指定的文件。
2. `WECHAT_MP_AUTH_FILE` 环境变量。
3. 当前目录的 `.wechat-mp-auth.json`。
4. 当前目录的 `WeChat_Article/cookie.json`。

登录失效后，重新执行 `login` 命令覆盖本地登录文件即可。

## 输出结构

单个公众号：

```text
downloads/wechat/
└── 公众号名称/
    └── 2026-07-15_2026-07-21/
        ├── 2026-07-20_092005_文章标题.html
        ├── index.html
        ├── manifest.json
        └── 2026-07-21（最近7天）.md
```

多个公众号会保留每个账号的独立目录，并额外生成汇总目录：

```text
downloads/wechat/
├── 公众号A/...
├── 公众号B/...
└── 2026-07-19_2026-07-21/
    ├── manifest.json
    └── 2026-07-21（最近3天）.md
```

### Markdown 标题汇总

汇总文档按公众号分组，包含：

- 公众号名称及篇数。
- 文章标题。
- 北京时间发布时间。
- 可点击的微信原文链接。
- 抓取失败的公众号及原因。

### HTML 说明

HTML 文件保存微信服务器返回的完整页面，但图片、音频、视频和脚本仍可能引用微信远程资源，因此不保证完全离线。

## CLI 参数

### `login`

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `--auth` | `.wechat-mp-auth.json` | 登录态保存路径 |
| `--timeout` | `600` | 等待登录完成的秒数 |

### `download`

| 参数 | 必填 | 说明 |
|---|---:|---|
| `--account` | 是 | 公众号精确昵称或微信号；可重复传入 |
| `--days` | 二选一 | 包含当天的最近 N 个自然日 |
| `--start` | 二选一 | 开始日期，格式 `YYYY-MM-DD` |
| `--end` | 否 | 结束日期，格式 `YYYY-MM-DD` |
| `--auth` | 否 | 登录态文件路径 |
| `--output` | 否 | 输出根目录，默认 `downloads/wechat` |
| `--delay` | 否 | 请求间隔秒数，默认 `5`，最低 `1` |
| `--skip-auth-check` | 否 | 仅调试用；跳过下载前的登录态校验 |

退出码：

- `0`：全部成功。
- `1`：登录、参数或顶层请求错误。
- `2`：部分公众号或文章失败，其他结果已保留。

## 安装为 Codex Skill

### 项目级安装

在需要使用的项目根目录执行：

```bash
mkdir -p .codex/skills
cp -R /path/to/download-wechat-articles-skill/download-wechat-articles .codex/skills/
```

### 全局安装

```bash
mkdir -p ~/.codex/skills
cp -R download-wechat-articles ~/.codex/skills/
```

安装后可直接对 Codex 说：

```text
下载“梁靠谱”最近 7 天的公众号文章，保存为 HTML。
```

```text
查找“梁靠谱”、“宝玉AI”和“数字生命卡兹克”最近 3 天的文章，生成一份标题汇总。
```

Skill 会指导 Codex 使用仓库中的确定性脚本，而不是每次临时重写抓取逻辑。

## 运行测试

离线测试不会访问微信，也不需要 Cookie：

```bash
python download-wechat-articles/scripts/test_wechat_articles.py
```

测试覆盖：

- 最近 N 天的日期边界。
- 起止日期校验。
- 原 `WeChat_Article` Cookie 格式兼容。
- 文章时间过滤和提前停止分页。
- 旧版和新版微信文章 HTML 识别。
- 单账号与多账号 Markdown 汇总。
- HTML、索引和清单文件生成。

## 常见问题

### 提示登录失效

重新执行 `login` 命令，完成微信官方页面登录。

### 搜索到多个同名公众号

脚本不会在模糊结果中盲目选第一个。请改用完整精确昵称或公众号微信号。

### 出现“访问频繁”或频率控制

停止当前任务，稍后重试，并调大 `--delay`。不要轮换账号或尝试绕过平台控制。

### 文章 HTML 中的图片无法离线显示

当前版本保存的是服务器原始 HTML，其中资源可能仍指向微信 CDN。请在有网络时打开。

### Chrome 或 ChromeDriver 启动失败

先确认 Chrome 已安装且可正常启动。Selenium Manager 通常会自动处理匹配的驱动程序，首次运行可能需要下载驱动。

## 安全说明

- 不要在命令、Issue、聊天或日志中粘贴 Cookie 或 token。
- 不要将 `.wechat-mp-auth.json` 、`cookie.json` 或下载结果提交到公开仓库。
- “记住密码”不是本工具的必需功能；本工具不会询问或保存微信密码。
- 建议使用低频率、小时间窗和必要的公众号清单。
- 对第三方文章进行再发布或商业使用前，请自行确认授权。

## 项目结构

```text
download-wechat-articles-skill/
├── README.md
├── .gitignore
├── docs/
│   └── images/
│       ├── wechat-qr.png
│       └── wechat.png
└── download-wechat-articles/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    └── scripts/
        ├── requirements.txt
        ├── test_wechat_articles.py
        └── wechat_articles.py
```

## 致谢

公众号搜索和文章列表思路参考了 [`1061700625/WeChat_Article`](https://github.com/1061700625/WeChat_Article)。本项目对登录、日期过滤、多账号处理、文章页兼容、Markdown 汇总和安全输出进行了重新封装。
