"""报告生成器单元测试。"""

from __future__ import annotations

from pathlib import Path

from wrg.report_generator import ReportGenerator, _safe_filename, now_pretty


class TestSafeFilename:
    def test_basic(self):
        assert _safe_filename("测试 公司 名") == "测试_公司_名"

    def test_alphanumeric_kept(self):
        assert _safe_filename("file-1.txt") == "file-1.txt"

    def test_special_chars_replaced(self):
        assert _safe_filename("a/b\\c:d*e?f") == "a_b_c_d_e_f"

    def test_empty(self):
        assert _safe_filename("") == ""

    def test_truncation(self):
        s = "x" * 200
        out = _safe_filename(s)
        assert len(out) == 80


class TestNowPretty:
    def test_returns_string(self):
        s = now_pretty()
        assert isinstance(s, str)
        assert len(s) > 0


class TestReportGenerator:
    def test_init_creates_dir(self, tmp_path: Path):
        out = tmp_path / "reports"
        gen = ReportGenerator(out)
        assert out.exists()

    def test_init_default(self):
        gen = ReportGenerator()
        assert gen.output_dir.exists()

    def test_generate_text(self, tmp_path: Path):
        gen = ReportGenerator(tmp_path)
        path = gen.generate_text("报告内容\n第二行", "测试案件")
        assert Path(path).exists()
        content = Path(path).read_text("utf-8")
        assert "报告内容" in content

    def test_generate_text_filename_uses_case_name(self, tmp_path: Path):
        gen = ReportGenerator(tmp_path)
        path = gen.generate_text("x", "我的案件")
        name = Path(path).name
        assert name.startswith("report_我的案件_")

    def test_generate_summary(self, tmp_path: Path):
        gen = ReportGenerator(tmp_path)
        summary = gen.generate_summary(
            {"company_name": "X公司", "worker_name": "张三", "worker_phone": "1"},
            [{"name": "ILO", "email": "ilo@ilo.org"}],
            3,
        )
        assert "X公司" in summary
        assert "张三" in summary
        assert "ILO" in summary
        assert "ilo@ilo.org" in summary
        assert "证据数量: 3" in summary
        assert "=" in summary

    def test_generate_summary_handles_missing_fields(self, tmp_path: Path):
        gen = ReportGenerator(tmp_path)
        summary = gen.generate_summary({}, [], 0)
        assert "未命名" in summary
        assert "匿名" in summary
