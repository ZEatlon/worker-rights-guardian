"""端到端冒烟测试。

模拟真实使用流程:init → add-evidence → generate → verify 邮件产出。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from wrg.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_end_to_end_workflow(
    runner: CliRunner,
    tmp_path: Path,
    sample_text_file: Path,
    sample_png_file: Path,
):
    """完整工作流:init → add-evidence × N → generate → verify。"""
    case = tmp_path / "demo-case"
    case.mkdir()

    # 1. init
    r = runner.invoke(
        cli,
        ["init", "--case-dir", str(case), "--non-interactive"],
    )
    assert r.exit_code == 0, r.output

    # 注入完整字段以便生成
    info_file = case / "case_info.json"
    info = json.loads(info_file.read_text("utf-8"))
    info.update(
        {
            "company_name": "示例公司",
            "company_address": "上海市浦东新区某路 100 号",
            "company_legal_person": "张三",
            "company_credit_code": "91310000MA1FL00001",
            "company_phone": "021-12345678",
            "worker_name": "李四",
            "worker_phone": "13800138000",
            "worker_email": "lisi@example.com",
            "worker_id": "",
            "entry_date": "2023-06-01",
            "job_position": "工程师",
            "contract_status": "已签订",
        }
    )
    info_file.write_text(
        json.dumps(info, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2. 添加 3 类证据
    for src, desc, tags in [
        (sample_text_file, "劳动合同关键页", ["合同"]),
        (sample_png_file, "9月工资条", ["工资"]),
        (sample_text_file, "聊天记录", ["沟通"]),
    ]:
        r = runner.invoke(
            cli,
            [
                "add-evidence",
                "--case-dir",
                str(case),
                str(src),
                "--desc",
                desc,
                "--tag",
                tags[0],
            ],
        )
        assert r.exit_code == 0, r.output

    # 3. 验证 evidence_index.json
    index = json.loads((case / "evidence_index.json").read_text("utf-8"))
    assert len(index) == 3

    # 4. 生成 3 封邮件,覆盖不同语种与机构
    r = runner.invoke(
        cli,
        [
            "generate",
            "--case-dir",
            str(case),
            "-i",
            "ILO - 日内瓦总部",
            "-i",
            "北京市劳动保障监察总队",
            "-i",
            "BBC News",
            "--violation",
            "拖欠工资:9 月与 10 月工资至今未发:30000",
            "--violation",
            "违法加班:连续 4 周强制每日加班 4 小时:0",
            "--from-addr",
            "anon@worker.local",
        ],
    )
    assert r.exit_code == 0, r.output

    mails_dir = case / "mails"
    assert mails_dir.exists()
    eml_files = list(mails_dir.glob("*.eml"))
    assert len(eml_files) == 3, f"应生成 3 个 .eml,实际 {len(eml_files)}"

    # 5. 校验邮件内容(.txt 草稿可直接读取,更易校验)
    txt_files = list(mails_dir.glob("*.txt"))
    assert len(txt_files) == 3, f"应生成 3 个 .txt,实际 {len(txt_files)}"

    any_has_company = False
    any_has_worker = False
    any_has_disclaimer = False
    for txt in txt_files:
        text = txt.read_text(encoding="utf-8")
        if "示例公司" in text:
            any_has_company = True
        if "李四" in text:
            any_has_worker = True
        if "真实性声明" in text or "法律责任" in text:
            any_has_disclaimer = True
    assert any_has_company, "邮件正文应包含单位名称"
    assert any_has_worker, "邮件正文应包含投诉人姓名"
    assert any_has_disclaimer, "邮件正文应包含真实性声明"

    # 5b. 额外校验 .eml 使用 email 库能正确解析
    import email
    from email import policy

    for eml in eml_files:
        msg = email.message_from_bytes(
            eml.read_bytes(), policy=policy.default
        )
        assert msg["Subject"], "应有 Subject 头"
        assert msg["To"], "应有 To 头"
        # 至少含一个正文 part
        body = msg.get_body(preferencelist=("plain",))
        assert body is not None, "应包含正文 part"
        body_text = body.get_content()
        assert "示例公司" in body_text or "李四" in body_text, "正文应含案件信息"

    # 6. 校验证据完整性
    r = runner.invoke(cli, ["verify", "--case-dir", str(case)])
    assert r.exit_code == 0, r.output
    assert "OK" in r.output

    # 7. 案件摘要
    r = runner.invoke(cli, ["summary", "--case-dir", str(case)])
    assert r.exit_code == 0
    assert "示例公司" in r.output
    assert "李四" in r.output

    # 8. 列出机构
    r = runner.invoke(cli, ["list-institutions", "--category", "china"])
    assert r.exit_code == 0
    assert "中华全国总工会" in r.output

    # 9. 搜索
    r = runner.invoke(cli, ["search", "--keyword", "劳动监察"])
    assert r.exit_code == 0
    assert "劳动" in r.output

    # 10. 案件违规事实已被持久化
    final_info = json.loads(info_file.read_text("utf-8"))
    assert len(final_info.get("violations", [])) == 2


def test_workflow_offline_guarantee(
    runner: CliRunner,
    tmp_path: Path,
    sample_text_file: Path,
    monkeypatch,
):
    """冒烟测试:整个流程不应触发任何网络 I/O。"""
    import socket

    # 禁用网络,以确保工具本地化
    real_socket = socket.socket

    blocked = []

    def guarded_socket(*args, **kwargs):
        blocked.append((args, kwargs))
        raise RuntimeError("network access blocked in test")

    monkeypatch.setattr(socket, "socket", guarded_socket)
    try:
        case = tmp_path / "offline-case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        info_file = case / "case_info.json"
        info = json.loads(info_file.read_text("utf-8"))
        info.update(
            {
                "company_name": "X",
                "worker_name": "Y",
                "worker_phone": "1",
                "company_address": "Z",
                "entry_date": "2024-01-01",
                "job_position": "P",
                "contract_status": "已签订",
            }
        )
        info_file.write_text(
            json.dumps(info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        r = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "-i",
                "ILO - 日内瓦总部",
                "--violation",
                "拖欠工资:测试:0",
            ],
        )
        assert r.exit_code == 0, r.output
        assert blocked == [], "工具不应发起任何 socket 连接"
    finally:
        monkeypatch.setattr(socket, "socket", real_socket)
