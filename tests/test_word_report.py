"""Word 报告生成器单元测试(需要 python-docx)。"""

from __future__ import annotations

from pathlib import Path

import pytest


# 检测 python-docx 是否可用
try:
    import docx  # noqa: F401
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


pytestmark = pytest.mark.skipif(
    not HAS_DOCX, reason="需要 python-docx"
)


@pytest.fixture
def case_data() -> dict:
    return {
        "company_name": "X Co.",
        "company_address": "1 Road",
        "company_legal_person": "Alice",
        "worker_name": "Bob",
        "worker_phone": "13800138000",
        "worker_email": "bob@example.com",
        "violations": [
            {"type": "wage", "description": "9 月未发", "amount": "15000"},
            {"type": "overtime", "description": "强制加班", "amount": ""},
        ],
    }


@pytest.fixture
def evidence_list() -> list[dict]:
    return [
        {"name": "contract.pdf", "file_type": "document",
         "file_size": 1024, "description": "合同"},
        {"name": "salary.jpg", "file_type": "image",
         "file_size": 512, "description": "工资条"},
    ]


class TestWordReportGenerator:
    def test_init_creates_dir(self, tmp_path: Path):
        from wrg.word_report import WordReportGenerator

        out = tmp_path / "word-out"
        WordReportGenerator(out)
        assert out.exists()

    def test_init_default(self):
        from wrg.word_report import WordReportGenerator

        gen = WordReportGenerator()
        assert gen.output_dir.exists()

    def test_generate_zh(
        self,
        tmp_path: Path,
        case_data: dict,
        evidence_list: list[dict],
    ):
        from wrg.word_report import WordReportGenerator

        gen = WordReportGenerator(tmp_path)
        path = gen.generate(
            case_data, evidence_list, "X Co.", lang="zh"
        )
        assert Path(path).exists()
        assert path.endswith(".docx")

    def test_generate_en(
        self,
        tmp_path: Path,
        case_data: dict,
        evidence_list: list[dict],
    ):
        from wrg.word_report import WordReportGenerator

        gen = WordReportGenerator(tmp_path)
        path = gen.generate(
            case_data, evidence_list, "X Co.", lang="en"
        )
        assert Path(path).exists()

    def test_generate_empty_violations(
        self,
        tmp_path: Path,
        evidence_list: list[dict],
    ):
        from wrg.word_report import WordReportGenerator

        gen = WordReportGenerator(tmp_path)
        path = gen.generate({}, evidence_list, "case", lang="zh")
        assert Path(path).exists()

    def test_generate_no_evidence(
        self,
        tmp_path: Path,
        case_data: dict,
    ):
        from wrg.word_report import WordReportGenerator

        gen = WordReportGenerator(tmp_path)
        path = gen.generate(case_data, [], "case", lang="zh")
        assert Path(path).exists()


def test_safe_helper_chinese_preserved():
    """中文/Unicode 应原样保留。"""
    from wrg.word_report import WordReportGenerator

    # 静态方法应能直接调用,且中文不被替换
    assert WordReportGenerator._safe("") == ""
    out = WordReportGenerator._safe("测试 公司-1.pdf")
    assert "测试" in out
    assert "公司" in out


def test_safe_helper_strips_special():
    """特殊字符应被替换为下划线。"""
    from wrg.word_report import WordReportGenerator

    out = WordReportGenerator._safe("a/b\\c d?e")
    assert "/" not in out
    assert "\\" not in out
    assert "?" not in out
