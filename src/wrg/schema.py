"""JSON Schema 定义与校验。

所有持久化的数据结构（case_info.json / scenario.yaml / institutions.yaml）
都使用统一的 ``jsonschema`` 风格验证（不引入第三方依赖，用极简手写校验器）。

校验失败抛 ``wrg.schema.ValidationError``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["ValidationError", "validate_case_info", "validate_scenario",
           "validate_institutions"]


class ValidationError(ValueError):
    """数据结构不符合预期格式。"""


# ============================================================
# case_info.json
# ============================================================

_CASE_INFO_REQUIRED: list[str] = [
    "company_name",
    "company_address",
    "worker_name",
    "worker_phone",
]

_CASE_INFO_STR_FIELDS: list[str] = [
    "company_name",
    "company_address",
    "company_legal_person",
    "company_credit_code",
    "company_phone",
    "worker_name",
    "worker_phone",
    "worker_email",
    "worker_id",
    "entry_date",
    "job_position",
    "contract_status",
    "created_at",
]


def validate_case_info(data: Any) -> None:
    """校验 case_info.json 内容。

    顶层必须是 dict，包含 4 个必备字符串字段；
    violations 必须是 list[dict]，每项至少有 type/description。
    """
    if not isinstance(data, dict):
        raise ValidationError("case_info 必须为 dict")

    for f in _CASE_INFO_REQUIRED:
        if f not in data:
            raise ValidationError(f"case_info 缺少必备字段:{f}")
        if not isinstance(data[f], str):
            raise ValidationError(f"case_info.{f} 应为字符串")

    for f in _CASE_INFO_STR_FIELDS:
        if f in data and not isinstance(data[f], str):
            raise ValidationError(f"case_info.{f} 应为字符串")

    violations = data.get("violations")
    if violations is not None:
        if not isinstance(violations, list):
            raise ValidationError("case_info.violations 应为 list")
        for i, v in enumerate(violations):
            if not isinstance(v, dict):
                raise ValidationError(f"violations[{i}] 应为 dict")
            if "type" not in v or "description" not in v:
                raise ValidationError(
                    f"violations[{i}] 缺少 type 或 description"
                )


# ============================================================
# scenario YAML
# ============================================================

_SCENARIO_REQUIRED_TOP: list[str] = ["name", "steps"]


def validate_scenario(data: Any) -> None:
    """校验剧本 YAML 结构。

    顶层必须含 name + steps；每个 step 必须含 type，可选 lang/institutions/description。
    """
    if not isinstance(data, dict):
        raise ValidationError("scenario 顶层必须为 dict")

    for k in _SCENARIO_REQUIRED_TOP:
        if k not in data:
            raise ValidationError(f"scenario 缺少必备字段:{k}")

    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValidationError("scenario.name 必须为非空字符串")

    steps = data["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValidationError("scenario.steps 必须为非空 list")

    valid_types = {
        "wage", "overtime", "injury", "discrim", "contract",
        "social", "child", "forced", "safety", "union", "other",
    }
    valid_langs = {"zh", "en", "ja", "ko"}

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValidationError(f"steps[{i}] 必须为 dict")
        if "type" not in step:
            raise ValidationError(f"steps[{i}] 缺少 type")
        if step["type"] not in valid_types:
            raise ValidationError(
                f"steps[{i}].type '{step['type']}' 不在支持列表中"
            )
        if "lang" in step and step["lang"] not in valid_langs:
            raise ValidationError(
                f"steps[{i}].lang '{step['lang']}' 不支持"
            )
        if "institutions" in step:
            insts = step["institutions"]
            if not isinstance(insts, list):
                raise ValidationError(
                    f"steps[{i}].institutions 必须为 list"
                )
            for j, inst in enumerate(insts):
                if not isinstance(inst, str):
                    raise ValidationError(
                        f"steps[{i}].institutions[{j}] 必须为字符串"
                    )


# ============================================================
# institutions.yaml
# ============================================================


def validate_institutions(data: Any) -> None:
    """校验 institutions.yaml。

    顶层为 dict，每个 category 是 list[dict]，每个 dict 至少含 name/email|contact|url。
    """
    if not isinstance(data, dict):
        raise ValidationError("institutions 顶层必须为 dict")

    for cat, items in data.items():
        if not isinstance(items, list):
            raise ValidationError(f"institutions.{cat} 必须为 list")
        for i, inst in enumerate(items):
            if not isinstance(inst, dict):
                raise ValidationError(
                    f"institutions.{cat}[{i}] 必须为 dict"
                )
            if "name" not in inst or not isinstance(inst["name"], str):
                raise ValidationError(
                    f"institutions.{cat}[{i}].name 必须为字符串"
                )
            # 至少要有一种联系方式
            if not any(k in inst for k in ("email", "contact", "url")):
                raise ValidationError(
                    f"institutions.{cat}[{i}].{inst['name']} "
                    "至少需要 email/contact/url 之一"
                )


# ============================================================
# 通用便捷入口
# ============================================================


def validate_yaml_file(path: str | Path, kind: str) -> Any:
    """根据 kind 校验对应 YAML 文件并返回解析后的 dict。"""
    import yaml

    p = Path(path)
    if not p.exists():
        raise ValidationError(f"文件不存在:{p}")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValidationError(f"YAML 解析失败:{exc}") from exc

    if kind == "case_info":
        validate_case_info(data)
    elif kind == "scenario":
        validate_scenario(data)
    elif kind == "institutions":
        validate_institutions(data)
    else:
        raise ValidationError(f"未知 kind: {kind}")
    return data


def validate_json_file(path: str | Path, kind: str) -> Any:
    """校验 JSON 文件并返回 dict。"""
    import json

    p = Path(path)
    if not p.exists():
        raise ValidationError(f"文件不存在:{p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"JSON 解析失败:{exc}") from exc

    if kind == "case_info":
        validate_case_info(data)
    else:
        raise ValidationError(f"未知 kind: {kind}")
    return data