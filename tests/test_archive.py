"""案件打包(archive)模块单元测试。"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from wrg.archive import (
    ArchiveBuilder,
    ArchiveEntry,
    ArchiveError,
    ArchiveManifest,
    CHECKSUM_NAME,
    MANIFEST_NAME,
    _classify,
    _hash_file,
    decrypt_archive,
    encrypt_archive,
    extract_archive,
    read_manifest,
    verify_archive,
)


@pytest.fixture
def sample_case(tmp_path: Path) -> Path:
    """构造一个最小可用案件目录。"""
    case = tmp_path / "case"
    case.mkdir()
    info = {
        "company_name": "ACME",
        "company_address": "上海市某路 1 号",
        "worker_name": "李四",
        "worker_phone": "13800138000",
        "violations": [{"type": "wage", "description": "欠薪", "amount": "1000"}],
    }
    (case / "case_info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (case / "evidence_index.json").write_text("[]", encoding="utf-8")

    ev_dir = case / "evidence"
    ev_dir.mkdir()
    (ev_dir / "a.txt").write_text("evidence A", encoding="utf-8")
    (ev_dir / "b.txt").write_text("evidence B", encoding="utf-8")

    mails_dir = case / "mails"
    mails_dir.mkdir()
    (mails_dir / "draft.eml").write_text("dummy eml", encoding="utf-8")

    return case


class TestArchiveBuilder:
    def test_init_missing_dir(self, tmp_path: Path):
        with pytest.raises(ArchiveError):
            ArchiveBuilder(tmp_path / "nope")

    def test_iter_files_excludes_pycache(self, sample_case: Path):
        # 故意放一个 __pycache__/x.pyc
        cache_dir = sample_case / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "x.pyc").write_bytes(b"")
        builder = ArchiveBuilder(sample_case)
        rels = [str(p.relative_to(sample_case)).replace("\\", "/")
                for p in builder.iter_files()]
        assert all("__pycache__" not in r for r in rels)

    def test_build_manifest(self, sample_case: Path):
        builder = ArchiveBuilder(sample_case, tool_version="test-1")
        manifest = builder.build_manifest()
        assert manifest.case_dir == str(sample_case)
        assert manifest.tool_version == "test-1"
        assert len(manifest.entries) >= 4  # case_info + index + 2 evidence + 1 mail

        paths = {e.path for e in manifest.entries}
        assert "case_info.json" in paths
        assert "evidence/a.txt" in paths
        assert "mails/draft.eml" in paths

        for entry in manifest.entries:
            assert len(entry.sha256) == 64
            assert entry.size > 0

    def test_classification(self):
        assert _classify("case_info.json") == "case_info"
        assert _classify("evidence_index.json") == "case_info"
        assert _classify("evidence/foo.pdf") == "evidence"
        assert _classify("mails/x.eml") == "mail"
        assert _classify("reports/y.docx") == "report"
        assert _classify("misc.txt") == "other"

    def test_hash_file(self, tmp_path: Path):
        f = tmp_path / "x.txt"
        f.write_text("hi", encoding="utf-8")
        h = _hash_file(f)
        assert len(h) == 64
        assert h == _hash_file(f)  # 确定性

    def test_write_zip(self, sample_case: Path, tmp_path: Path):
        out = tmp_path / "test.zip"
        builder = ArchiveBuilder(sample_case, tool_version="0.3")
        path, manifest = builder.write_zip(out)
        assert path.exists()
        assert path == out
        # zip 内部应含 manifest.json + manifest.sha256
        with zipfile.ZipFile(out) as zf:
            assert MANIFEST_NAME in zf.namelist()
            assert CHECKSUM_NAME in zf.namelist()
            assert "case_info.json" in zf.namelist()
            assert "evidence/a.txt" in zf.namelist()

    def test_write_zip_overwrites_silently(self, sample_case: Path, tmp_path: Path):
        """写 zip 使用 .tmp + rename,因此会原子覆盖,不会抛 FileExistsError。"""
        out = tmp_path / "test.zip"
        ArchiveBuilder(sample_case).write_zip(out)
        # 第二次写不应报错,而应原子覆盖
        ArchiveBuilder(sample_case).write_zip(out)
        assert out.exists()
        # 仍然可正常读取
        manifest = read_manifest(out)
        assert manifest.entries

    def test_write_zip_with_yes_flag_via_init(
        self, sample_case: Path, tmp_path: Path,
    ):
        out = tmp_path / "test.zip"
        ArchiveBuilder(sample_case).write_zip(out)
        # 模拟 --yes:删除后重建
        out.unlink()
        ArchiveBuilder(sample_case).write_zip(out)
        assert out.exists()


class TestReadAndVerify:
    def test_read_manifest(self, sample_case: Path, tmp_path: Path):
        zip_path, manifest = ArchiveBuilder(sample_case).write_zip(
            tmp_path / "x.zip"
        )
        loaded = read_manifest(zip_path)
        assert loaded.case_dir == manifest.case_dir
        assert len(loaded.entries) == len(manifest.entries)

    def test_read_manifest_missing(self, tmp_path: Path):
        with pytest.raises(ArchiveError):
            read_manifest(tmp_path / "nope.zip")

    def test_read_manifest_bad_zip(self, tmp_path: Path):
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not a zip")
        with pytest.raises(ArchiveError):
            read_manifest(bad)

    def test_verify_ok(self, sample_case: Path, tmp_path: Path):
        zip_path, _ = ArchiveBuilder(sample_case).write_zip(
            tmp_path / "x.zip"
        )
        ok, errors = verify_archive(zip_path)
        assert ok is True
        assert errors == []

    def test_verify_missing(self, tmp_path: Path):
        ok, errors = verify_archive(tmp_path / "nope.zip")
        assert ok is False
        assert errors

    def test_verify_tamper_detected(self, sample_case: Path, tmp_path: Path):
        zip_path, _ = ArchiveBuilder(sample_case).write_zip(
            tmp_path / "x.zip"
        )
        # 篡改 zip 中的一个文件
        with zipfile.ZipFile(zip_path, "a") as zf:
            zf.writestr("evidence/a.txt", "TAMPERED")
        ok, errors = verify_archive(zip_path)
        assert ok is False
        assert any("evidence/a.txt" in e for e in errors)


class TestExtract:
    def test_extract(self, sample_case: Path, tmp_path: Path):
        zip_path, _ = ArchiveBuilder(sample_case).write_zip(
            tmp_path / "x.zip"
        )
        out = tmp_path / "extracted"
        target = extract_archive(zip_path, out)
        assert target.exists()
        # 关键文件应恢复
        assert (target / "case_info.json").exists()
        assert (target / "evidence" / "a.txt").exists()

    def test_extract_target_not_empty_fails(
        self, sample_case: Path, tmp_path: Path,
    ):
        zip_path, _ = ArchiveBuilder(sample_case).write_zip(
            tmp_path / "x.zip"
        )
        out = tmp_path / "extracted"
        out.mkdir()
        (out / "stuff.txt").write_text("x", encoding="utf-8")
        with pytest.raises(ArchiveError):
            extract_archive(zip_path, out)
        # overwrite=True 可继续
        extract_archive(zip_path, out, overwrite=True)

    def test_extract_corrupt_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not a zip")
        with pytest.raises(ArchiveError):
            extract_archive(bad, tmp_path / "out")


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(
        self, sample_case: Path, tmp_path: Path,
    ):
        zip_path, _ = ArchiveBuilder(sample_case).write_zip(
            tmp_path / "x.zip"
        )
        enc = tmp_path / "x.zip.enc"
        try:
            encrypt_archive(zip_path, enc, "secret-pwd")
        except ArchiveError:
            pytest.skip("cryptography 未安装")
        assert enc.exists()
        # 解密
        dec = tmp_path / "x_dec.zip"
        decrypt_archive(enc, dec, "secret-pwd")
        assert dec.exists()
        # 应能正常解析
        manifest = read_manifest(dec)
        assert manifest.case_dir == str(sample_case)

    def test_encrypt_wrong_password_raises(
        self, sample_case: Path, tmp_path: Path,
    ):
        zip_path, _ = ArchiveBuilder(sample_case).write_zip(
            tmp_path / "x.zip"
        )
        enc = tmp_path / "x.zip.enc"
        try:
            encrypt_archive(zip_path, enc, "correct")
        except ArchiveError:
            pytest.skip("cryptography 未安装")
        with pytest.raises(ArchiveError):
            decrypt_archive(enc, tmp_path / "out.zip", "wrong")


class TestManifestSerialization:
    def test_roundtrip(self):
        m = ArchiveManifest(
            case_dir="X",
            created_at="now",
            tool_version="0.3",
            entries=[
                ArchiveEntry(path="a.txt", size=10, sha256="x" * 64,
                             file_type="other"),
            ],
            metadata={"k": 1},
        )
        data = m.to_dict()
        m2 = ArchiveManifest.from_dict(data)
        assert m2.case_dir == "X"
        assert m2.tool_version == "0.3"
        assert m2.entries[0].path == "a.txt"
        assert m2.metadata == {"k": 1}

    def test_total_size(self):
        m = ArchiveManifest(
            case_dir="X",
            created_at="now",
            tool_version="0.3",
            entries=[
                ArchiveEntry("a", 100, "h", "x"),
                ArchiveEntry("b", 200, "h", "x"),
            ],
        )
        assert m.total_size == 300
