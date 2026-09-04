"""国际化的中英双语短文案。

为避免对 gettext 的依赖，MVP 仅维护一个轻量字典。
"""

from __future__ import annotations

from typing import Any

_MESSAGES: dict[str, dict[str, str]] = {
    "zh": {
        # 通用
        "app.banner": "Worker Rights Guardian（工人权益守护）",
        "app.disclaimer": "本工具仅作为辅助整理材料之用，不构成法律建议。",
        "app.config_path": "全局配置文件",
        "app.config_created": "全局配置已创建",
        # 证据
        "evidence.added": "证据已添加",
        "evidence.not_found": "未找到证据",
        "evidence.removed": "证据已删除",
        "evidence.list_empty": "暂无证据",
        "evidence.tampered": "证据文件校验失败，可能被篡改",
        "evidence.verify_ok": "所有证据校验通过",
        # 案件
        "case.init_done": "案件已初始化",
        "case.not_init": "案件尚未初始化，请先运行 wrg init",
        "case.case_file_missing": "未找到案件文件，请先执行 wrg init",
        "case.existing": "案件已存在，如要重新初始化请加 --force",
        # 邮件
        "mail.draft_done": "邮件草稿已生成",
        "mail.institution_not_found": "未找到指定机构",
        "mail.saved_to": "邮件已保存至",
        "mail.word_report": "Word 报告",
        "mail.no_template": "未找到对应语言模板，使用默认正文",
        # 收件人
        "recipients.empty": "暂无匹配机构",
        "recipients.pool": "收件人池",
        "recipients.search_done": "搜索完成",
        # 配置
        "config.yaml_missing": "配置文件不存在",
        "config.yaml_corrupt": "配置文件损坏，已回退到空配置",
        "config.set_ok": "配置已更新",
        # 模板
        "template.not_found": "模板不存在",
        "template.rendered": "模板渲染完成",
        # 剧本
        "scenario.not_found": "剧本文件不存在",
        "scenario.loaded": "剧本已加载",
        "scenario.invalid": "剧本文件格式无效",
        # 流程
        "wizard.welcome": "欢迎使用交互式向导",
        "wizard.violation_count": "已记录 {n} 条违法事实",
        "exit.success": "完成",
        "exit.error": "出错了",
        "footer.disclaimer": "本工具仅作为辅助整理材料之用，不构成法律建议。",
        # 归档（v0.3）
        "archive.done": "归档已生成",
        "archive.verify_ok": "归档完整性校验通过",
        "archive.verify_fail": "归档完整性校验失败",
        "archive.extract_done": "归档已解压",
        "archive.encrypted": "已加密输出",
        "archive.decrypted": "已解密输出",
        "archive.need_cryptography": "需要 cryptography 包",
        # HTML 预览（v0.3）
        "preview.done": "HTML 预览已生成",
        # 完成性（v0.3）
        "validate.case_ok": "案件信息格式有效",
        "validate.scenario_ok": "剧本格式有效",
        "validate.institutions_ok": "机构池格式有效",
    },
    "en": {
        # General
        "app.banner": "Worker Rights Guardian",
        "app.disclaimer": (
            "This tool assists with material preparation only and does not "
            "constitute legal advice."
        ),
        "app.config_path": "Global config file",
        "app.config_created": "Global config created",
        # Evidence
        "evidence.added": "Evidence added",
        "evidence.not_found": "Evidence not found",
        "evidence.removed": "Evidence removed",
        "evidence.list_empty": "No evidence",
        "evidence.tampered": "Evidence file verification failed (possible tampering)",
        "evidence.verify_ok": "All evidence passed verification",
        # Case
        "case.init_done": "Case initialized",
        "case.not_init": "Case not initialized. Run `wrg init` first.",
        "case.case_file_missing": "Case file not found. Run `wrg init` first.",
        "case.existing": "Case already exists. Use --force to reinitialize.",
        # Mail
        "mail.draft_done": "Mail draft generated",
        "mail.institution_not_found": "Institution not found",
        "mail.saved_to": "Mail saved to",
        "mail.word_report": "Word report",
        "mail.no_template": "No template for this language; using default body",
        # Recipients
        "recipients.empty": "No matching institutions",
        "recipients.pool": "Recipient pool",
        "recipients.search_done": "Search completed",
        # Config
        "config.yaml_missing": "Config file not found",
        "config.yaml_corrupt": "Config file is corrupt; falling back to empty config",
        "config.set_ok": "Config updated",
        # Template
        "template.not_found": "Template not found",
        "template.rendered": "Template rendered",
        # Scenario
        "scenario.not_found": "Scenario file not found",
        "scenario.loaded": "Scenario loaded",
        "scenario.invalid": "Invalid scenario file format",
        # Workflow
        "wizard.welcome": "Welcome to the interactive wizard",
        "wizard.violation_count": "Recorded {n} violation(s)",
        "exit.success": "Done",
        "exit.error": "Error",
        "footer.disclaimer": (
            "This tool assists with material preparation only and does not "
            "constitute legal advice."
        ),
        # Archive (v0.3)
        "archive.done": "Archive created",
        "archive.verify_ok": "Archive integrity verified",
        "archive.verify_fail": "Archive integrity check failed",
        "archive.extract_done": "Archive extracted",
        "archive.encrypted": "Encrypted output written",
        "archive.decrypted": "Decrypted output written",
        "archive.need_cryptography": "cryptography package is required",
        # HTML preview (v0.3)
        "preview.done": "HTML preview generated",
        # Validation (v0.3)
        "validate.case_ok": "Case info is valid",
        "validate.scenario_ok": "Scenario is valid",
        "validate.institutions_ok": "Institution pool is valid",
    },
}


def t(key: str, lang: str = "zh", **kwargs: Any) -> str:
    """获取翻译短文案，缺失时回退到中文，再缺失时回退到 key 本身。"""
    msg = _MESSAGES.get(lang, _MESSAGES["zh"]).get(key)
    if msg is None:
        msg = _MESSAGES["zh"].get(key, key)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except (KeyError, IndexError):
            return msg
    return msg


__all__ = ["t"]