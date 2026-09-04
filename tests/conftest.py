"""pytest 共享 fixtures。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 确保 src/ 在 import 路径中,以便在没有 pip install 时也能跑测试
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def project_root() -> Path:
    return ROOT


@pytest.fixture
def config_dir(project_root: Path) -> Path:
    return project_root / "config"


@pytest.fixture
def template_dir(project_root: Path) -> Path:
    return project_root / "config" / "templates"


@pytest.fixture
def fixtures_dir(project_root: Path) -> Path:
    return project_root / "tests" / "fixtures"


@pytest.fixture
def tmp_case_dir(tmp_path: Path) -> Path:
    """每个测试一个干净的案件目录。"""
    case = tmp_path / "case"
    case.mkdir()
    return case


@pytest.fixture
def sample_text_file(fixtures_dir: Path) -> Path:
    p = fixtures_dir / "sample.txt"
    p.write_text("这是一段示例证据文本,用于测试。", encoding="utf-8")
    return p


@pytest.fixture
def sample_md_file(fixtures_dir: Path) -> Path:
    p = fixtures_dir / "sample.md"
    p.write_text("# 标题\n\n证据 markdown 内容。\n", encoding="utf-8")
    return p


@pytest.fixture
def sample_pdf_file(fixtures_dir: Path) -> Path:
    """极简有效 PDF,1 页空内容。"""
    p = fixtures_dir / "sample.pdf"
    if not p.exists():
        # 最简 PDF:只包含 1 个空白页
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Resources<<>>/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length 44>>stream\n"
            b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET\nendstream\nendobj\n"
            b"xref\n0 5\n"
            b"0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n"
            b"0000000098 00000 n \n0000000177 00000 n \n"
            b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n260\n%%EOF\n"
        )
        p.write_bytes(pdf_bytes)
    return p


@pytest.fixture
def sample_png_file(fixtures_dir: Path) -> Path:
    """生成 1x1 像素的最小 PNG。"""
    p = fixtures_dir / "sample.png"
    if not p.exists():
        # 1x1 透明 PNG
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\rIDATx\x9cc\xfc\xcf\xc0P\x0f\x00\x05\x01\x01\x02"
            b"\xcf\xa0.\xb2"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        p.write_bytes(png_bytes)
    return p


@pytest.fixture
def case_data() -> dict:
    """通用案件数据,可在多个测试间复用。"""
    return {
        "company_name": "测试公司",
        "company_address": "上海市浦东新区某路 1 号",
        "company_legal_person": "张三",
        "company_credit_code": "91310000XXXXXX",
        "company_phone": "021-12345678",
        "worker_name": "李四",
        "worker_phone": "13800138000",
        "worker_email": "lisi@example.com",
        "worker_id": "",
        "entry_date": "2024-01-01",
        "job_position": "工程师",
        "contract_status": "已签订",
        "violations": [
            {
                "type": "拖欠工资",
                "description": "2024 年 9 月工资至今未发放",
                "amount": "15000",
            }
        ],
        "total_claim": "30000",
        "other_requests": "无",
    }
