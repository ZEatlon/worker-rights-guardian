"""JSON Schema 校验单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wrg.schema import (
    ValidationError,
    validate_case_info,
    validate_institutions,
    validate_scenario,
)


class TestCaseInfoSchema:
    def test_minimal_ok(self):
        validate_case_info(
            {
                "company_name": "A",
                "company_address": "B",
                "worker_name": "C",
                "worker_phone": "1",
            }
        )

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            validate_case_info({"company_name": "A"})

    def test_top_level_must_be_dict(self):
        with pytest.raises(ValidationError):
            validate_case_info("not a dict")  # type: ignore[arg-type]

    def test_string_field_wrong_type(self):
        with pytest.raises(ValidationError):
            validate_case_info(
                {
                    "company_name": 123,  # 应为字符串
                    "company_address": "B",
                    "worker_name": "C",
                    "worker_phone": "1",
                }
            )

    def test_violations_structure(self):
        validate_case_info(
            {
                "company_name": "A",
                "company_address": "B",
                "worker_name": "C",
                "worker_phone": "1",
                "violations": [
                    {"type": "wage", "description": "x", "amount": "100"},
                ],
            }
        )

    def test_violations_missing_fields(self):
        with pytest.raises(ValidationError):
            validate_case_info(
                {
                    "company_name": "A",
                    "company_address": "B",
                    "worker_name": "C",
                    "worker_phone": "1",
                    "violations": [{"type": "wage"}],  # 缺 description
                }
            )

    def test_violations_not_list(self):
        with pytest.raises(ValidationError):
            validate_case_info(
                {
                    "company_name": "A",
                    "company_address": "B",
                    "worker_name": "C",
                    "worker_phone": "1",
                    "violations": "not a list",
                }
            )

    def test_violation_item_not_dict(self):
        with pytest.raises(ValidationError):
            validate_case_info(
                {
                    "company_name": "A",
                    "company_address": "B",
                    "worker_name": "C",
                    "worker_phone": "1",
                    "violations": ["string"],
                }
            )


class TestScenarioSchema:
    def test_minimal_ok(self):
        validate_scenario({"name": "t", "steps": [{"type": "wage"}]})

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            validate_scenario({"steps": [{"type": "wage"}]})

    def test_missing_steps(self):
        with pytest.raises(ValidationError):
            validate_scenario({"name": "t"})

    def test_empty_steps(self):
        with pytest.raises(ValidationError):
            validate_scenario({"name": "t", "steps": []})

    def test_step_missing_type(self):
        with pytest.raises(ValidationError):
            validate_scenario({"name": "t", "steps": [{}]})

    def test_step_invalid_type(self):
        with pytest.raises(ValidationError):
            validate_scenario({"name": "t", "steps": [{"type": "bogus"}]})

    def test_step_invalid_lang(self):
        with pytest.raises(ValidationError):
            validate_scenario(
                {"name": "t", "steps": [{"type": "wage", "lang": "xx"}]}
            )

    def test_step_institutions_not_list(self):
        with pytest.raises(ValidationError):
            validate_scenario(
                {
                    "name": "t",
                    "steps": [{"type": "wage", "institutions": "A"}],
                }
            )

    def test_step_institution_not_string(self):
        with pytest.raises(ValidationError):
            validate_scenario(
                {
                    "name": "t",
                    "steps": [
                        {"type": "wage", "institutions": [123]}
                    ],
                }
            )

    def test_top_level_not_dict(self):
        with pytest.raises(ValidationError):
            validate_scenario([{"name": "t"}])  # type: ignore[arg-type]

    def test_step_not_dict(self):
        with pytest.raises(ValidationError):
            validate_scenario({"name": "t", "steps": ["x"]})


class TestInstitutionsSchema:
    def test_ok(self):
        validate_institutions(
            {
                "china": [
                    {"name": "A", "email": "a@b.com"},
                ]
            }
        )

    def test_top_not_dict(self):
        with pytest.raises(ValidationError):
            validate_institutions([{"name": "A"}])  # type: ignore[arg-type]

    def test_category_not_list(self):
        with pytest.raises(ValidationError):
            validate_institutions({"china": "not list"})

    def test_item_not_dict(self):
        with pytest.raises(ValidationError):
            validate_institutions({"china": ["A"]})

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            validate_institutions({"china": [{"email": "a@b.com"}]})

    def test_missing_contact(self):
        with pytest.raises(ValidationError):
            validate_institutions({"china": [{"name": "A"}]})

    def test_url_only_ok(self):
        validate_institutions(
            {"china": [{"name": "A", "url": "https://x"}]}
        )


class TestValidateFiles:
    def test_validate_yaml_file_ok(self, tmp_path: Path):
        p = tmp_path / "sc.yaml"
        p.write_text(
            "name: t\nsteps:\n  - type: wage\n    lang: zh\n",
            encoding="utf-8",
        )
        from wrg.schema import validate_yaml_file

        data = validate_yaml_file(p, "scenario")
        assert data["name"] == "t"

    def test_validate_yaml_file_missing(self, tmp_path: Path):
        from wrg.schema import validate_yaml_file

        with pytest.raises(ValidationError):
            validate_yaml_file(tmp_path / "nope.yaml", "scenario")

    def test_validate_yaml_corrupt(self, tmp_path: Path):
        from wrg.schema import validate_yaml_file

        p = tmp_path / "bad.yaml"
        p.write_text(":\n- :\n", encoding="utf-8")
        with pytest.raises(ValidationError):
            validate_yaml_file(p, "scenario")

    def test_validate_yaml_unknown_kind(self, tmp_path: Path):
        from wrg.schema import validate_yaml_file

        p = tmp_path / "x.yaml"
        p.write_text("name: t\n", encoding="utf-8")
        with pytest.raises(ValidationError):
            validate_yaml_file(p, "bogus")

    def test_validate_json_file_ok(self, tmp_path: Path):
        import json
        from wrg.schema import validate_json_file

        p = tmp_path / "c.json"
        p.write_text(
            json.dumps(
                {
                    "company_name": "A",
                    "company_address": "B",
                    "worker_name": "C",
                    "worker_phone": "1",
                }
            ),
            encoding="utf-8",
        )
        data = validate_json_file(p, "case_info")
        assert data["company_name"] == "A"

    def test_validate_json_corrupt(self, tmp_path: Path):
        from wrg.schema import validate_json_file

        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(ValidationError):
            validate_json_file(p, "case_info")

    def test_validate_json_missing(self, tmp_path: Path):
        from wrg.schema import validate_json_file

        with pytest.raises(ValidationError):
            validate_json_file(tmp_path / "nope.json", "case_info")

    def test_validate_json_unknown_kind(self, tmp_path: Path):
        from wrg.schema import validate_json_file

        p = tmp_path / "x.json"
        p.write_text("{}", encoding="utf-8")
        with pytest.raises(ValidationError):
            validate_json_file(p, "scenario")
