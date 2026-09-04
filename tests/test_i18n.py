"""i18n 短文案测试。"""

from __future__ import annotations

from wrg.i18n import t


class TestT:
    def test_zh_default(self):
        assert "证据" in t("evidence.added")

    def test_en(self):
        assert "Evidence" in t("evidence.added", lang="en")

    def test_missing_key_falls_back_to_zh(self):
        assert t("nonexistent.key") == "nonexistent.key"

    def test_unknown_lang_falls_back_to_zh(self):
        # 不存在的语言应回退到中文
        assert t("evidence.added", lang="xx") == t("evidence.added", lang="zh")

    def test_kwargs_substitution(self):
        # 短文案里没有占位符,format 时若无键则原样返回
        msg = t("evidence.added", lang="zh")
        assert "证据" in msg
