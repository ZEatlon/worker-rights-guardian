"""监督机构与媒体联系方式数据库。

数据存放在 YAML 文件中，按类别聚合。每个机构都是 ``Institution`` 实例，
可通过关键词、scope、地区进行搜索。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from .paths import resolve_config_dir

INSTITUTIONS_FILENAME = "institutions.yaml"
MEDIA_FILENAME = "media_contacts.yaml"


@dataclass
class Institution:
    """机构数据类。

    Attributes:
        name: 机构名称。
        type: hotline / email / online / address。
        scope: 适用范围（全国 / 全球 / USA / Japan 等）。
        region: 地区描述（可空）。
        description: 描述。
        contact: 电话或其他联系方式。
        email: 邮箱。
        url: 网址。
        category: 所属类别（由 DB 注入）。
        raw: 原始字典（便于扩展字段透传）。
    """

    name: str
    type: str
    scope: str = ""
    region: str = ""
    description: str = ""
    contact: str = ""
    email: str = ""
    url: str = ""
    category: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def display_contact(self) -> str:
        """人类可读的联系方式。"""
        if self.email:
            return f"邮箱: {self.email}"
        if self.contact:
            return f"电话: {self.contact}"
        if self.url:
            return f"网址: {self.url}"
        return "暂无联系方式"

    def matches(self, keyword: str) -> bool:
        k = keyword.lower()
        fields = [
            self.name or "",
            self.description or "",
            self.scope or "",
            self.region or "",
            self.email or "",
        ]
        return any(k in f.lower() for f in fields)


def _coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _build_institution(item: dict[str, Any], category: str) -> Institution:
    raw = dict(item)
    return Institution(
        name=_coerce_str(raw.get("name", "")),
        type=_coerce_str(raw.get("type", "")),
        scope=_coerce_str(raw.get("scope", "")),
        region=_coerce_str(raw.get("region", "")),
        description=_coerce_str(raw.get("description", "")),
        contact=_coerce_str(raw.get("contact", "")),
        email=_coerce_str(raw.get("email", "")),
        url=_coerce_str(raw.get("url", "")),
        category=category,
        raw=raw,
    )


class InstitutionDB:
    """机构数据库。

    使用::

        db = InstitutionDB()  # 默认 config/
        all_institutions = db.list_all()
        china = db.search("劳动监察", category="china")
    """

    def __init__(self, config_dir: str | Path | None = None) -> None:
        self.config_dir = resolve_config_dir(config_dir)
        self.institutions: dict[str, list[Institution]] = {}
        self.media: dict[str, list[Institution]] = {}
        self._load()

    # ---------- 加载 ----------

    def _load_yaml(self, filename: str) -> dict[str, list[dict[str, Any]]]:
        path = self.config_dir / filename
        if not path.exists():
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return {}
        if not isinstance(data, dict):
            return {}
        # 过滤掉非字典项
        cleaned: dict[str, list[dict[str, Any]]] = {}
        for k, v in data.items():
            if isinstance(v, list):
                cleaned[k] = [it for it in v if isinstance(it, dict)]
            else:
                cleaned[k] = []
        return cleaned

    def _load(self) -> None:
        for category, items in self._load_yaml(INSTITUTIONS_FILENAME).items():
            self.institutions[category] = [
                _build_institution(item, category) for item in items
            ]
        for category, items in self._load_yaml(MEDIA_FILENAME).items():
            self.media[category] = [
                _build_institution(item, category) for item in items
            ]

    # ---------- 访问 ----------

    def get_categories(self) -> list[str]:
        return list(self.institutions.keys())

    def get_media_categories(self) -> list[str]:
        return list(self.media.keys())

    def list_all(self) -> dict[str, list[Institution]]:
        return self.institutions

    def list_all_media(self) -> dict[str, list[Institution]]:
        return self.media

    def _iter_all(self) -> Iterable[Institution]:
        for items in self.institutions.values():
            yield from items
        for items in self.media.values():
            yield from items

    # ---------- 搜索 ----------

    def search(
        self,
        keyword: str = "",
        scope: str | None = None,
        category: str | None = None,
    ) -> list[Institution]:
        """搜索机构。

        Args:
            keyword: 关键词（为空时返回全部）。
            scope: 按 scope 精确过滤（不区分大小写）。
            category: 在指定类别内搜索（支持机构与媒体类别）。

        Returns:
            命中的机构列表。
        """
        if category:
            pools: list[Institution] = []
            if category in self.institutions:
                pools.extend(self.institutions[category])
            if category in self.media:
                pools.extend(self.media[category])
        else:
            pools = list(self._iter_all())

        results: list[Institution] = []
        kw = (keyword or "").strip()
        for inst in pools:
            if scope and inst.scope.lower() != scope.lower():
                continue
            if kw and not inst.matches(kw):
                continue
            results.append(inst)
        return results

    def find_by_name(self, name: str) -> Institution | None:
        """按名称精确匹配。"""
        for inst in self._iter_all():
            if inst.name == name:
                return inst
        return None

    def get_by_scope(self, scope: str) -> list[Institution]:
        return [inst for inst in self._iter_all() if inst.scope.lower() == scope.lower()]

    def get_by_region(self, region: str) -> list[Institution]:
        r = region.lower()
        return [inst for inst in self._iter_all() if r in inst.region.lower()]

    def get_by_category(self, category: str) -> list[Institution]:
        results: list[Institution] = []
        if category in self.institutions:
            results.extend(self.institutions[category])
        if category in self.media:
            results.extend(self.media[category])
        return results

    def stats(self) -> dict[str, int]:
        """返回各类别机构数量统计。"""
        return {
            **{k: len(v) for k, v in self.institutions.items()},
            **{f"media.{k}": len(v) for k, v in self.media.items()},
        }


__all__ = [
    "Institution",
    "InstitutionDB",
    "INSTITUTIONS_FILENAME",
    "MEDIA_FILENAME",
]