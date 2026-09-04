"""证据管理单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wrg.evidence import (
    EvidenceItem,
    EvidenceManager,
    classify_extension,
    sha256_of,
)


class TestClassifyExtension:
    def test_image(self):
        assert classify_extension(".jpg") == "image"
        assert classify_extension(".png") == "image"
        assert classify_extension(".HEIC") == "image"

    def test_document(self):
        assert classify_extension(".pdf") == "document"
        assert classify_extension(".docx") == "document"

    def test_audio(self):
        assert classify_extension(".mp3") == "audio"

    def test_video(self):
        assert classify_extension(".mp4") == "video"

    def test_text(self):
        assert classify_extension(".txt") == "text"
        assert classify_extension(".md") == "text"

    def test_unknown(self):
        assert classify_extension(".bin") == "unknown"
        assert classify_extension("") == "unknown"

    def test_without_dot(self):
        assert classify_extension("jpg") == "image"


class TestSha256:
    def test_known_text(self, tmp_path: Path):
        p = tmp_path / "a.txt"
        p.write_text("hello", encoding="utf-8")
        expected = (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )
        assert sha256_of(p) == expected

    def test_different_size_chunks(self, tmp_path: Path):
        p = tmp_path / "big.bin"
        p.write_bytes(b"x" * 100000)
        h1 = sha256_of(p, chunk=1024)
        h2 = sha256_of(p, chunk=65536)
        assert h1 == h2


class TestEvidenceItem:
    def test_roundtrip(self):
        item = EvidenceItem(
            id="EVD_xxx",
            name="x.txt",
            file_path="/tmp/x.txt",
            file_type="text",
            file_size=10,
            checksum="abc",
            description="d",
            tags=["t1", "t2"],
        )
        d = item.to_dict()
        assert d["id"] == "EVD_xxx"
        again = EvidenceItem.from_dict(d)
        assert again.id == item.id
        assert again.tags == item.tags

    def test_from_dict_missing_fields(self):
        item = EvidenceItem.from_dict({"id": "X"})
        assert item.id == "X"
        assert item.tags == []
        assert item.file_size == 0


class TestEvidenceManager:
    def test_init_creates_dirs(self, tmp_case_dir: Path):
        mgr = EvidenceManager(tmp_case_dir)
        assert (tmp_case_dir / "evidence").exists()
        assert mgr.evidence_list == []

    def test_add_text_file(
        self,
        tmp_case_dir: Path,
        sample_text_file: Path,
    ):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(
            sample_text_file,
            description="示例文本",
            tags=["测试"],
        )
        assert item.id.startswith("EVD_")
        assert item.file_type == "text"
        assert item.tags == ["测试"]
        # 文件已复制到 evidence/
        assert Path(item.file_path).exists()
        # 校验和正确
        assert sha256_of(item.file_path) == item.checksum
        # 索引已保存
        index_data = json.loads(
            (tmp_case_dir / "evidence_index.json").read_text("utf-8")
        )
        assert len(index_data) == 1

    def test_add_image(self, tmp_case_dir: Path, sample_png_file: Path):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(sample_png_file)
        assert item.file_type == "image"
        assert item.file_size > 0

    def test_add_pdf(self, tmp_case_dir: Path, sample_pdf_file: Path):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(sample_pdf_file)
        assert item.file_type == "document"

    def test_add_missing_file_raises(self, tmp_case_dir: Path):
        mgr = EvidenceManager(tmp_case_dir)
        with pytest.raises(FileNotFoundError):
            mgr.add_evidence("/nonexistent/path/file.jpg")

    def test_add_unsupported_type_raises(
        self,
        tmp_case_dir: Path,
        tmp_path: Path,
    ):
        mgr = EvidenceManager(tmp_case_dir)
        bin_file = tmp_path / "weird.bin"
        bin_file.write_bytes(b"\x00" * 8)
        with pytest.raises(ValueError):
            mgr.add_evidence(bin_file)

    def test_add_text_evidence(self, tmp_case_dir: Path):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_text_evidence(
            "聊天记录内容",
            "wechat.txt",
            description="微信聊天",
        )
        assert item.file_type == "text"
        assert Path(item.file_path).read_text("utf-8") == "聊天记录内容"

    def test_add_text_evidence_empty_name_raises(self, tmp_case_dir: Path):
        mgr = EvidenceManager(tmp_case_dir)
        with pytest.raises(ValueError):
            mgr.add_text_evidence("x", "")

    def test_list_evidence_filter_by_type(
        self,
        tmp_case_dir: Path,
        sample_text_file: Path,
        sample_png_file: Path,
    ):
        mgr = EvidenceManager(tmp_case_dir)
        mgr.add_evidence(sample_text_file)
        mgr.add_evidence(sample_png_file)
        assert len(mgr.list_evidence()) == 2
        assert len(mgr.list_evidence(file_type="image")) == 1
        assert len(mgr.list_evidence(file_type="text")) == 1

    def test_list_evidence_filter_by_tag(
        self,
        tmp_case_dir: Path,
        sample_text_file: Path,
    ):
        mgr = EvidenceManager(tmp_case_dir)
        mgr.add_evidence(sample_text_file, tags=["工资"])
        mgr.add_evidence(sample_text_file, tags=["加班"])
        assert len(mgr.list_evidence(tag="工资")) == 1

    def test_get_evidence(self, tmp_case_dir: Path, sample_text_file: Path):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(sample_text_file)
        assert mgr.get_evidence(item.id) == item
        assert mgr.get_evidence("nonexistent") is None

    def test_remove_evidence(
        self,
        tmp_case_dir: Path,
        sample_text_file: Path,
    ):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(sample_text_file)
        path = Path(item.file_path)
        assert path.exists()
        assert mgr.remove_evidence(item.id) is True
        assert not path.exists()
        assert mgr.list_evidence() == []
        assert mgr.remove_evidence(item.id) is False

    def test_persistence_across_instances(
        self,
        tmp_case_dir: Path,
        sample_text_file: Path,
    ):
        mgr1 = EvidenceManager(tmp_case_dir)
        item = mgr1.add_evidence(sample_text_file)
        # 重新创建实例应能加载已持久化的索引
        mgr2 = EvidenceManager(tmp_case_dir)
        assert len(mgr2.evidence_list) == 1
        assert mgr2.evidence_list[0].id == item.id

    def test_corrupt_index_resets_gracefully(self, tmp_case_dir: Path):
        (tmp_case_dir / "evidence_index.json").write_text(
            "{not valid json", encoding="utf-8"
        )
        mgr = EvidenceManager(tmp_case_dir)
        assert mgr.evidence_list == []

    def test_verify_integrity(
        self,
        tmp_case_dir: Path,
        sample_text_file: Path,
    ):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(sample_text_file)
        results = mgr.verify_integrity()
        assert results == [(item.id, True)]

    def test_verify_integrity_detects_tamper(
        self,
        tmp_case_dir: Path,
        sample_text_file: Path,
    ):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(sample_text_file)
        # 篡改文件
        Path(item.file_path).write_text("篡改", encoding="utf-8")
        results = mgr.verify_integrity()
        assert results == [(item.id, False)]

    def test_summary_format(self, tmp_case_dir: Path, sample_text_file: Path):
        mgr = EvidenceManager(tmp_case_dir)
        mgr.add_evidence(sample_text_file, description="工资条")
        summary = mgr.generate_evidence_summary()
        assert "# 证据清单" in summary
        assert "工资条" in summary
        assert str(mgr.evidence_list[0].checksum[:16]) in summary

    def test_id_format(self, tmp_case_dir: Path, sample_text_file: Path):
        mgr = EvidenceManager(tmp_case_dir)
        item = mgr.add_evidence(sample_text_file)
        # 形如 EVD_YYYYMMDD_HHMMSS_xxxxxxxx
        parts = item.id.split("_")
        assert len(parts) == 3
        assert parts[0] == "EVD"
        assert len(parts[1]) == 15  # YYYYMMDD_HHMMSS
        assert len(parts[2]) == 8
