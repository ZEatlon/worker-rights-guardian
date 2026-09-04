"""模板引擎单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wrg.template_engine import TemplateEngine


class TestTemplateEngine:
    def test_render_string_simple(self):
        eng = TemplateEngine(template_dir=Path("/nonexistent-but-tolerated"))
        out = eng.render_string("Hello {{ name }}", {"name": "World"})
        assert out == "Hello World"

    def test_render_string_filters(self):
        eng = TemplateEngine(template_dir=Path("/nonexistent-but-tolerated"))
        out = eng.render_string(
            "{{ value | format_currency }}",
            {"value": 1234.5},
        )
        assert "1,234.50" in out

    def test_render_string_format_date(self):
        eng = TemplateEngine(template_dir=Path("/nonexistent-but-tolerated"))
        out = eng.render_string(
            "{{ d | format_date('%Y/%m') }}",
            {"d": "2024-09-15"},
        )
        assert out == "2024/09"

    def test_render_string_format_date_invalid(self):
        eng = TemplateEngine(template_dir=Path("/nonexistent-but-tolerated"))
        out = eng.render_string(
            "{{ d | format_date }}",
            {"d": "not a date"},
        )
        assert out == "not a date"

    def test_render_with_real_template(
        self,
        template_dir: Path,
    ):
        eng = TemplateEngine(template_dir=template_dir)
        out = eng.render(
            "zh/labor_complaint.jinja2",
            {
                "institution_name": "测试机构",
                "company_name": "测试公司",
                "company_address": "上海市某路 1 号",
                "company_legal_person": "张三",
                "company_credit_code": "",
                "company_phone": "",
                "worker_name": "李四",
                "worker_phone": "13800138000",
                "worker_email": "a@b.com",
                "entry_date": "2024-01-01",
                "job_position": "工程师",
                "contract_status": "已签订",
                "report_date": "2026-09-03",
                "violations": [
                    {"type": "拖欠工资", "description": "9月工资未发", "amount": "15000"}
                ],
                "evidence_list": [],
                "total_claim": "30000",
                "other_requests": "无",
                "measures_taken": "无",
            },
        )
        assert "测试公司" in out
        assert "测试机构" in out
        assert "李四" in out
        assert "拖欠工资" in out
        assert "共 0 项证据" in out

    def test_has_template_true(self, template_dir: Path):
        eng = TemplateEngine(template_dir=template_dir)
        assert eng.has_template("zh/labor_complaint.jinja2")

    def test_has_template_false(self):
        eng = TemplateEngine(template_dir=Path("/nonexistent-but-tolerated"))
        assert not eng.has_template("nonexistent.jinja2")

    def test_list_templates(self, template_dir: Path):
        eng = TemplateEngine(template_dir=template_dir)
        templates = eng.list_templates()
        assert any(t["language"] == "zh" for t in templates)
        assert any("labor_complaint" in t["name"] for t in templates)

    def test_list_templates_filter_language(self, template_dir: Path):
        eng = TemplateEngine(template_dir=template_dir)
        templates = eng.list_templates(language="zh")
        assert all(t["language"] == "zh" for t in templates)

    def test_strict_undefined_raises(self):
        eng = TemplateEngine(template_dir=Path("/nonexistent-but-tolerated"), strict=True)
        with pytest.raises(Exception):
            eng.render_string("{{ undefined_var }}", {})

    def test_autoescape_off_for_text(self):
        eng = TemplateEngine(
            template_dir=Path("/nonexistent-but-tolerated"),
            autoescape=False,
        )
        out = eng.render_string("<b>{{ x }}</b>", {"x": "<script>"})
        assert "<script>" in out

    def test_create_template_dir_if_missing(self, tmp_path):
        target = tmp_path / "new-templates"
        # 模板目录不存在,引擎应能容忍
        eng = TemplateEngine(template_dir=target)
        # 第一次访问时已被引擎创建
        assert target.exists()
