"""路径工具测试。"""

from __future__ import annotations

from wrg.paths import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_TEMPLATE_DIR,
    PACKAGE_ROOT,
    REPO_ROOT,
    resolve_config_dir,
    resolve_template_dir,
)


class TestPaths:
    def test_package_root_is_path(self):
        assert PACKAGE_ROOT.is_dir()

    def test_default_config_exists(self):
        # 仓库默认应包含 config 目录
        assert DEFAULT_CONFIG_DIR.is_dir()

    def test_default_template_exists(self):
        assert DEFAULT_TEMPLATE_DIR.is_dir()

    def test_repo_root_contains_config(self):
        assert (REPO_ROOT / "config").is_dir()

    def test_resolve_config_none_returns_default(self):
        assert resolve_config_dir(None) == DEFAULT_CONFIG_DIR

    def test_resolve_template_none_returns_default(self):
        assert resolve_template_dir(None) == DEFAULT_TEMPLATE_DIR

    def test_resolve_config_returns_absolute(self, tmp_path):
        out = resolve_config_dir(tmp_path)
        assert out.is_absolute()

    def test_resolve_template_returns_absolute(self, tmp_path):
        out = resolve_template_dir(tmp_path)
        assert out.is_absolute()
