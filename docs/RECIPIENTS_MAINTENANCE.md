# 收件人维护手册(RECIPIENTS_MAINTENANCE)

本项目的收件人数据存储在两个 YAML 文件中:

- `config/institutions.yaml` — 监督机构
- `config/media_contacts.yaml` — 媒体联系方式

本文档说明如何维护与扩充这两份数据。

---

## 1. YAML 结构

### 1.1 institutions.yaml

顶层是 **类别**(category),值是机构列表。预置类别:

```yaml
china:           # 中国监督机构
international:   # 联合国 / ILO 等
usa:             # 美国
eu:              # 欧盟
uk:              # 英国
japan:           # 日本
korea:           # 韩国
australia:       # 澳大利亚
new_zealand:     # 新西兰
```

每个机构的字段:

```yaml
- name: "机构名称"
  type: "email"           # hotline / email / online / address
  scope: "适用范围"        # 全国 / China / USA / global ...
  region: "地区"           # 可空,如"上海"、"瑞士日内瓦"
  description: "简介"
  contact: "电话"          # 仅 type=hotline 时填
  email: "邮箱"            # 仅 type=email 时填
  url: "网址"              # 仅 type=online 时填
```

### 1.2 media_contacts.yaml

结构与 institutions.yaml 类似,但所有顶级 key 都视为 **媒体类别**。
建议命名:国家 / 地区 + `_media` 后缀(`china_media`、`international_media`)。

---

## 2. 添加新机构

### 2.1 在已有类别中追加

```yaml
# 编辑 config/institutions.yaml,在相应类别末尾追加:

japan:
  - name: "既存机构 A"
    ...
  - name: "既存机构 B"   # ← 新增项
    type: "email"
    email: "xxx@go.jp"
    scope: "Japan"
    description: "..."
```

### 2.2 新增国家 / 地区类别

例如新增"新加坡":

```yaml
# 在 institutions.yaml 末尾新增:

singapore:
    - name: "新加坡人力部 (MOM)"
      type: "email"
      email: "mom_email@mom.gov.sg"
      scope: "Singapore"
      region: "新加坡"
      description: "新加坡人力部"
```

CLI 会自动识别新类别:

```bash
$ wrg list-institutions --category singapore
$ wrg search --keyword MOM
```

---

## 3. 添加新邮件模板

### 3.1 目录结构

```
config/templates/
├── zh/
│   └── labor_complaint.jinja2
├── en/
│   └── labor_complaint.jinja2
├── ja/
│   └── labor_complaint.jinja2
└── ko/
    └── labor_complaint.jinja2
```

### 3.2 新建语言模板

```bash
mkdir -p config/templates/fr
```

创建 `config/templates/fr/labor_complaint.jinja2`:

```jinja2
Objet: Plainte concernant {{ company_name }}

Madame, Monsieur {{ institution_name }},

Je suis un(e) ancien(ne) employé(e) de {{ company_name }} ...
```

### 3.3 占位符参考

| 占位符 | 含义 |
|---|---|
| `{{ institution_name }}` | 收件机构 |
| `{{ company_name }}` | 被投诉单位 |
| `{{ company_address }}` | 单位地址 |
| `{{ company_legal_person }}` | 法人 |
| `{{ worker_name }}` | 投诉人 |
| `{{ worker_phone }}` | 联系电话 |
| `{{ worker_email }}` | 邮箱 |
| `{{ entry_date }}` | 入职时间 |
| `{{ job_position }}` | 岗位 |
| `{{ contract_status }}` | 合同情况 |
| `{{ report_date }}` | 出具日期(由工具自动生成) |
| `{% for violation in violations %}` | 违法事实循环 |
| `{% for evidence in evidence_list %}` | 证据循环 |

---

## 4. 数据校验建议

为保证数据质量,建议:

1. **来源可查**:在 `description` 或 commit message 中注明出处(如官网 URL);
2. **定期核对**:每 3-6 个月人工核对一次邮箱是否仍然有效;
3. **PR 流程**:通过 GitHub Pull Request 提交更新,便于 Reviewer 校验;
4. **不要编造**:无法核实邮箱时,留空 `email` 字段,不要瞎填。

---

## 5. 自动化校验(可选)

可在 CI 中加入 YAML 语法检查:

```yaml
# .github/workflows/ci.yml
- name: Validate YAML
  run: |
    python -c "import yaml; yaml.safe_load(open('config/institutions.yaml'))"
    python -c "import yaml; yaml.safe_load(open('config/media_contacts.yaml'))"
```

更严格地,可校验邮箱格式:

```python
import yaml, re

for f in ("config/institutions.yaml", "config/media_contacts.yaml"):
    data = yaml.safe_load(open(f))
    for cat, items in data.items():
        for inst in items:
            email = inst.get("email", "")
            if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                print(f"可疑邮箱:{cat} / {inst.get('name')}: {email}")
```

---

## 6. 提交 PR 模板建议

```markdown
### 变更类型
- [ ] 新增机构
- [ ] 更新邮箱
- [ ] 移除失效邮箱
- [ ] 新增模板
- [ ] 其他

### 详情
- 来源(URL):
- 校验日期:
- 备注:
```

---

## 7. 不收录的内容

出于谨慎,**不收录**以下内容:

- 个人律师 / 法务团队联系方式(避免商业推广嫌疑);
- 与劳动维权无关的政府邮箱(如税务、统计等);
- 已知失效的联系方式;
- 来源不明的邮箱。

如需新增,请优先确认来源后再 PR。
