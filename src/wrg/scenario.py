"""剧本（scenario）机制。

一个剧本是一组预定义的“案件 → 收件人 → 语言”组合，执行一次可一键生成
所有相关邮件草稿。例如::

    # config/scenarios/wage_default.yaml
    type: wage
    langs: [zh, en]
    pools: [china_government, un_ilo, media_global]

执行::

    wrg play --case-dir ./cases/my-case --scenario config/scenarios/wage_default.yaml

即可针对该案件生成上述语言/收件人组合的所有邮件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .institution_db import InstitutionDB


@dataclass
class ScenarioStep:
    """剧本中的一个步骤。"""

    type: str  # 申诉类型，如 wage
    lang: str  # 语言代码，如 zh / en / ja / ko
    institutions: list[str] = field(default_factory=list)
    # 可选，覆盖默认 violation 文案
    violation_type: str | None = None
    violation_description: str | None = None
    violation_amount: str | None = None


@dataclass
class Scenario:
    """剧本（可包含多个步骤）。"""

    name: str
    steps: list[ScenarioStep] = field(default_factory=list)
    description: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def expand(self, db: InstitutionDB) -> list[tuple[str, str, str]]:
        """展开为 (类型, 语言, 机构名) 三元组列表。

        若 step.institutions 为空，会自动从 ``type`` 与 ``lang`` 推断
        默认收件人集合。
        """
        out: list[tuple[str, str, str]] = []
        for step in self.steps:
            names = list(step.institutions)
            if not names:
                # 自动按 type + lang 推断
                names = _auto_recipients(db, step.type, step.lang)
            for name in names:
                out.append((step.type, step.lang, name))
        return out


def _auto_recipients(
    db: InstitutionDB,
    violation_type: str,
    lang: str,
) -> list[str]:
    """根据违规类型与语言给出合理的默认收件人集合。"""
    pool_keywords: dict[str, list[str]] = {
        "wage": ["劳动监察", "劳动保障", "ILO", "拖欠"],
        "国际": ["ILO", "OHCHR", "UN"],
    }
    if lang == "en":
        keys = ["ILO", "DOL", "OSHA", "EEOC", "BBC", "Reuters"]
    elif lang == "ja":
        keys = ["労働基準監督署", "中央労働委員会", "NHK", "朝日"]
    elif lang == "ko":
        keys = ["고용노동부", "노동위원회", "Korea Times"]
    else:
        keys = ["劳动监察", "ILO", "工会"]
    results: list[str] = []
    for k in keys:
        for inst in db.search(k):
            if inst.name not in results:
                results.append(inst.name)
            if len(results) >= 3:
                break
        if len(results) >= 3:
            break
    return results


def load_scenario(path: str | Path) -> Scenario:
    """加载剧本文件（YAML）。"""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"剧本文件不存在: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"剧本 YAML 解析失败: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("剧本文件必须是一个字典")

    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list):
        raise ValueError("剧本文件必须包含 'steps' 列表")

    name = str(raw.get("name", p.stem))
    description = str(raw.get("description", ""))
    steps: list[ScenarioStep] = []
    for item in steps_raw:
        if not isinstance(item, dict):
            continue
        steps.append(
            ScenarioStep(
                type=str(item.get("type", "other")),
                lang=str(item.get("lang", "zh")),
                institutions=list(item.get("institutions", []) or []),
                violation_type=item.get("violation_type"),
                violation_description=item.get("violation_description"),
                violation_amount=item.get("violation_amount"),
            )
        )
    return Scenario(
        name=name, steps=steps, description=description, raw=raw
    )


__all__ = ["Scenario", "ScenarioStep", "load_scenario"]