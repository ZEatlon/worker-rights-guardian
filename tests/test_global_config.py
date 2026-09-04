"""全局配置单元测试。"""

from __future__ import annotations

import pytest

from wrg.global_config import GlobalConfig, default_global_config_path


class TestGlobalConfig:
    def test_default_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        p = default_global_config_path()
        assert p == tmp_path / ".wrg" / "config.yaml"

    def test_load_missing_returns_empty(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "nope.yaml")
        assert cfg.load() == {}

    def test_save_creates_file(self, tmp_path):
        path = tmp_path / "g.yaml"
        cfg = GlobalConfig(path)
        cfg.set("a", 1)
        cfg.save()
        assert path.exists()

    def test_get_set(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("foo", "bar")
        assert cfg.get("foo") == "bar"
        assert cfg.get("missing", "default") == "default"

    def test_save_and_reload(self, tmp_path):
        path = tmp_path / "g.yaml"
        cfg1 = GlobalConfig(path)
        cfg1.set("k", "v")
        cfg1.save()
        cfg2 = GlobalConfig(path)
        assert cfg2.get("k") == "v"

    def test_corrupt_yaml_returns_empty(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(": : :\n", encoding="utf-8")
        cfg = GlobalConfig(path)
        assert cfg.load() == {}

    def test_defaults_returns_dict(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("defaults", {"a": 1, "b": "x"})
        assert cfg.defaults() == {"a": 1, "b": "x"}

    def test_defaults_returns_empty_when_not_dict(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("defaults", "not a dict")
        assert cfg.defaults() == {}

    def test_default_lang(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("default_lang", "en")
        assert cfg.default_lang() == "en"

    def test_default_lang_invalid_falls_back(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("default_lang", "xyz")
        assert cfg.default_lang() == "zh"

    def test_from_addr(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("from_addr", "x@y.com")
        assert cfg.from_addr() == "x@y.com"

    def test_favorites(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("recipient_pool_favorites", ["ILO", "BBC"])
        assert cfg.favorites() == ["ILO", "BBC"]

    def test_filters_non_string_favorites(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("recipient_pool_favorites", ["ILO", 123, None, "BBC"])
        assert cfg.favorites() == ["ILO", "BBC"]

    def test_merge_into_case_does_not_overwrite(self, tmp_path):
        cfg = GlobalConfig(tmp_path / "g.yaml")
        cfg.set("defaults", {"worker_name": "默认", "company_name": "X"})
        case = {"worker_name": "李四", "worker_phone": "1"}
        out = cfg.merge_into_case(case)
        assert out["worker_name"] == "李四"  # 未覆盖
        assert out["company_name"] == "X"  # 补全
        assert out["worker_phone"] == "1"

    def test_ensure_minimal_creates(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        cfg = GlobalConfig.ensure_minimal()
        assert cfg.path.exists()
        assert cfg.get("default_lang") == "zh"

    def test_atomic_save_via_tmp(self, tmp_path):
        """确保使用 .tmp + rename 原子写入。"""
        path = tmp_path / "atomic.yaml"
        cfg = GlobalConfig(path)
        cfg.set("k", "v1")
        cfg.save()
        # 不应残留 .tmp
        assert not (path.with_suffix(path.suffix + ".tmp")).exists()
