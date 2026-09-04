"""剧本(scenario)机制单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wrg.institution_db import InstitutionDB
from wrg.scenario import load_scenario


@pytest.fixture
def db() -> InstitutionDB:
    return InstitutionDB()


class TestLoadScenario:
    def test_load_minimal(self, tmp_path: Path):
        p = tmp_path / "sc.yaml"
        p.write_text(
            "name: t\nsteps:\n  - type: wage\n    lang: zh\n    institutions:\n      - ILO - 日内瓦总部\n",
            encoding="utf-8",
        )
        sc = load_scenario(p)
        assert sc.name == "t"
        assert len(sc.steps) == 1
        assert sc.steps[0].type == "wage"
        assert sc.steps[0].lang == "zh"
        assert sc.steps[0].institutions == ["ILO - 日内瓦总部"]

    def test_load_real_scenario(self, project_root: Path):
        sc = load_scenario(project_root / "config" / "scenarios" / "wage_default.yaml")
        assert sc.name
        assert len(sc.steps) >= 1

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_scenario(tmp_path / "nope.yaml")

    def test_invalid_yaml_raises(self, tmp_path: Path):
        p = tmp_path / "bad.yaml"
        p.write_text("name: t\nsteps:\n  - this is: not: a: dict", encoding="utf-8")
        with pytest.raises(ValueError):
            load_scenario(p)

    def test_missing_steps_raises(self, tmp_path: Path):
        p = tmp_path / "no_steps.yaml"
        p.write_text("name: x\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_scenario(p)

    def test_top_level_not_dict_raises(self, tmp_path: Path):
        p = tmp_path / "list.yaml"
        p.write_text("- 1\n- 2\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_scenario(p)

    def test_skips_non_dict_steps(self, tmp_path: Path):
        p = tmp_path / "mixed.yaml"
        p.write_text(
            "name: t\nsteps:\n  - 42\n  - {type: wage, lang: zh}\n",
            encoding="utf-8",
        )
        sc = load_scenario(p)
        assert len(sc.steps) == 1


class TestScenarioExpand:
    def test_expand_with_explicit_institutions(self, tmp_path: Path, db: InstitutionDB):
        p = tmp_path / "sc.yaml"
        p.write_text(
            "name: t\nsteps:\n  - type: wage\n    lang: zh\n    institutions:\n      - ILO - 日内瓦总部\n",
            encoding="utf-8",
        )
        sc = load_scenario(p)
        triples = sc.expand(db)
        assert ("wage", "zh", "ILO - 日内瓦总部") in triples

    def test_expand_with_auto_institutions(self, tmp_path: Path, db: InstitutionDB):
        p = tmp_path / "sc.yaml"
        p.write_text(
            "name: t\nsteps:\n  - type: wage\n    lang: en\n",
            encoding="utf-8",
        )
        sc = load_scenario(p)
        triples = sc.expand(db)
        # 自动按 en 推断,至少 1 个机构
        assert len(triples) >= 1
        for t in triples:
            assert t[0] == "wage"
            assert t[1] == "en"

    def test_expand_multiple_steps(self, tmp_path: Path, db: InstitutionDB):
        p = tmp_path / "sc.yaml"
        p.write_text(
            "name: t\nsteps:\n  - type: wage\n    lang: zh\n    institutions: [A]\n  - type: overtime\n    lang: en\n    institutions: [B]\n",
            encoding="utf-8",
        )
        sc = load_scenario(p)
        triples = sc.expand(db)
        assert len(triples) == 2
