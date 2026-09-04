"""项目内部路径解析。"""

from __future__ import annotations

from pathlib import Path

# 当前文件: src/wrg/paths.py
PACKAGE_ROOT: Path = Path(__file__).resolve().parent
SRC_ROOT: Path = PACKAGE_ROOT.parent
# 默认配置（随仓库发布）:仓库根下的 config/ 目录
REPO_ROOT: Path = SRC_ROOT.parent
DEFAULT_CONFIG_DIR: Path = REPO_ROOT / "config"
DEFAULT_TEMPLATE_DIR: Path = DEFAULT_CONFIG_DIR / "templates"


def resolve_config_dir(config_dir: str | Path | None) -> Path:
    """解析用户传入的配置目录，空值时回退到默认 config/。"""
    if config_dir is None:
        return DEFAULT_CONFIG_DIR
    p = Path(config_dir).expanduser().resolve()
    return p


def resolve_template_dir(template_dir: str | Path | None) -> Path:
    """解析模板目录，空值时回退到默认 templates/。"""
    if template_dir is None:
        return DEFAULT_TEMPLATE_DIR
    p = Path(template_dir).expanduser().resolve()
    return p


__all__ = [
    "PACKAGE_ROOT",
    "SRC_ROOT",
    "REPO_ROOT",
    "DEFAULT_CONFIG_DIR",
    "DEFAULT_TEMPLATE_DIR",
    "resolve_config_dir",
    "resolve_template_dir",
]