"""邮件构建器单元测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wrg.evidence import EvidenceItem
from wrg.institution_db import Institution
from wrg.mail_builder import MailBuilder, validate_email
from wrg.template_engine import TemplateEngine


@pytest.fixture
def template_engine(template_dir: Path) -> TemplateEngine:
    return TemplateEngine(template_dir=template_dir)


@pytest.fixture
def institution() -> Institution:
    return Institution(
        name="ILO - 日内瓦总部",
        type="email",
        scope="global",
        region="瑞士日内瓦",
        description="联合国负责工作世界的专门机构",
        email="ilo@ilo.org",
        category="international",
    )


@pytest.fixture
def evidence_items(tmp_case_dir: Path) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            id="EVD_001",
            name="contract.pdf",
            file_path="ignored",
            file_type="document",
            file_size=1024,
            checksum="abc",
            description="劳动合同",
        ),
        EvidenceItem(
            id="EVD_002",
            name="wage.txt",
            file_path="ignored",
            file_type="text",
            file_size=512,
            checksum="def",
            description="9月工资条",
            tags=["工资"],
        ),
    ]


class TestValidateEmail:
    def test_valid(self):
        assert validate_email("a@b.com")
        assert validate_email("john.doe+tag@sub.example.co.uk")

    def test_invalid(self):
        assert not validate_email("")
        assert not validate_email(None)
        assert not validate_email("not-an-email")
        assert not validate_email("a@b")
        assert not validate_email("@b.com")
        assert not validate_email("a@.com")
        # 含控制字符
        assert not validate_email("a\n@b.com")


class TestBuildComplaintMail:
    def test_subject_zh(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="zh"
        )
        assert "测试公司" in mail["subject"]
        assert mail["to"] == "ilo@ilo.org"
        assert mail["institution"] == institution.name
        assert mail["language"] == "zh"
        assert len(mail["attach_paths"]) == 2

    def test_subject_en(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="en"
        )
        assert "Complaint" in mail["subject"]
        assert mail["language"] == "en"

    def test_subject_ja(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="ja"
        )
        assert "告発" in mail["subject"]
        assert mail["language"] == "ja"

    def test_subject_ko(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="ko"
        )
        assert "신고" in mail["subject"]
        assert mail["language"] == "ko"

    def test_body_includes_company_and_worker(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="zh"
        )
        assert "测试公司" in mail["body"]
        assert "李四" in mail["body"]
        assert "拖欠工资" in mail["body"]
        # 真实性声明
        assert "真实性声明" in mail["body"] or "法律责任" in mail["body"]

    def test_body_en_disclaimer(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="en"
        )
        assert "Declaration of Truthfulness" in mail["body"]
        assert "true to the best of my knowledge" in mail["body"]

    def test_uses_default_body_when_template_missing(
        self,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        # 无模板目录 → 走内置默认正文
        from pathlib import Path
        eng = TemplateEngine(template_dir=Path("/nonexistent-but-tolerated"))
        builder = MailBuilder(eng)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="zh"
        )
        assert "测试公司" in mail["body"]
        assert "投诉人" in mail["body"]

    def test_institution_without_email_falls_back(
        self,
        template_engine: TemplateEngine,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        inst = Institution(name="Hotline", type="hotline", contact="12333")
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, inst, evidence_items, language="zh"
        )
        assert mail["to"] == "12333"

    def test_empty_violations_still_renders(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
    ):
        cd = {
            "company_name": "X",
            "worker_name": "Y",
            "worker_phone": "1",
            "violations": [],
        }
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(cd, institution, evidence_items)
        assert "X" in mail["subject"]
        assert "违法" in mail["subject"] or "X" in mail["subject"]


class TestBuildBatchMails:
    def test_batch_with_db_lookup(
        self,
        template_engine: TemplateEngine,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        from wrg.institution_db import InstitutionDB

        db = InstitutionDB()
        builder = MailBuilder(template_engine, db)
        mails = builder.build_batch_mails(
            case_data,
            ["ILO - 日内瓦总部", "ILO - 北京局"],
            evidence_items,
            language="en",
        )
        assert len(mails) == 2
        assert all(m["language"] == "en" for m in mails)

    def test_batch_unknown_institution_skipped(
        self,
        template_engine: TemplateEngine,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        from wrg.institution_db import InstitutionDB

        db = InstitutionDB()
        builder = MailBuilder(template_engine, db)
        mails = builder.build_batch_mails(
            case_data,
            ["不存在的机构"],
            evidence_items,
        )
        assert mails == []

    def test_batch_requires_db(self, template_engine: TemplateEngine, case_data: dict):
        builder = MailBuilder(template_engine, institution_db=None)
        with pytest.raises(RuntimeError):
            builder.build_batch_mails(case_data, ["X"])


class TestEmlGeneration:
    def test_to_eml_basic(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="zh"
        )
        msg = builder.to_eml(mail, from_addr="a@b.com")
        assert msg["Subject"]
        assert msg["From"] == "a@b.com"
        assert msg["To"] == mail["to"]
        # multipart/alternative: text + html,任一部分都不为空
        if msg.is_multipart():
            parts = list(msg.walk())
            texts = [p.get_content() for p in parts
                     if p.get_content_type() == "text/plain"]
            assert texts and texts[0].strip()
        else:
            assert msg.get_content()

    def test_write_eml(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
        tmp_path: Path,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="zh"
        )
        out = tmp_path / "draft.eml"
        builder.write_eml(mail, out, from_addr="a@b.com")
        assert out.exists()
        raw = out.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        assert "Subject:" in text
        # multipart 邮件应包含 text/plain 与 text/html 两个部分
        from email import policy
        from email.parser import BytesParser
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        if parsed.is_multipart():
            parts = [str(p.get_content()) for p in parsed.walk()
                     if not p.is_multipart()]
            joined = "\n".join(p for p in parts if p)
        else:
            joined = str(parsed.get_content())
        assert "测试公司" in joined
        assert "李四" in joined

    def test_write_txt(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        evidence_items: list[EvidenceItem],
        case_data: dict,
        tmp_path: Path,
    ):
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, evidence_items, language="zh"
        )
        out = tmp_path / "draft.txt"
        builder.write_txt(mail, out)
        text = out.read_text("utf-8")
        assert "收件人:" in text
        assert "主题:" in text
        assert "测试公司" in text
        assert "附件: 2 项" in text

    def test_eml_with_attachments(
        self,
        template_engine: TemplateEngine,
        institution: Institution,
        tmp_path: Path,
        case_data: dict,
    ):
        attach1 = tmp_path / "a.txt"
        attach1.write_text("hello", encoding="utf-8")
        ev = EvidenceItem(
            id="EVD_x",
            name="a.txt",
            file_path=str(attach1),
            file_type="text",
            file_size=5,
            checksum="x",
        )
        builder = MailBuilder(template_engine)
        mail = builder.build_complaint_mail(
            case_data, institution, [ev], language="zh"
        )
        msg = builder.to_eml(mail, from_addr="a@b.com")
        # 至少应包含 2 个 part: text + attachment
        assert msg.is_multipart()
