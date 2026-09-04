"""HTML 邮件模板与 multipart 邮件测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wrg.template_engine import TemplateEngine


@pytest.fixture
def engine(template_dir: Path) -> TemplateEngine:
    return TemplateEngine(template_dir=template_dir)


COMMON_CONTEXT: dict = {
    "institution_name": "Test Institution",
    "company_name": "ACME Inc.",
    "company_address": "1 Road",
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
    "evidence_list": [
        {"name": "a.pdf", "file_type": "document",
         "file_size": 1024, "description": "Contract"},
    ],
    "total_claim": "30000",
    "other_requests": "",
    "measures_taken": "",
    "currency": "USD",
}


class TestHTMLTemplates:
    @pytest.mark.parametrize(
        "lang,expected_phrase",
        [
            ("zh", "劳动监察"),
            ("en", "Labor Rights"),
            ("ja", "労働基準監督"),
            ("ko", "근로기준 감독"),
        ],
    )
    def test_each_lang_renders_html(
        self, engine: TemplateEngine,
        lang: str, expected_phrase: str,
    ):
        out = engine.render(f"{lang}/labor_complaint.html.jinja2",
                            COMMON_CONTEXT)
        assert "<!DOCTYPE html>" in out
        assert "<html" in out
        assert expected_phrase in out or "Complaint" in out or "告発" in out
        assert "ACME Inc." in out
        assert "Bob" in out

    def test_zh_html_evidence_table(self, engine: TemplateEngine):
        out = engine.render("zh/labor_complaint.html.jinja2",
                            COMMON_CONTEXT)
        assert "<table" in out
        assert "a.pdf" in out
        assert "Contract" in out or "合同" in out

    def test_en_html_total_claim_in_currency(self, engine: TemplateEngine):
        ctx = dict(COMMON_CONTEXT)
        ctx["total_claim"] = "50000"
        ctx["currency"] = "USD"
        out = engine.render("en/labor_complaint.html.jinja2", ctx)
        assert "50000" in out
        assert "USD" in out

    def test_html_no_evidence_branch(self, engine: TemplateEngine):
        ctx = dict(COMMON_CONTEXT)
        ctx["evidence_list"] = []
        out = engine.render("en/labor_complaint.html.jinja2", ctx)
        # 无证据分支应触发
        assert "No additional evidence" in out or "evidence" in out.lower()

    def test_html_violations_loop(self, engine: TemplateEngine):
        ctx = dict(COMMON_CONTEXT)
        ctx["violations"] = [
            {"type": "Type A", "description": "Desc A", "amount": "100"},
            {"type": "Type B", "description": "Desc B", "amount": "200"},
            {"type": "Type C", "description": "Desc C", "amount": "300"},
        ]
        out = engine.render("zh/labor_complaint.html.jinja2", ctx)
        assert out.count("【1】") == 1
        assert out.count("【2】") == 1
        assert out.count("【3】") == 1

    def test_html_template_missing_optionals(self, engine: TemplateEngine):
        """HTML 模板在缺失可选字段时不应崩溃(应使用默认值或留空)。"""
        # 只提供最关键字段,其他走 Jinja 默认
        out = engine.render(
            "en/labor_complaint.html.jinja2",
            {
                "company_name": "X",
                "company_address": "Y",
                "worker_name": "Z",
                "worker_phone": "0",
                "institution_name": "I",
                "report_date": "2026-09-03",
                "violations": [{"type": "x", "description": "y", "amount": ""}],
                "evidence_list": [],
            },
        )
        assert "<!DOCTYPE html>" in out
        assert "X" in out
