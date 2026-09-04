# 🛡️ Worker Rights Guardian（工人权益守护）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](./tests)

一个 Python 开源 CLI 工具，辅助劳动者依法整理证据、生成规范的举报邮件草稿。
收件人覆盖**中国监督机构、联合国 / ILO、美国、欧盟、英国、日本、韩国、澳大利亚、新西兰**及
**欧美澳新日韩主流媒体**。

> ⚖️ **免责声明**：本工具仅作为辅助整理材料之用，**不构成法律建议**。
> 请依法维权，必要时咨询专业律师。

---

## ✨ 功能特性

- 📁 **证据管理**：支持图片、文档、音视频、文本等多种格式，自动计算 SHA-256 校验和
- 📝 **智能模板**：Jinja2 多语言邮件模板（中文 / 英文 / 日文 / 韩文），含富文本 HTML 格式
- 🏛️ **机构数据库**：内置中国 / 国际 / 美 / 欧 / 英 / 日韩 / 澳新监督机构 46+ 家
- 📺 **媒体数据库**：内置欧美澳新日韩等 18+ 家主流媒体联系方式
- 🔒 **隐私保护**：全本地运行，无任何网络上报；案件可 AES-256-GCM 加密打包
- 🌐 **国际化**：中英日韩四语模板，CLI 支持中英文案
- 🚫 **不自动发送**：只生成 `.eml` / `.txt` 草稿，由用户人工核查后再投递
- ✅ **完整性校验**：`wrg verify` 检测证据篡改；`wrg archive verify` 校验归档 SHA-256
- 🧰 **剧本与向导**：`wrg play` 一键按剧本生成多封邮件；`wrg wizard` 交互式向导
- 📦 **案件打包**：整案 ZIP + SHA-256 清单 + 可选加密，便于备份与分享
- 🔍 **格式校验**：`wrg validate` 在使用前检查 case_info / scenario / institutions 文件
- 🖥️ **Shell 补全**：支持 bash / zsh / fish 命令行自动补全

---

## 📦 安装

### 方式一：pip 安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/ZEatlon/worker-rights-guardian.git
cd worker-rights-guardian

# 安装（开发模式）
pip install -e .

# 或安装 + 测试依赖
pip install -e ".[dev]"
```

### 方式二：直接运行

```bash
# 至少安装运行时依赖
pip install PyYAML Jinja2 click rich

# 把 src/ 加入 PYTHONPATH 后调用
python -m wrg.cli --help
```

### 系统要求

- Python 3.10 或更高
- Linux / macOS / Windows 均可
- **无需联网**

---

## 🚀 快速开始

> 📘 **新手必读** — 完整 5 分钟教程、场景演练与 FAQ，见 [docs/USER_GUIDE.md](docs/USER_GUIDE.md)。
> 📖 **参数参考** — 每个命令的详细参数，见 [docs/USAGE.md](docs/USAGE.md)。

### 1. 初始化案件

```bash
wrg init --case-dir ./cases/my-case
```

按提示填写被投诉单位、投诉人基本信息等。也可加上 `--non-interactive` 用空字段初始化
（便于 CI 与脚本）。

### 2. 添加证据

```bash
# 添加工资条截图
wrg add-evidence ./salary_sep.png --desc "2024年9月工资条" --tag 工资

# 添加劳动合同 PDF
wrg add-evidence ./contract.pdf --desc "劳动合同"

# 添加聊天记录（从 stdin）
echo "2024-09-15 HR: 工资会晚点发" | wrg add-text --name chat.txt --desc 微信沟通

# 添加文字证据（直接命令行给出内容）
wrg add-text --name memo.txt --content "现场记录..." --desc 现场记录
```

### 3. 列出证据

```bash
wrg list-evidence
wrg list-evidence --type image --tag 工资
```

### 4. 校验完整性

```bash
wrg verify
```

### 5. 浏览与搜索机构

```bash
# 列出所有监督机构（分类显示）
wrg list-institutions

# 列出媒体联系方式
wrg list-institutions --media

# 只看某类别
wrg list-institutions --category china
wrg list-institutions --category usa

# 搜索
wrg search --keyword ILO
wrg search --keyword 劳动监察
wrg search --keyword DOL --scope USA
```

### 6. 生成举报邮件草稿

```bash
# 给 ILO 发邮件
wrg generate \
    -i "ILO - 日内瓦总部" \
    --violation "拖欠工资:9月至今未发放:15000" \
    --no-summary

# 同时发给多个机构
wrg generate \
    -i "ILO - 日内瓦总部" \
    -i "北京市劳动保障监察总队" \
    -i "BBC News" \
    --violation "拖欠工资:9月至今未发放:15000" \
    --violation "违法加班:连续4周强制每日加班4小时:0"

# 输出为 .txt 而非 .eml
wrg generate -i "中华全国总工会" --format txt --violation "..."
```

邮件草稿保存在 `<case_dir>/mails/` 目录下，文件名形如
`ILO_-_日内瓦总部_zh.eml` 与 `ILO_-_日内瓦总部_zh.txt`。

### 7. 案件摘要

```bash
wrg summary
```

---

## 📋 支持的申诉类型

| 代码 | 中文 | English |
|---|---|---|
| `wage` | 拖欠工资 | Wage Theft |
| `overtime` | 违法加班 | Excessive Overtime |
| `injury` | 工伤 / 职业危害 | Occupational Injury |
| `discrim` | 歧视 / 性骚扰 | Discrimination / Harassment |
| `contract` | 违法解雇 | Wrongful Termination |
| `social` | 拒缴社保 | Social Insurance Evasion |
| `child` | 使用童工 | Child Labor |
| `forced` | 强迫劳动 | Forced Labor |
| `safety` | 安全生产违法 | Workplace Safety |
| `union` | 阻挠工会 / 集体谈判 | Anti-Union |
| `other` | 其他 | Other |

运行 `wrg types` 查看完整列表。

---

## 📂 项目结构

```
worker-rights-guardian/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── e2e_demo.py
├── e2e_v03_demo.py
├── config/
│   ├── institutions.yaml        # 监督机构数据库（46+ 家）
│   ├── media_contacts.yaml      # 媒体联系方式
│   ├── scenarios/               # 剧本（yaml）
│   │   ├── wage_default.yaml
│   │   └── injury_default.yaml
│   └── templates/               # 邮件模板
│       ├── zh/labor_complaint.{jinja2,html.jinja2}
│       ├── en/labor_complaint.{jinja2,html.jinja2}
│       ├── ja/labor_complaint.{jinja2,html.jinja2}
│       └── ko/labor_complaint.{jinja2,html.jinja2}
├── src/wrg/
│   ├── __init__.py
│   ├── cli.py                    # 命令行入口（13+ 子命令）
│   ├── evidence.py               # 证据管理
│   ├── institution_db.py         # 机构数据库
│   ├── mail_builder.py           # 邮件构建器（text + html）
│   ├── report_generator.py       # 文本报告
│   ├── template_engine.py        # Jinja2 模板引擎
│   ├── word_report.py            # 可选 Word 报告（python-docx）
│   ├── archive.py                # 案件打包/校验/加密
│   ├── schema.py                 # JSON Schema 校验
│   ├── scenario.py               # 剧本机制
│   ├── global_config.py          # ~/.wrg/config.yaml
│   ├── i18n.py                   # 简短中英日韩文案
│   └── paths.py                  # 路径解析
├── tests/                        # 275 个测试，89% 覆盖率
│   ├── conftest.py
│   ├── test_*.py
│   └── test_e2e.py               # 端到端 + 离线保证
└── docs/
    ├── USER_GUIDE.md            # 🆕 面向用户的完整教程（初学者首选）
    ├── USAGE.md                 # 命令行参数参考手册
    ├── LEGAL_NOTES.md           # 法律与合规
    └── RECIPIENTS_MAINTENANCE.md # 收件人维护
```

---

## ⚖️ 法律声明

1. 本工具仅供学习和依法维权使用，**禁止用于任何违法目的**。
2. 使用本工具生成的材料需确保内容真实，虚假举报需承担法律责任。
3. 本工具不存储、不上传任何用户数据，所有操作均在本地完成。
4. 机构联系方式均来自公开渠道，如有变更请以官方最新信息为准。
5. 详见 [LICENSE](./LICENSE) 与 [docs/LEGAL_NOTES.md](./docs/LEGAL_NOTES.md)。

---

## 🧪 开发与测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 查看覆盖率
pytest --cov=wrg --cov-report=term-missing

# 当前：275 个测试，89% 覆盖率
```

## 🆕 v0.3 新增命令速览

```bash
# 案件打包为 zip（含 manifest.json + manifest.sha256）
wrg archive pack --case-dir ./cases/my-case -o ./case.zip

# 校验归档完整性
wrg archive verify ./case.zip

# 解压归档
wrg archive extract ./case.zip -o ./restored --yes

# 加密归档（AES-256-GCM）
wrg archive pack --case-dir ./cases/my-case -o ./case.zip --encrypt

# 生成 Word 报告（可选，需 python-docx）
wrg generate -i "ILO - 日内瓦总部" --word --violation "wage:9月欠薪:15000"

# 按剧本一键生成多封邮件
wrg play --case-dir ./cases/my-case config/scenarios/wage_default.yaml

# 全局配置（收件人偏好、From 头等）
wrg config init
wrg config set default_lang en
wrg config set from_addr alice@example.com

# 配置 / 剧本 / 机构池格式校验
wrg validate case ./cases/my-case/case_info.json
wrg validate scenario ./config/scenarios/wage_default.yaml
wrg validate institutions ./config/institutions.yaml

# 本地 HTML 预览（不联网）
wrg preview --case-dir ./cases/my-case --lang zh

# Shell 自动补全
wrg completion bash > ~/.wrg_completion.bash
wrg completion zsh  > "${fpath[1]}/_wrg"
wrg completion fish > ~/.config/fish/completions/wrg.fish
```

### 代码贡献

欢迎通过 Issue 与 PR 贡献：

- 补充更多国家 / 地区的监督机构
- 完善多语言邮件模板
- 改进证据管理功能
- 完善文档与翻译

---

## 📄 许可证

- **代码**：MIT（详见 [LICENSE](./LICENSE)）
- **模板与收件人数据**：CC-BY-SA 4.0

---

**🛡️ 劳动者权益受法律保护。依法维权，理性表达。**