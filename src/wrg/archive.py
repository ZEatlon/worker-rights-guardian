"""案件打包与清单生成。

把整个案件目录（case_info.json + evidence/ + mails/ + reports/）打包成
单 zip 文件，并生成 ``manifest.json`` 与 ``manifest.sha256`` 校验文件。

提供:
- ``ArchiveBuilder``: 构造 zip 归档
- ``verify_archive``: 校验已存在归档的完整性
- ``encrypt_archive`` / ``decrypt_archive``: 可选 AES-256 加密（依赖 cryptography）
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

__all__ = [
    "ArchiveBuilder",
    "ArchiveError",
    "verify_archive",
    "MANIFEST_NAME",
    "CHECKSUM_NAME",
]


MANIFEST_NAME = "manifest.json"
CHECKSUM_NAME = "manifest.sha256"

# 排除规则：不打包临时文件、Python 缓存、生成的日志等
EXCLUDE_NAMES: set[str] = {
    "__pycache__",
    ".DS_Store",
    "Thumbs.db",
}
EXCLUDE_SUFFIXES: tuple[str, ...] = (".pyc", ".tmp", ".bak")


class ArchiveError(RuntimeError):
    """打包 / 解包过程中出现错误。"""


@dataclass
class ArchiveEntry:
    """归档内单文件的清单条目。"""

    path: str            # 归档内相对路径（正斜杠）
    size: int            # 字节
    sha256: str          # 十六进制摘要
    file_type: str       # case_info / evidence / mail / report / other


@dataclass
class ArchiveManifest:
    """整个归档的清单。"""

    case_dir: str
    created_at: str
    tool_version: str
    entries: list[ArchiveEntry] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "case_dir": self.case_dir,
            "created_at": self.created_at,
            "tool_version": self.tool_version,
            "metadata": self.metadata,
            "entries": [
                {
                    "path": e.path,
                    "size": e.size,
                    "sha256": e.sha256,
                    "file_type": e.file_type,
                }
                for e in self.entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchiveManifest":
        entries = [
            ArchiveEntry(
                path=e["path"],
                size=e["size"],
                sha256=e["sha256"],
                file_type=e["file_type"],
            )
            for e in data.get("entries", [])
        ]
        return cls(
            case_dir=data.get("case_dir", ""),
            created_at=data.get("created_at", ""),
            tool_version=data.get("tool_version", ""),
            entries=entries,
            metadata=data.get("metadata", {}),
        )

    @property
    def total_size(self) -> int:
        return sum(e.size for e in self.entries)


def _classify(rel_path: str) -> str:
    """根据相对路径推断文件类别。"""
    p = rel_path.replace("\\", "/").lower()
    if p == "case_info.json" or p == "evidence_index.json":
        return "case_info"
    if p.startswith("evidence/"):
        return "evidence"
    if p.startswith("mails/"):
        return "mail"
    if p.startswith("reports/"):
        return "report"
    return "other"


def _hash_file(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


class ArchiveBuilder:
    """把案件目录打包为 zip 并附带 manifest。"""

    def __init__(
        self,
        case_dir: str | Path,
        tool_version: str = "0.3.0",
        metadata: Optional[dict] = None,
    ) -> None:
        self.case_dir = Path(case_dir).expanduser().resolve()
        if not self.case_dir.exists():
            raise ArchiveError(f"案件目录不存在:{self.case_dir}")
        self.tool_version = tool_version
        self.metadata = metadata or {}

    # ------------------------------------------------------------
    # 列出待打包文件
    # ------------------------------------------------------------
    def iter_files(self) -> Iterable[Path]:
        """递归列出待打包文件（应用排除规则）。"""
        if not self.case_dir.is_dir():
            raise ArchiveError(f"案件目录不是目录:{self.case_dir}")
        for p in sorted(self.case_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(self.case_dir)
            if any(part in EXCLUDE_NAMES for part in rel.parts):
                continue
            if rel.suffix.lower() in EXCLUDE_SUFFIXES:
                continue
            yield p

    # ------------------------------------------------------------
    # 构造清单
    # ------------------------------------------------------------
    def build_manifest(self) -> ArchiveManifest:
        manifest = ArchiveManifest(
            case_dir=str(self.case_dir),
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            tool_version=self.tool_version,
            metadata=dict(self.metadata),
        )
        for p in self.iter_files():
            rel = str(p.relative_to(self.case_dir)).replace("\\", "/")
            manifest.entries.append(
                ArchiveEntry(
                    path=rel,
                    size=p.stat().st_size,
                    sha256=_hash_file(p),
                    file_type=_classify(rel),
                )
            )
        return manifest

    # ------------------------------------------------------------
    # 写入 zip
    # ------------------------------------------------------------
    def write_zip(
        self,
        output_path: str | Path,
        *,
        compression: int = zipfile.ZIP_DEFLATED,
        compress_level: int = 9,
    ) -> tuple[Path, ArchiveManifest]:
        """打包并返回 (zip 路径, manifest)。"""
        out = Path(output_path).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        manifest = self.build_manifest()
        manifest_json = json.dumps(
            manifest.to_dict(), ensure_ascii=False, indent=2
        )

        tmp = out.with_suffix(out.suffix + ".tmp")
        try:
            with zipfile.ZipFile(
                tmp, "w", compression=compression, compresslevel=compress_level
            ) as zf:
                # 先写入所有业务文件
                for p in self.iter_files():
                    rel = str(p.relative_to(self.case_dir)).replace("\\", "/")
                    zf.write(p, arcname=rel)
                # 再写入 manifest
                zf.writestr(MANIFEST_NAME, manifest_json)
                # 校验文件：对 manifest.json 自身做 SHA-256
                digest = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
                zf.writestr(
                    CHECKSUM_NAME,
                    f"{digest}  {MANIFEST_NAME}\n",
                )
            tmp.replace(out)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise

        return out, manifest


def read_manifest(zip_path: str | Path) -> ArchiveManifest:
    """读取归档内的 manifest.json，返回 ArchiveManifest。"""
    p = Path(zip_path)
    if not p.exists():
        raise ArchiveError(f"归档文件不存在:{p}")
    try:
        with zipfile.ZipFile(p, "r") as zf:
            if MANIFEST_NAME not in zf.namelist():
                raise ArchiveError("归档中缺少 manifest.json")
            data = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
    except zipfile.BadZipFile as exc:
        raise ArchiveError(f"无法解析 zip 文件:{exc}") from exc
    return ArchiveManifest.from_dict(data)


def verify_archive(
    zip_path: str | Path,
    *,
    check_manifest_checksum: bool = True,
    check_file_digests: bool = True,
) -> tuple[bool, list[str]]:
    """校验归档完整性。

    Returns:
        (是否全部通过, 错误信息列表)
    """
    errors: list[str] = []
    p = Path(zip_path)
    if not p.exists():
        return False, [f"归档文件不存在:{p}"]

    try:
        manifest = read_manifest(p)
    except ArchiveError as exc:
        return False, [str(exc)]

    if check_manifest_checksum:
        try:
            with zipfile.ZipFile(p, "r") as zf:
                if CHECKSUM_NAME not in zf.namelist():
                    errors.append("缺少 manifest.sha256 校验文件")
                else:
                    expected = (
                        zf.read(CHECKSUM_NAME).decode("utf-8").strip().split()[0]
                    )
                    actual = hashlib.sha256(
                        zf.read(MANIFEST_NAME)
                    ).hexdigest()
                    if expected != actual:
                        errors.append(
                            f"manifest.json SHA-256 不匹配:期望 {expected}，实际 {actual}"
                        )
        except zipfile.BadZipFile as exc:
            return False, [f"无法解析 zip 文件:{exc}"]

    if check_file_digests:
        try:
            with zipfile.ZipFile(p, "r") as zf:
                names = set(zf.namelist())
                for entry in manifest.entries:
                    if entry.path not in names:
                        errors.append(f"缺失文件:{entry.path}")
                        continue
                    actual = hashlib.sha256(zf.read(entry.path)).hexdigest()
                    if actual != entry.sha256:
                        errors.append(
                            f"{entry.path}: SHA-256 不匹配"
                        )
        except zipfile.BadZipFile as exc:
            return False, [f"无法解析 zip 文件:{exc}"]

    return len(errors) == 0, errors


def extract_archive(
    zip_path: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """解压归档到指定目录。

    Returns:
        解压后的案件根目录路径
    """
    p = Path(zip_path)
    out = Path(output_dir).expanduser().resolve()
    if out.exists() and any(out.iterdir()) and not overwrite:
        raise ArchiveError(
            f"目标目录非空:{out}（如要覆盖请设 overwrite=True）"
        )
    out.mkdir(parents=True, exist_ok=True)

    manifest = read_manifest(p)
    # 验证完整性，失败则不解压
    ok, errors = verify_archive(p, check_manifest_checksum=False)
    if not ok:
        raise ArchiveError(f"归档校验失败:{'; '.join(errors)}")

    with zipfile.ZipFile(p, "r") as zf:
        for name in zf.namelist():
            if name in (MANIFEST_NAME, CHECKSUM_NAME):
                continue
            zf.extract(name, path=out)
    # 返回归档本身的根（即 out），文件已按归档内相对路径展开
    return Path(out)


# ============================================================
# 可选 AES-256 加密（依赖 cryptography）
# ============================================================


def _require_cryptography():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
    except ImportError as exc:
        raise ArchiveError(
            "加密/解密需要 cryptography 包，请运行 pip install cryptography"
        ) from exc


def encrypt_archive(
    zip_path: str | Path,
    output_path: str | Path,
    password: str,
) -> Path:
    """使用 AES-256-GCM 加密 zip 文件。

    格式:
        - 前 12 字节:nonce
        - 后续字节:AES-GCM 密文
    """
    _require_cryptography()
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    src = Path(zip_path)
    dst = Path(output_path)
    if not src.exists():
        raise ArchiveError(f"源文件不存在:{src}")
    key = hashlib.sha256(password.encode("utf-8")).digest()
    nonce = os.urandom(12)
    data = src.read_bytes()
    ciphertext = AESGCM(key).encrypt(nonce, data, associated_data=None)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(nonce + ciphertext)
    return dst


def decrypt_archive(
    enc_path: str | Path,
    output_path: str | Path,
    password: str,
) -> Path:
    """解密 AES-256-GCM 加密的 zip。"""
    _require_cryptography()
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    src = Path(enc_path)
    dst = Path(output_path)
    if not src.exists():
        raise ArchiveError(f"源文件不存在:{src}")
    raw = src.read_bytes()
    nonce, ciphertext = raw[:12], raw[12:]
    key = hashlib.sha256(password.encode("utf-8")).digest()
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, associated_data=None)
    except Exception as exc:
        raise ArchiveError(f"解密失败（密码错误或文件损坏）:{exc}") from exc
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(plaintext)
    return dst