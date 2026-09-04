# 使用指南(USAGE)

> 📘 **本手册聚焦命令行参考**。如需面向初学者的完整教程,请阅读
> [USER_GUIDE.md](./USER_GUIDE.md)。

本文档是 `wrg` 命令行的逐参数参考手册,涵盖每个子命令、典型工作流与进阶技巧。

## 目录

1. [全局选项](#全局选项)
2. [典型工作流](#典型工作流)
3. [子命令详解](#子命令详解)
4. [v0.2 / v0.3 新增命令](#v02--v03-新增命令)
5. [配置文件](#配置文件)
6. [邮件草稿格式](#邮件草稿格式)
7. [常见问题](#常见问题)

---

## 全局选项

```bash
wrg --help            # 帮助
wrg --version         # 版本(wrg 0.3.0)
wrg <command> --help  # 查看子命令帮助
```

每个子命令都接受 `--case-dir / -d`,默认 `./cases/default`。

---

## 典型工作流

```bash
# 1. 创建案件
wrg init --case-dir ./cases/case-2024-09-acme

# 2. 准备案件基本信息(可选:手工编辑 case_info.json)

# 3. 导入证据
wrg add-evidence ./evidence/contract.pdf --tag 合同
wrg add-evidence ./evidence/salary.jpg --tag 工资 --desc 9月工资条
echo "微信沟通记录..." | wrg add-text --name wechat.txt --tag 沟通

# 4. 浏览目标机构
wrg list-institutions
wrg search --keyword ILO

# 5. 生成邮件草稿
wrg generate \
    -i "ILO - 日内瓦总部" \
    -i "中华全国总工会" \
    --violation "拖欠工资:9月至今未发:15000"

# 6. 用邮件客户端打开 .eml 文件(Thunderbird、Outlook 等)人工检查后发送
ls cases/case-2024-09-acme/mails/
```

完整教程参见 [USER_GUIDE.md](./USER_GUIDE.md)。

---

## 子命令详解

### init

初始化一个案件目录。

```bash
wrg init --case-dir <PATH>
wrg init --case-dir <PATH> --non-interactive            # 空字段初始化(便于脚本)
wrg init --case-dir <PATH> --force                      # 覆盖已有 case_info.json
wrg init --case-dir <PATH> --use-global-defaults        # 用 ~/.wrg/config.yaml 中的 defaults
```

初始化后会生成:

```
<case-dir>/
├── case_info.json          # 案件基本信息
└── evidence/               # 空目录(后续导入证据时自动填充)
```

`case_info.json` 字段:

| 字段 | 说明 |
|---|---|
| `company_name` | 被投诉单位 |
| `company_address` | 单位地址 |
| `company_legal_person` | 法定代表人 |
| `company_credit_code` | 统一社会信用代码 |
| `company_phone` | 单位电话 |
| `worker_name` | 投诉人姓名 |
| `worker_phone` | 联系电话 |
| `worker_email` | 电子邮箱 |
| `worker_id` | 身份证号(可空) |
| `entry_date` | 入职时间 |
| `job_position` | 岗位 |
| `contract_status` | 合同签订情况 |
| `violations` | 违法事实列表(可空) |
| `created_at` | 创建时间(ISO 8601) |

### add-evidence

从文件导入证据。

```bash
wrg add-evidence <PATH> [--desc "..."] [--tag 标签1 --tag 标签2]
```

支持的文件类型:image(JPG/PNG/GIF/BMP/WebP/HEIC)、document(PDF/DOC/DOCX/XLS/XLSX/PPT/PPTX)、audio(MP3/WAV/AAC/M4A/OGG/FLAC)、video(MP4/AVI/MOV/MKV/FLV/WMV)、text(TXT/MD/CSV/JSON)。

文件会自动复制到 `<case-dir>/evidence/`,并计算 SHA-256 校验和。

### add-text

添加一段文本作为证据(聊天记录等)。

```bash
# 命令行参数
wrg add-text --name chat.txt --content "聊天内容..."

# 从 stdin 读取(支持管道)
echo "聊天内容..." | wrg add-text --name chat.txt

# 交互式
wrg add-text --name memo.txt --content "$(cat memo.txt)"
```

### list-evidence

列出当前案件的证据。

```bash
wrg list-evidence                        # 全部
wrg list-evidence --type image           # 仅图片
wrg list-evidence --tag 工资             # 仅标签匹配
wrg list-evidence --type document --tag 合同
```

### remove-evidence

根据 ID 删除证据(含磁盘文件)。

```bash
wrg remove-evidence <EVIDENCE_ID>        # 需确认
wrg remove-evidence <EVIDENCE_ID> --yes  # 跳过确认
```

### verify

校验所有证据文件的 SHA-256 是否仍与索引一致。可用于检测证据是否被篡改。

```bash
wrg verify
```

退出码:全部 OK 时为 0;存在篡改时非 0。

### list-institutions

```bash
wrg list-institutions                       # 监督机构
wrg list-institutions --media               # 媒体联系方式
wrg list-institutions --category china      # 单类别
wrg list-institutions --category usa
```

### search

```bash
wrg search --keyword ILO                    # 按关键词
wrg search --keyword 劳动                   # 中文关键词
wrg search --scope USA                      # 按 scope 过滤
wrg search --category international --keyword ILO
```

### types

列出支持的申诉类型。

```bash
wrg types
```

### generate

生成举报邮件草稿。

```bash
wrg generate \
    -i "机构A" -i "机构B" \
    --violation "类型:描述[:金额]" \
    [--violation ...] \
    [--lang zh] [--lang en] [--lang ja] [--lang ko] \
    [--format eml|txt|both] \
    [--from-addr "anonymous@..."] \
    [--summary|--no-summary] \
    [--interactive|-I] \
    [--word|--no-word]
```

`--violation` 格式:**`类型:描述[:金额]`**(用半角冒号分隔)。

例如:

```bash
wrg generate \
    -i "ILO - 日内瓦总部" \
    --violation "拖欠工资:9月至今未发:15000元" \
    --violation "违法加班:连续4周强制每日加班4小时"
```

输出位置:`<case-dir>/mails/<机构名>_<语言>.eml` 与 `<机构名>_<语言>.txt`。

**注意**:工具**不发送邮件**。请用任意邮件客户端(Thunderbird / Outlook / mutt)人工检查
`.eml` 后再投递。

### summary

打印案件摘要。

```bash
wrg summary
```

---

## v0.2 / v0.3 新增命令

### wizard

交互式向导:补全机构、违法事实、语言,然后调用 `generate`。

```bash
wrg wizard --case-dir <DIR>
```

### play

按剧本批量生成邮件。

```bash
wrg play <scenario.yaml> --case-dir <DIR> [--format eml|txt|both]
```

剧本示例见 `config/scenarios/wage_default.yaml` 与 `injury_default.yaml`。

### preview

生成本地 HTML 预览(仅本地,绝不联网)。

```bash
wrg preview --case-dir <DIR> [--lang zh|en|ja|ko] [-o OUT.html]
```

默认输出到 `<case>/reports/preview_<lang>.html`,浏览器打开即可。

### archive

案件打包 / 校验 / 解压。

```bash
# 打包成 zip(含 manifest.json + manifest.sha256)
wrg archive pack --case-dir <DIR> -o <OUT.zip> [--level 0-9] [--yes]

# 加密打包(需要 cryptography)
wrg archive pack --case-dir <DIR> -o <OUT.zip> --encrypt [--password PWD] [--yes]

# 校验完整性
wrg archive verify <FILE.zip>

# 解压
wrg archive extract <FILE.zip|.enc> -o <OUT_DIR> [--yes] [--password PWD]
```

### validate

校验 YAML/JSON 文件结构。

```bash
wrg validate case <case_info.json>
wrg validate scenario <scenario.yaml>
wrg validate institutions <institutions.yaml>
```

### config

管理全局配置(`~/.wrg/config.yaml`)。

```bash
wrg config init [--yes]
wrg config set <key> <value>
wrg config get <key>
wrg config show
wrg config path
```

支持自动类型转换:`true/false` 转布尔,数字转 int/float。

### completion

生成 shell 自动补全脚本。

```bash
wrg completion bash > ~/.wrg_completion.bash
wrg completion zsh > "${fpath[1]}/_wrg"
wrg completion fish > ~/.config/fish/completions/wrg.fish
```

---

## 配置文件

### 全局配置 `~/.wrg/config.yaml`

```yaml
default_lang: zh              # 默认邮件语言
from_addr: anon@worker.local  # 默认发件人
defaults:                     # init --use-global-defaults 使用的默认值
  worker_name: ""
  company_name: ""
recipient_pool_favorites:     # 收藏的常用机构(预留)
  - ILO - 日内瓦总部
  - BBC News
```

### 自定义 YAML 路径(API)

```python
from wrg.institution_db import InstitutionDB

db = InstitutionDB(config_dir="/path/to/your/config")
```

### 自定义模板目录(API)

```python
from wrg.template_engine import TemplateEngine

eng = TemplateEngine(template_dir="/path/to/templates")
```

---

## 邮件草稿格式

生成的 `.eml` 文件是标准的 RFC 5322 multipart/alternative 邮件,包含:

- `Subject:` 主题
- `From:` 草稿 From(默认 `anonymous@worker.local`,可改)
- `To:` 收件人邮箱
- `Date:` 生成时间
- 正文(text/plain + text/html 双格式,主流邮件客户端自动选择渲染版本)
- 附件:所有已添加的证据文件

可被 Thunderbird / mutt / Outlook / Apple Mail 直接打开。

`.txt` 文件是方便人工预览的纯文本版本,包含收件人、主题、机构、语言、附件数量、正文。

---

## 常见问题

### Q1:为什么工具不发邮件?

自动发送邮件存在三大风险:

1. **法律风险**:不同国家 / 地区对群发邮件、跨境数据有不同法规;
2. **误发风险**:参数错配可能导致邮件被误投;
3. **滥用风险**:工具被恶意使用时,自动发送会扩大危害。

因此工具只生成 `.eml` 草稿,由用户在邮件客户端人工核查后投递。

### Q2:如何修改收件人邮箱?

直接编辑 `config/institutions.yaml` 或 `config/media_contacts.yaml`。详见
[RECIPIENTS_MAINTENANCE.md](./RECIPIENTS_MAINTENANCE.md)。

### Q3:如何添加新语言模板?

在 `config/templates/<lang>/` 下放置 `<name>.jinja2` 与 `<name>.html.jinja2` 两个文件,
然后:

```bash
wrg generate --lang <lang> ...
```

模板字段详见 [USER_GUIDE.md § Q6](./USER_GUIDE.md)。

### Q4:如何在 CI 中使用?

```bash
wrg init --case-dir ./cases/ci --non-interactive --force
# ... 用脚本填充 case_info.json、调用 add-evidence ...
wrg generate --case-dir ./cases/ci -i "X" --violation "..."
```

### Q5:数据保存在哪里?

所有数据均在当前工作目录的 `<case-dir>/` 内。
全局配置在 `~/.wrg/config.yaml`(可选)。
删除这两个位置即可彻底清除所有痕迹。

工具不写入 `~/.config/`、`~/Library/`、注册表等全局位置,也无任何遥测。

### Q6:如何离线校验 / 验证文件?

```bash
# 校验案件 YAML/JSON
wrg validate case <case_info.json>
wrg validate institutions <institutions.yaml>

# 校验证据完整性
wrg verify

# 校验归档完整性
wrg archive verify <file.zip>
```
