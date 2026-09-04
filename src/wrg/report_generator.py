"""报告生成器。

MVP 阶段只生成纯文本报告 + 案件摘要。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def now_pretty() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ReportGenerator:
    """纯文本报告生成器。"""

    def __init__(self, output_dir: str | Path | None = None) -> None:
        if output_dir is None:
            output_dir = Path.cwd() / "reports"
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_text(self, content: str, case_name: str) -> str:
        """生成纯文本报告并返回写入路径。"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = _safe_filename(case_name) or "case"
        filepath = self.output_dir / f"report_{safe_name}_{ts}.txt"
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def generate_summary(
        self,
        case_data: dict[str, Any],
        institutions: list[dict[str, Any]],
        evidence_count: int,
    ) -> str:
        """生成纯文本案件摘要（用于控制台输出）。"""
        lines = [
            "=" * 60,
            "劳动监察举报案件摘要",
            "=" * 60,
            f"生成时间: {now_pretty()}",
            f"案件名称: {case_data.get('company_name', '未命名')}",
            f"投诉人:   {case_data.get('worker_name', '匿名')}",
            f"联系电话: {case_data.get('worker_phone', '-')}",
            f"证据数量: {evidence_count}",
            "-" * 60,
            "目标机构:",
        ]
        for inst in institutions:
            lines.append(f"  - {inst.get('name', '未知机构')}")
            contact = inst.get("email") or inst.get("contact") or inst.get("url") or "暂无"
            lines.append(f"    联系方式: {contact}")
        lines.append("=" * 60)
        return "\n".join(lines)


def _safe_filename(name: str) -> str:
    """把任意字符串处理成安全的文件名片段。

    保留 ASCII 字母数字与中文字符，以及 ``-_.()`` 等符号，
    其他字符（包含空格）替换为下划线，文件名长度上限 80。
    """
    if not name:
        return ""
    keep = "-_.()"
    return "".join(
        ch if (ch.isalnum() or ch in keep) else "_"
        for ch in name
    )[:80]


__all__ = ["ReportGenerator", "now_pretty"]