"""Worker Rights Guardian — 工人劳动监察举报辅助工具。

一个 Python 开源 CLI 工具，帮助劳动者把维权证据整理成规范的举报邮件
草稿，可一键投递到中国监督机构、联合国 / ILO、欧美澳新日韩监督机构与
主流媒体。

设计原则：
    * 全本地处理，绝不联网上报。
    * 仅生成邮件草稿，不自动发送。
    * 收件人 / 模板 / 案件信息均以本地文件管理，可审计可扩展。

典型用法::

    from wrg.evidence import EvidenceManager
    from wrg.institution_db import InstitutionDB
    from wrg.template_engine import TemplateEngine
    from wrg.mail_builder import MailBuilder

详见 ``README.md`` 与 ``docs/USAGE.md``。
"""

from __future__ import annotations

__version__ = "0.3.0"
__all__ = ["__version__"]