# Changelog

All notable changes to **Worker Rights Guardian** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

---

## [0.3.0] - 2026-09-03

### 新增

- **JSON Schema 校验**（[src/wrg/schema.py](src/wrg/schema.py)）
  - `validate_case_info` / `validate_scenario` / `validate_institutions`
  - 顶层 dict 检查、必备字段、类型校验、嵌套 violations 校验
- **HTML 邮件模板**（中文 / 英文 / 日文 / 韩文）
  - `config/templates/{zh,en,ja,ko}/labor_complaint.html.jinja2`
  - 内联 CSS，兼容主流邮件客户端
  - `.eml` 现在是 multipart/alternative（text + html）
- **案件打包**（[src/wrg/archive.py](src/wrg/archive.py)）
  - `wrg archive pack` 生成 zip + `manifest.json` + `manifest.sha256`
  - `wrg archive verify` 校验 SHA-256 完整性
  - `wrg archive extract` 解压恢复案件
  - 可选 AES-256-GCM 加密（`--encrypt`，需 `cryptography` 包）
- **本地 HTML 预览** `wrg preview`
  - 浏览器本地打开，绝不上传
  - 默认输出到 `<case>/reports/preview_<lang>.html`
- **配置校验** `wrg validate <case|scenario|institutions> <path>`
- **Shell 自动补全**
  - `wrg completion bash` / `zsh` / `fish`
- **机构池扩充**：新增 16 家机构，涵盖
  - EU：Eurofound、DG EMPL、France DGT、Germany BMAS、Netherlands
    Arbeidsinspectie、Sweden AV
  - 日本：厚生劳动省劳动基准局、JIL
  - 韩国：KOSHA、雇佣情报院
  - 澳大利亚：Fair Work Commission、AHRC、ASEA
  - 新西兰：Worksafe NZ、NZ Human Rights Commission
- 新增 i18n 文案：archive、preview、validate

### 测试

- 新增 83 个测试（总数从 192 升至 275，覆盖率 89%）
- [tests/test_schema.py](tests/test_schema.py) — Schema 校验 34 个
- [tests/test_archive.py](tests/test_archive.py) — 归档 21 个
- [tests/test_html_templates.py](tests/test_html_templates.py) — HTML 模板 7 个
- [tests/test_v03_cli.py](tests/test_v03_cli.py) — v0.3 CLI 集成 19 个

### 安全性

- 加密使用 AES-256-GCM（认证加密，防篡改）
- 归档使用 atomic `.tmp + rename`，避免半写状态
- 归档文件 SHA-256 全量校验，任何字节篡改都能检测

---

## [0.2.0] - 2026-09-03

### 新增

- 多语言邮件模板：中文、英文、日文、韩文
- 全局配置 `~/.wrg/config.yaml`：`wrg config init/set/get/show/path`
- 可选 Word 输出 `wrg generate --word`（基于 python-docx）
- 剧本机制 `config/scenarios/*.yaml` + `wrg play`
- 独立 `wrg wizard` 子命令与 `wrg generate --interactive`
- 多语言 i18n 文案

### 测试

- 137 → 192 个测试，覆盖率 90%

---

## [0.1.0] - 2026-09-03

首个 MVP 版本。

- CLI 命令：`init` / `add-evidence` / `add-text` / `list-evidence` /
  `remove-evidence` / `verify` / `list-institutions` / `search` /
  `types` / `generate` / `summary` / `config`
- 案件目录：`case_info.json` + `evidence_index.json` + `evidence/` + `mails/` + `reports/`
- 邮件草稿：.eml（RFC 5322）+ .txt 双格式
- SHA-256 证据完整性校验
- 收件人池：中国监督机构、联合国 / ILO、美 / 英 / 欧 / 澳 / 新 / 日 / 韩 30+ 家
- 4 国主流媒体联系方式
- i18n 中英双语短文案
- 137 个测试，覆盖率 92%