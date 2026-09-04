"""Jinja2 邮件模板引擎。

模板按语言代码组织在 ``config/templates/<lang>/`` 目录下，使用 Jinja2
的 ``FileSystemLoader``。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .paths import resolve_template_dir


def _format_date(value: Any, fmt: str = "%Y-%m-%d") -> str:
    """日期格式化过滤器。"""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str):
        for parser in (
            lambda s: datetime.fromisoformat(s),
            lambda s: datetime.strptime(s, "%Y-%m-%d"),
            lambda s: datetime.strptime(s, "%Y/%m/%d"),
        ):
            try:
                return parser(value).strftime(fmt)
            except (ValueError, TypeError):
                continue
    return str(value)


def _format_currency(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value) if value is not None else ""


class TemplateEngine:
    """Jinja2 模板引擎封装。"""

    def __init__(
        self,
        template_dir: str | Path | None = None,
        *,
        autoescape: bool = True,
        strict: bool = False,
    ) -> None:
        self.template_dir = resolve_template_dir(template_dir)
        if not self.template_dir.exists():
            # 模板目录不存在时，设为临时目录以避免 FileSystemLoader 报错
            self.template_dir.mkdir(parents=True, exist_ok=True)
        env_kwargs: dict[str, Any] = {
            "loader": FileSystemLoader(str(self.template_dir)),
            "autoescape": select_autoescape(["html", "xml"]) if autoescape else False,
            "trim_blocks": True,
            "lstrip_blocks": True,
        }
        if strict:
            env_kwargs["undefined"] = StrictUndefined
        self.env = Environment(**env_kwargs)
        self.env.filters["format_date"] = _format_date
        self.env.filters["format_currency"] = _format_currency

    # ---------- 模板访问 ----------

    def list_templates(self, language: str | None = None) -> list[dict[str, str]]:
        """列出可用模板。

        Args:
            language: 若指定，只返回该语言子目录中的模板。

        Returns:
            ``[{path, name, language}, ...]``
        """
        results: list[dict[str, str]] = []
        if not self.template_dir.exists():
            return results
        roots: list[Path]
        if language:
            roots = [self.template_dir / language]
        else:
            roots = [p for p in self.template_dir.iterdir() if p.is_dir()]
        for root in roots:
            if not root.exists():
                continue
            lang = root.name
            for f in sorted(root.rglob("*.jinja2")):
                rel = f.relative_to(self.template_dir).as_posix()
                results.append(
                    {
                        "path": rel,
                        "name": f.stem,
                        "language": lang,
                    }
                )
        return results

    def has_template(self, template_path: str) -> bool:
        try:
            self.env.get_template(template_path)
            return True
        except Exception:  # 包括 TemplateNotFound
            return False

    def render(self, template_path: str, context: dict[str, Any]) -> str:
        """按相对路径加载并渲染模板。"""
        template = self.env.get_template(template_path)
        return template.render(**context)

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """渲染内联模板字符串。"""
        template = self.env.from_string(template_string)
        return template.render(**context)


__all__ = ["TemplateEngine"]