"""证据导入与管理。

支持图片、文档、音视频、文本等多种格式，自动计算 SHA-256 校验和，
将证据文件统一复制到案件目录下，并把元数据保存为 JSON 索引。

典型用法::

    mgr = EvidenceManager("./cases/demo")
    item = mgr.add_evidence("salary.jpg", description="3月工资条")
    for ev in mgr.list_evidence():
        print(ev.id, ev.name, ev.checksum)
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# 文件类型分类表。优先级:先匹配更具体的扩展名;text 优先于 document
# 因为 .txt/.md 既可视为文档也可视为纯文本，默认归入 text。
SUPPORTED_TYPES: dict[str, list[str]] = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"],
    "audio": [".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"],
    "video": [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"],
    "text": [".txt", ".md", ".csv", ".json", ".log"],
    "document": [".pdf", ".doc", ".docx",
                 ".xls", ".xlsx", ".ppt", ".pptx"],
}


def classify_extension(ext: str) -> str:
    """根据扩展名（含点）返回文件类型，未知类型返回 ``"unknown"``。"""
    if not ext:
        return "unknown"
    e = ext.lower()
    if not e.startswith("."):
        e = "." + e
    for ftype, exts in SUPPORTED_TYPES.items():
        if e in exts:
            return ftype
    return "unknown"


def sha256_of(path: str | Path, chunk: int = 65536) -> str:
    """计算文件的 SHA-256 十六进制摘要。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def now_iso() -> str:
    """获取当前 UTC 时间的 ISO8601 字符串（秒精度）。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class EvidenceItem:
    """证据项数据类。

    Attributes:
        id: 形如 ``EVD_<时间戳>_<8位哈希>`` 的唯一 ID。
        name: 原始文件名。
        file_path: 持久化后的绝对/相对路径字符串。
        file_type: image / document / audio / video / text / unknown。
        file_size: 文件字节数。
        checksum: SHA-256 十六进制。
        description: 用户填写的描述。
        created_at: ISO8601 时间。
        tags: 用户标签列表。
    """

    id: str
    name: str
    file_path: str
    file_type: str
    file_size: int
    checksum: str
    description: str = ""
    created_at: str = field(default_factory=now_iso)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        # 兼容缺字段
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            file_path=str(data.get("file_path", "")),
            file_type=str(data.get("file_type", "unknown")),
            file_size=int(data.get("file_size", 0)),
            checksum=str(data.get("checksum", "")),
            description=str(data.get("description", "")),
            created_at=str(data.get("created_at", now_iso())),
            tags=list(data.get("tags", []) or []),
        )


class EvidenceManager:
    """单个案件目录下的证据管理器。

    目录布局::

        <case_dir>/
        ├── evidence/                # 复制的证据文件
        │   ├── EVD_xxx.jpg
        │   └── EVD_yyy.pdf
        └── evidence_index.json      # 元数据索引
    """

    INDEX_FILENAME = "evidence_index.json"
    EVIDENCE_SUBDIR = "evidence"

    def __init__(self, case_dir: str | Path) -> None:
        self.case_dir = Path(case_dir).expanduser().resolve()
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir = self.case_dir / self.EVIDENCE_SUBDIR
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.case_dir / self.INDEX_FILENAME
        self.evidence_list: list[EvidenceItem] = []
        self._load_index()

    # ---------- 索引 I/O ----------

    def _load_index(self) -> None:
        if not self.index_file.exists():
            self.evidence_list = []
            return
        try:
            data = json.loads(self.index_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("index file must be a JSON list")
            self.evidence_list = [EvidenceItem.from_dict(item) for item in data]
        except (json.JSONDecodeError, ValueError, OSError):
            # 索引损坏时不让程序崩溃，记为空但保留文件供人工修复
            self.evidence_list = []

    def _save_index(self) -> None:
        payload = [item.to_dict() for item in self.evidence_list]
        # 原子写:先写临时文件再 rename，避免半写状态
        tmp = self.index_file.with_suffix(self.index_file.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.index_file)

    # ---------- ID 生成 ----------

    def _new_evidence_id(self, hint: str) -> str:
        # 使用无下划线的时间戳（YYYYMMDDTHHMMSS），便于以 _ 切分得到 3 段
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        salt = hashlib.md5(hint.encode("utf-8", errors="replace")).hexdigest()[:8]
        return f"EVD_{ts}_{salt}"

    # ---------- 添加 ----------

    def add_evidence(
        self,
        source_path: str | Path,
        description: str = "",
        tags: Iterable[str] | None = None,
    ) -> EvidenceItem:
        """从外部路径添加证据。

        Args:
            source_path: 原始文件路径。
            description: 用户填写的描述。
            tags: 标签列表。

        Returns:
            新建的 ``EvidenceItem``。

        Raises:
            FileNotFoundError: 源文件不存在。
            ValueError: 不支持的文件扩展名。
        """
        src = Path(source_path).expanduser()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"文件不存在: {source_path}")

        ext = src.suffix
        ftype = classify_extension(ext)
        if ftype == "unknown":
            raise ValueError(f"不支持的文件类型: {ext or '(无扩展名)'}")

        evidence_id = self._new_evidence_id(src.name)
        dest_name = f"{evidence_id}{ext}"
        dest_path = self.evidence_dir / dest_name
        shutil.copy2(src, dest_path)

        item = EvidenceItem(
            id=evidence_id,
            name=src.name,
            file_path=str(dest_path),
            file_type=ftype,
            file_size=dest_path.stat().st_size,
            checksum=sha256_of(dest_path),
            description=description,
            tags=list(tags or []),
        )
        self.evidence_list.append(item)
        self._save_index()
        return item

    def add_text_evidence(
        self,
        content: str,
        name: str,
        description: str = "",
        tags: Iterable[str] | None = None,
    ) -> EvidenceItem:
        """添加一段文本作为证据（例如聊天记录）。"""
        if not name:
            raise ValueError("name 不能为空")
        ext = Path(name).suffix or ".txt"
        evidence_id = self._new_evidence_id(name)
        dest_name = f"{evidence_id}{ext}"
        dest_path = self.evidence_dir / dest_name
        dest_path.write_text(content, encoding="utf-8")

        item = EvidenceItem(
            id=evidence_id,
            name=name,
            file_path=str(dest_path),
            file_type="text",
            file_size=dest_path.stat().st_size,
            checksum=sha256_of(dest_path),
            description=description,
            tags=list(tags or []),
        )
        self.evidence_list.append(item)
        self._save_index()
        return item

    # ---------- 查询 ----------

    def list_evidence(
        self,
        file_type: str | None = None,
        tag: str | None = None,
    ) -> list[EvidenceItem]:
        """列出证据，可按类型与标签筛选。"""
        result = self.evidence_list
        if file_type:
            ft = file_type.lower()
            result = [e for e in result if e.file_type == ft]
        if tag:
            result = [e for e in result if tag in e.tags]
        return result

    def get_evidence(self, evidence_id: str) -> EvidenceItem | None:
        for item in self.evidence_list:
            if item.id == evidence_id:
                return item
        return None

    def remove_evidence(self, evidence_id: str) -> bool:
        """根据 ID 删除证据（含磁盘文件）。"""
        for i, item in enumerate(self.evidence_list):
            if item.id == evidence_id:
                path = Path(item.file_path)
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
                self.evidence_list.pop(i)
                self._save_index()
                return True
        return False

    def verify_integrity(self) -> list[tuple[str, bool]]:
        """校验所有证据文件是否仍然存在且校验和未变。

        Returns:
            ``[(evidence_id, ok), ...]`` 列表。
        """
        results: list[tuple[str, bool]] = []
        for item in self.evidence_list:
            path = Path(item.file_path)
            if not path.exists():
                results.append((item.id, False))
                continue
            try:
                ok = sha256_of(path) == item.checksum
            except OSError:
                ok = False
            results.append((item.id, ok))
        return results

    # ---------- 摘要 ----------

    def generate_evidence_summary(self) -> str:
        """生成 Markdown 格式的证据清单。"""
        lines: list[str] = []
        lines.append("# 证据清单")
        lines.append("")
        lines.append(f"- 生成时间: {now_iso()}")
        lines.append(f"- 证据总数: {len(self.evidence_list)}")
        total = sum(e.file_size for e in self.evidence_list)
        lines.append(f"- 总大小: {total / 1024:.1f} KB")
        lines.append("")
        lines.append("| # | 文件 | 描述 | 类型 | 大小 | SHA-256 | 标签 |")
        lines.append("|---|---|---|---|---|---|---|")
        for idx, item in enumerate(self.evidence_list, 1):
            desc = item.description.replace("|", "\\|") or "-"
            tags = ", ".join(item.tags) if item.tags else "-"
            size = f"{item.file_size / 1024:.1f} KB"
            lines.append(
                f"| {idx} | {item.name} | {desc} | {item.file_type} | "
                f"{size} | `{item.checksum[:16]}…` | {tags} |"
            )
        return "\n".join(lines) + "\n"


__all__ = [
    "SUPPORTED_TYPES",
    "EvidenceItem",
    "EvidenceManager",
    "classify_extension",
    "sha256_of",
    "now_iso",
]