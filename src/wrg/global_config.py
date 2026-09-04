"""全局配置（`~/.wrg/config.yaml`）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def default_global_config_path() -> Path:
    """返回全局配置文件的默认路径 ``~/.wrg/config.yaml``。"""
    return Path.home() / ".wrg" / "config.yaml"


GLOBAL_FILENAME = "config.yaml"


class GlobalConfig:
    """全局用户配置。

    字段:
        defaults: 案件信息默认值，可在 init 时与项目 case_info.json 合并。
        default_lang: 默认邮件模板语言。
        from_addr: 默认 ``From`` 头。
        recipient_pool_favorites: 收藏的收件人机构名列表（用于剧本）。
        interactive: 交互偏好（预留）。
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or default_global_config_path()).expanduser()
        self._data: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            self._data = {}
            self._loaded = True
            return self._data
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        self._data = data
        self._loaded = True
        return self._data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            yaml.safe_dump(self._data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        if not self._loaded:
            self.load()
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if not self._loaded:
            self.load()
        self._data[key] = value

    @property
    def data(self) -> dict[str, Any]:
        if not self._loaded:
            self.load()
        return self._data

    # ---------- 业务方法 ----------

    def defaults(self) -> dict[str, Any]:
        """返回 ``defaults`` 字段（用于填充 case_info.json）。"""
        v = self.get("defaults", {})
        return v if isinstance(v, dict) else {}

    def default_lang(self) -> str:
        v = self.get("default_lang", "zh")
        return v if isinstance(v, str) and v in ("zh", "en", "ja", "ko") else "zh"

    def from_addr(self) -> str:
        v = self.get("from_addr", "anonymous@worker.local")
        return v if isinstance(v, str) else "anonymous@worker.local"

    def favorites(self) -> list[str]:
        v = self.get("recipient_pool_favorites", [])
        if isinstance(v, list):
            return [x for x in v if isinstance(x, str)]
        return []

    def merge_into_case(self, case_info: dict[str, Any]) -> dict[str, Any]:
        """将全局默认值合并进 case_info（不覆盖已有值）。"""
        defaults = self.defaults()
        for k, v in defaults.items():
            if k not in case_info or case_info[k] in (None, "", []):
                case_info[k] = v
        return case_info

    # ---------- 工厂 ----------

    @classmethod
    def ensure_minimal(cls) -> "GlobalConfig":
        """确保全局配置文件存在（创建含骨架的默认配置）。"""
        cfg = cls()
        if not cfg.path.exists():
            cfg._data = {
                "default_lang": "zh",
                "from_addr": "anonymous@worker.local",
                "defaults": {},
                "recipient_pool_favorites": [],
            }
            cfg._loaded = True
            cfg.save()
        else:
            cfg.load()
        return cfg


__all__ = ["GlobalConfig", "default_global_config_path"]