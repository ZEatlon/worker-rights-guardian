"""邮件构建器。

读取案件数据 + 机构信息 + 证据列表，渲染模板并组装为邮件草稿（主题 +
正文 + 收件人）。**不发送邮件**，只返回字段，由 CLI 落盘成 .eml 或
.txt。
"""

from __future__ import annotations

import re
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from .evidence import EvidenceItem
from .institution_db import Institution
from .template_engine import TemplateEngine

# RFC 5322 简化版
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

LANG_DEFAULT_TEMPLATE = {
    "zh": "zh/labor_complaint.jinja2",
    "en": "en/labor_complaint.jinja2",
    "ja": "ja/labor_complaint.jinja2",
    "ko": "ko/labor_complaint.jinja2",
}

LANG_HTML_TEMPLATE = {
    "zh": "zh/labor_complaint.html.jinja2",
    "en": "en/labor_complaint.html.jinja2",
    "ja": "ja/labor_complaint.html.jinja2",
    "ko": "ko/labor_complaint.html.jinja2",
}

DISCLAIMER_ZH = (
    "\n\n—— 真实性声明 ——\n"
    "以上材料属实，本人愿承担相应法律责任。如有需要可随时提供原件与补充材料。\n"
    "为保护个人隐私，身份证号等敏感信息已做隐去处理。\n"
)

DISCLAIMER_EN = (
    "\n\n-- Declaration of Truthfulness --\n"
    "I declare that the information provided above is true to the best of my "
    "knowledge and I am willing to bear the corresponding legal responsibility. "
    "Original documents can be provided upon request. Sensitive personal data "
    "has been redacted to protect privacy.\n"
)


def validate_email(email: str | None) -> bool:
    """校验邮箱格式（简化版）。"""
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email.strip()))


def _today_str(lang: str = "zh") -> str:
    if lang == "en":
        return datetime.now().strftime("%B %d, %Y")
    if lang == "ja":
        return datetime.now().strftime("%Y年%m月%d日")
    if lang == "ko":
        return datetime.now().strftime("%Y년 %m월 %d일")
    return datetime.now().strftime("%Y年%m月%d日")


class MailBuilder:
    """邮件构建器。

    需要一个 ``TemplateEngine`` 与一个可选的 ``InstitutionDB`` 实例，后者
    主要用于 ``build_batch_mails`` 时按名称查找机构。
    """

    def __init__(
        self,
        template_engine: TemplateEngine,
        institution_db: Any | None = None,
    ) -> None:
        self.template_engine = template_engine
        self.institution_db = institution_db

    # ---------- 单封邮件 ----------

    def build_complaint_mail(
        self,
        case_data: dict[str, Any],
        institution: Institution,
        evidence_items: list[EvidenceItem] | None = None,
        language: str = "zh",
        *,
        include_html: bool = True,
    ) -> dict[str, Any]:
        """构造一封投诉邮件。

        Args:
            include_html: 是否同时渲染 HTML 正文（若模板存在）。

        Returns:
            ``{subject, body, html, to, institution, language, attach_paths}``
        """
        violations = case_data.get("violations") or []
        evidence_dicts = [e.to_dict() for e in (evidence_items or [])]

        context: dict[str, Any] = {
            **case_data,
            "institution_name": institution.name,
            "report_date": _today_str(language),
            "violations": violations,
            "evidence_list": evidence_dicts,
            "today": datetime.now().strftime("%Y-%m-%d"),
        }

        template_path = LANG_DEFAULT_TEMPLATE.get(language, LANG_DEFAULT_TEMPLATE["zh"])
        body: str
        if self.template_engine.has_template(template_path):
            try:
                body = self.template_engine.render(template_path, context)
            except Exception:
                body = self._build_default_body(context, institution, language)
        else:
            body = self._build_default_body(context, institution, language)

        body = self._append_disclaimer(body, language)

        # HTML 正文（可选）
        html_body: str = ""
        if include_html:
            html_path = LANG_HTML_TEMPLATE.get(language)
            if html_path and self.template_engine.has_template(html_path):
                try:
                    html_body = self.template_engine.render(html_path, context)
                except Exception:
                    html_body = ""
            if html_body:
                # HTML 也加上声明段落
                html_body = self._append_html_disclaimer(html_body, language)

        subject = self._generate_subject(case_data, institution, language)
        to_addr = institution.email or institution.contact or institution.url

        attach_paths = [e.file_path for e in (evidence_items or []) if e.file_path]

        return {
            "subject": subject,
            "body": body,
            "html": html_body,
            "to": to_addr,
            "institution": institution.name,
            "language": language,
            "attach_paths": attach_paths,
        }

    # ---------- 批量 ----------

    def build_batch_mails(
        self,
        case_data: dict[str, Any],
        institution_names: list[str],
        evidence_items: list[EvidenceItem] | None = None,
        language: str = "zh",
    ) -> list[dict[str, Any]]:
        """按机构名称批量构造邮件。"""
        if not self.institution_db:
            raise RuntimeError("build_batch_mails 需要 institution_db 才能按名查找")
        mails: list[dict[str, Any]] = []
        for name in institution_names:
            inst = self.institution_db.find_by_name(name)
            if not inst:
                continue
            mails.append(
                self.build_complaint_mail(case_data, inst, evidence_items, language)
            )
        return mails

    # ---------- .eml 生成 ----------

    @staticmethod
    def to_eml(
        mail: dict[str, Any],
        *,
        from_addr: str = "anonymous@worker.local",
        attach_paths: list[str] | None = None,
    ) -> EmailMessage:
        """把邮件字典转成 ``email.message.EmailMessage``。

        注意:此函数 **不发送**，只构造对象。调用方可继续读写或落盘。

        若 ``mail["html"]`` 非空，则同时设置 text/html alternative 部分。
        """
        msg = EmailMessage()
        msg["Subject"] = mail.get("subject", "")
        msg["From"] = from_addr
        msg["To"] = mail.get("to", "")
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") or \
            datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        body = mail.get("body", "")
        html = mail.get("html", "")
        if html:
            msg.set_content(body)
            msg.add_alternative(html, subtype="html")
        else:
            msg.set_content(body)

        for path in attach_paths or mail.get("attach_paths", []) or []:
            p = Path(path)
            if not p.exists():
                continue
            data = p.read_bytes()
            msg.add_attachment(
                data,
                maintype="application",
                subtype="octet-stream",
                filename=p.name,
            )
        return msg

    @staticmethod
    def write_eml(
        mail: dict[str, Any],
        output_path: str | Path,
        *,
        from_addr: str = "anonymous@worker.local",
    ) -> Path:
        """落盘为 .eml 文件，返回写入路径。"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        msg = MailBuilder.to_eml(mail, from_addr=from_addr)
        path.write_bytes(bytes(msg))
        return path

    @staticmethod
    def write_txt(
        mail: dict[str, Any],
        output_path: str | Path,
    ) -> Path:
        """落盘为纯文本草稿。"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            f"收件人: {mail.get('to', '')}\n"
            f"主题: {mail.get('subject', '')}\n"
            f"机构: {mail.get('institution', '')}\n"
            f"语言: {mail.get('language', '')}\n"
            f"附件: {len(mail.get('attach_paths', []))} 项\n"
            + "=" * 60 + "\n"
            + mail.get("body", "")
        )
        path.write_text(content, encoding="utf-8")
        return path

    # ---------- 辅助 ----------

    @staticmethod
    def _generate_subject(
        case_data: dict[str, Any],
        institution: Institution,
        language: str,
    ) -> str:
        company = case_data.get("company_name") or "某单位"
        violations = case_data.get("violations") or []
        first_type = violations[0]["type"] if violations and isinstance(violations[0], dict) else "劳动违法"
        subjects = {
            "zh": f"关于【{company}】{first_type}的投诉举报",
            "en": f"Complaint about {first_type} at {company}",
            "ja": f"【{company}】における{first_type}に関する告発",
            "ko": f"【{company}】 {first_type} 신고",
        }
        return subjects.get(language, subjects["zh"])

    @staticmethod
    def _build_default_body(
        context: dict[str, Any],
        institution: Institution,
        language: str,
    ) -> str:
        cd = context
        if language == "en":
            return (
                f"Dear {institution.name},\n\n"
                f"I am writing to file a complaint regarding {cd.get('company_name', 'a company')} "
                f"for {cd.get('violations', [{}])[0].get('type', 'labor law violations')}.\n\n"
                f"Details:\n"
                f"- Company: {cd.get('company_name', '')}\n"
                f"- Address: {cd.get('company_address', '')}\n"
                f"- Worker: {cd.get('worker_name', '')}\n"
                f"- Phone: {cd.get('worker_phone', '')}\n\n"
                f"Description:\n{cd.get('violations', [{}])[0].get('description', 'See attached evidence.')}\n\n"
                f"Evidence files are attached to this email.\n\n"
                f"Sincerely,\n{cd.get('worker_name', '')}\n{cd.get('report_date', '')}\n"
            )
        # 默认中文
        return (
            f"尊敬的{institution_name_safe(institution)}:\n\n"
            f"我是【{cd.get('company_name', '某单位')}】的员工，现就该公司违反"
            f"劳动法律法规的情况进行投诉举报。\n\n"
            f"一、被投诉单位信息\n"
            f"  单位名称:{cd.get('company_name', '')}\n"
            f"  单位地址:{cd.get('company_address', '')}\n"
            f"  法定代表人:{cd.get('company_legal_person', '未知')}\n\n"
            f"二、投诉人信息\n"
            f"  姓名:{cd.get('worker_name', '')}\n"
            f"  联系电话:{cd.get('worker_phone', '')}\n"
            f"  电子邮箱:{cd.get('worker_email', '无')}\n"
            f"  入职时间:{cd.get('entry_date', '')}\n"
            f"  岗位:{cd.get('job_position', '')}\n\n"
            f"三、违法事实\n"
            f"  {cd.get('violations', [{}])[0].get('description', '详见附件证据')}\n\n"
            f"四、诉求\n"
            f"  1. 依法调查处理，责令被投诉单位纠正违法行为；\n"
            f"  2. 支付拖欠的工资、加班费、经济补偿金等；\n"
            f"  3. 补缴社会保险；\n"
            f"  4. 依法予以行政处罚。\n\n"
            f"相关证据见附件，请查收。\n\n"
            f"投诉人:{cd.get('worker_name', '')}\n"
            f"日期:{cd.get('report_date', '')}\n"
        )

    @staticmethod
    def _append_disclaimer(body: str, language: str) -> str:
        if language == "en":
            return body + DISCLAIMER_EN
        return body + DISCLAIMER_ZH

    @staticmethod
    def _append_html_disclaimer(html_body: str, language: str) -> str:
        """HTML 模板已自带声明段落，此处只兜底（若模板未声明）。"""
        if "Worker Rights Guardian" in html_body or "WRG" in html_body:
            return html_body
        # 兜底声明
        fallback = {
            "en": "<p><small>Generated by WRG. Processed locally. "
                  "I declare the information above is true.</small></p>",
            "zh": "<p><small>由 WRG 生成，全本地处理。以上材料属实。</small></p>",
            "ja": "<p><small>WRG により生成、全ローカル処理。上記内容に虚偽なし。</small></p>",
            "ko": "<p><small>WRG 에서 생성, 완전 로컬 처리. 위 내용은 사실과 다름없음.</small></p>",
        }
        return html_body + fallback.get(language, fallback["zh"])


def institution_name_safe(inst: Institution) -> str:
    """简单的安全转义（去掉控制字符，保留中文/英文/数字与常见标点）。"""
    if not inst:
        return ""
    name = inst.name
    # 去掉换行与控制字符
    return "".join(ch for ch in name if ch == "\t" or ch >= " ")


__all__ = [
    "MailBuilder",
    "validate_email",
    "EMAIL_PATTERN",
]