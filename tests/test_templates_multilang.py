"""多语言模板渲染测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wrg.template_engine import TemplateEngine


@pytest.fixture
def engine(template_dir: Path) -> TemplateEngine:
    return TemplateEngine(template_dir=template_dir)


class TestMultilangTemplates:
    """验证 zh / en / ja / ko 四种模板都可独立渲染。"""

    COMMON_CONTEXT: dict = {
        "institution_name": "Test Institution",
        "company_name": "Test Corp",
        "company_address": "1 Test Street",
        "company_legal_person": "Alice",
        "company_credit_code": "",
        "company_phone": "",
        "worker_name": "Bob",
        "worker_phone": "13800138000",
        "worker_email": "bob@example.com",
        "entry_date": "2024-01-01",
        "job_position": "Engineer",
        "contract_status": "Signed",
        "report_date": "2026-09-03",
        "violations": [
            {"type": "Wage Theft", "description": "Sep unpaid", "amount": "15000"}
        ],
        "evidence_list": [],
        "total_claim": "30000",
        "other_requests": "",
        "measures_taken": "",
        "currency": "",
    }

    def test_zh_renders(self, engine: TemplateEngine):
        out = engine.render("zh/labor_complaint.jinja2", self.COMMON_CONTEXT)
        assert "Test Corp" in out
        assert "Bob" in out
        assert "投诉" in out or "举报" in out

    def test_en_renders(self, engine: TemplateEngine):
        out = engine.render("en/labor_complaint.jinja2", self.COMMON_CONTEXT)
        assert "Test Corp" in out
        assert "Bob" in out
        assert "Complaint" in out
        # 英文模板使用英文术语
        assert "Wage Theft" in out

    def test_ja_renders(self, engine: TemplateEngine):
        out = engine.render("ja/labor_complaint.jinja2", self.COMMON_CONTEXT)
        assert "Test Corp" in out
        assert "Bob" in out
        assert "告発" in out or "請求" in out

    def test_ko_renders(self, engine: TemplateEngine):
        out = engine.render("ko/labor_complaint.jinja2", self.COMMON_CONTEXT)
        assert "Test Corp" in out
        assert "Bob" in out
        assert "신고" in out or "청구" in out

    def test_all_languages_have_subject(self, engine: TemplateEngine):
        """每种模板应至少能渲染出非空输出。"""
        for lang, path in [
            ("zh", "zh/labor_complaint.jinja2"),
            ("en", "en/labor_complaint.jinja2"),
            ("ja", "ja/labor_complaint.jinja2"),
            ("ko", "ko/labor_complaint.jinja2"),
        ]:
            out = engine.render(path, self.COMMON_CONTEXT)
            assert len(out) > 50, f"{lang} 模板输出过短({len(out)} 字符)"

    def test_evidence_list_with_data(self, engine: TemplateEngine):
        ctx = dict(self.COMMON_CONTEXT)
        ctx["evidence_list"] = [
            {"name": "a.pdf", "file_type": "document",
             "file_size": 1024, "description": "合同"},
        ]
        out = engine.render("zh/labor_complaint.jinja2", ctx)
        assert "a.pdf" in out
        assert "合同" in out

    def test_violations_loop(self, engine: TemplateEngine):
        ctx = dict(self.COMMON_CONTEXT)
        ctx["violations"] = [
            {"type": "Type A", "description": "Desc A", "amount": "100"},
            {"type": "Type B", "description": "Desc B", "amount": "200"},
        ]
        out = engine.render("en/labor_complaint.jinja2", ctx)
        assert "Type A" in out
        assert "Type B" in out
        assert "[1]" in out
        assert "[2]" in out
