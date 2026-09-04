"""机构数据库单元测试。"""

from __future__ import annotations

import pytest

from wrg.institution_db import Institution, InstitutionDB


class TestInstitution:
    def test_display_contact_email(self):
        i = Institution(name="X", type="email", email="x@y.com")
        assert i.display_contact == "邮箱: x@y.com"

    def test_display_contact_phone(self):
        i = Institution(name="X", type="hotline", contact="12333")
        assert "12333" in i.display_contact

    def test_display_contact_url(self):
        i = Institution(name="X", type="online", url="https://example.com")
        assert "https://example.com" in i.display_contact

    def test_display_contact_empty(self):
        i = Institution(name="X", type="email")
        assert i.display_contact == "暂无联系方式"

    def test_matches(self):
        i = Institution(
            name="ILO Beijing",
            type="email",
            description="国际劳工组织北京局",
            scope="China",
            region="北京",
            email="beijing@ilo.org",
        )
        assert i.matches("ILO")
        assert i.matches("北京")
        assert i.matches("ilo.org")
        assert not i.matches("ACFTU")


class TestInstitutionDB:
    def test_loads_default_config(self):
        db = InstitutionDB()
        # 默认 YAML 中应至少包含这些类别
        for cat in ("china", "international", "usa", "eu", "uk",
                    "japan", "korea", "australia", "new_zealand"):
            assert cat in db.get_categories()
        # 媒体类别
        assert "china_media" in db.get_media_categories()
        assert "international_media" in db.get_media_categories()

    def test_categories_nonempty(self):
        db = InstitutionDB()
        for cat in db.get_categories():
            assert len(db.institutions[cat]) > 0

    def test_search_keyword(self):
        db = InstitutionDB()
        results = db.search("ILO")
        assert any("ILO" in inst.name for inst in results)
        assert all("ILO" in (inst.name + inst.description + inst.scope + inst.region + inst.email).upper() or
                   "ilo" in (inst.name + inst.description + inst.scope + inst.region + inst.email).lower()
                   for inst in results)

    def test_search_scope(self):
        db = InstitutionDB()
        results = db.search("", scope="China")
        assert all(inst.scope.lower() == "china" for inst in results)

    def test_search_category(self):
        db = InstitutionDB()
        results = db.search(keyword="劳动", category="china")
        assert all(inst.category == "china" for inst in results)
        assert len(results) > 0

    def test_search_empty(self):
        db = InstitutionDB()
        results = db.search("")
        assert len(results) > 0  # 默认返回全部

    def test_search_no_match(self):
        db = InstitutionDB()
        results = db.search("完全不可能匹配的关键词xyzzy123456")
        assert results == []

    def test_find_by_name_exact(self):
        db = InstitutionDB()
        inst = db.find_by_name("ILO - 北京局")
        assert inst is not None
        assert inst.email == "beijing@ilo.org"

    def test_find_by_name_missing(self):
        db = InstitutionDB()
        assert db.find_by_name("不存在的机构") is None

    def test_get_by_scope(self):
        db = InstitutionDB()
        results = db.get_by_scope("USA")
        assert all(inst.scope.lower() == "usa" for inst in results)
        assert any("DOL" in inst.name.upper() or "OSHA" in inst.name.upper()
                   or "NLRB" in inst.name.upper() or "EEOC" in inst.name.upper()
                   for inst in results)

    def test_get_by_region(self):
        db = InstitutionDB()
        results = db.get_by_region("北京")
        assert any("北京" in inst.region for inst in results)

    def test_get_by_category_institutions(self):
        db = InstitutionDB()
        results = db.get_by_category("china")
        assert all(inst.category == "china" for inst in results)

    def test_get_by_category_media(self):
        db = InstitutionDB()
        results = db.get_by_category("china_media")
        assert all(inst.category == "china_media" for inst in results)

    def test_stats(self):
        db = InstitutionDB()
        s = db.stats()
        assert s["china"] > 0
        assert s["media.china_media"] > 0

    def test_list_all_and_media(self):
        db = InstitutionDB()
        all_inst = db.list_all()
        all_media = db.list_all_media()
        assert "china" in all_inst
        assert "china_media" in all_media
        # 不应重叠
        inst_names = {i.name for items in all_inst.values() for i in items}
        media_names = {i.name for items in all_media.values() for i in items}
        # 允许重叠(现实里也存在同一实体既是机构又是媒体),
        # 但应各有自己的样本。
        assert len(inst_names) > 0
        assert len(media_names) > 0

    def test_missing_yaml_returns_empty(self, tmp_path):
        # 不存在的 config 目录应返回空数据库而非崩溃
        db = InstitutionDB(config_dir=tmp_path)
        assert db.get_categories() == []
        assert db.get_media_categories() == []


class TestCustomConfig:
    def test_loads_custom_yaml(self, tmp_path):
        custom = tmp_path / "config"
        custom.mkdir()
        (custom / "institutions.yaml").write_text(
            "test:\n  - name: Test Inst\n    type: email\n    email: a@b.com\n",
            encoding="utf-8",
        )
        (custom / "media_contacts.yaml").write_text(
            "test_media:\n  - name: Test Media\n    type: email\n    email: c@d.com\n",
            encoding="utf-8",
        )
        db = InstitutionDB(config_dir=custom)
        assert "test" in db.get_categories()
        assert "test_media" in db.get_media_categories()
        inst = db.find_by_name("Test Inst")
        assert inst is not None
        assert inst.email == "a@b.com"

    def test_invalid_yaml_returns_empty(self, tmp_path):
        custom = tmp_path / "config"
        custom.mkdir()
        (custom / "institutions.yaml").write_text(
            ": : :\ninvalid:\n",
            encoding="utf-8",
        )
        db = InstitutionDB(config_dir=custom)
        # 即使损坏也应优雅降级
        assert db.get_categories() == []
