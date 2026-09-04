"""v0.3 新增 CLI 命令(archive / preview / validate / completion)的集成测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from wrg.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _make_case(path: Path, **overrides) -> None:
    path.mkdir(parents=True, exist_ok=True)
    data = {
        "company_name": "ACME",
        "company_address": "上海市某路 1 号",
        "worker_name": "李四",
        "worker_phone": "13800138000",
        "worker_email": "lisi@example.com",
        "entry_date": "2024-01-01",
        "job_position": "工程师",
        "contract_status": "已签订",
        "created_at": "2026-09-03T00:00:00",
        "violations": [
            {"type": "wage", "description": "9月欠薪", "amount": "15000"}
        ],
    }
    data.update(overrides)
    (path / "case_info.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (path / "evidence_index.json").write_text("[]", encoding="utf-8")
    ev = path / "evidence"
    ev.mkdir(exist_ok=True)
    (ev / "sample.txt").write_text("证据内容", encoding="utf-8")


class TestArchiveCmd:
    def test_pack_basic(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        result = runner.invoke(
            cli, ["archive", "pack", "--case-dir", str(case)],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / "case.zip").exists()

    def test_pack_with_output(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        out = tmp_path / "my-archive.zip"
        result = runner.invoke(
            cli,
            [
                "archive", "pack",
                "--case-dir", str(case),
                "-o", str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_pack_existing_without_yes_fails(
        self, runner: CliRunner, tmp_path: Path,
    ):
        case = tmp_path / "case"
        _make_case(case)
        out = tmp_path / "existing.zip"
        out.write_bytes(b"")
        result = runner.invoke(
            cli,
            [
                "archive", "pack",
                "--case-dir", str(case),
                "-o", str(out),
            ],
        )
        assert result.exit_code != 0

    def test_pack_with_yes(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        out = tmp_path / "existing.zip"
        out.write_bytes(b"placeholder")
        result = runner.invoke(
            cli,
            [
                "archive", "pack",
                "--case-dir", str(case),
                "-o", str(out),
                "--yes",
            ],
        )
        assert result.exit_code == 0, result.output
        # zip 应覆盖原文件
        import zipfile
        with zipfile.ZipFile(out) as zf:
            assert "case_info.json" in zf.namelist()

    def test_verify_ok(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        zip_path = tmp_path / "case.zip"
        from wrg.archive import ArchiveBuilder
        ArchiveBuilder(case).write_zip(zip_path)
        result = runner.invoke(cli, ["archive", "verify", str(zip_path)])
        assert result.exit_code == 0, result.output
        assert "通过" in result.output or "verified" in result.output.lower()

    def test_verify_missing(self, runner: CliRunner, tmp_path: Path):
        result = runner.invoke(
            cli, ["archive", "verify", str(tmp_path / "nope.zip")],
        )
        assert result.exit_code != 0

    def test_verify_tampered(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        zip_path = tmp_path / "case.zip"
        from wrg.archive import ArchiveBuilder
        ArchiveBuilder(case).write_zip(zip_path)
        # 篡改
        import zipfile
        with zipfile.ZipFile(zip_path, "a") as zf:
            zf.writestr("evidence/sample.txt", "TAMPERED")
        result = runner.invoke(cli, ["archive", "verify", str(zip_path)])
        assert result.exit_code != 0

    def test_extract(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        zip_path = tmp_path / "case.zip"
        from wrg.archive import ArchiveBuilder
        ArchiveBuilder(case).write_zip(zip_path)
        result = runner.invoke(
            cli,
            [
                "archive", "extract", str(zip_path),
                "-o", str(tmp_path / "restored"),
                "--yes",
            ],
        )
        assert result.exit_code == 0, result.output


class TestPreviewCmd:
    def test_preview_zh(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        result = runner.invoke(
            cli, ["preview", "--case-dir", str(case)],
        )
        assert result.exit_code == 0, result.output
        out = case / "reports" / "preview_zh.html"
        assert out.exists()
        html = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "ACME" in html
        assert "李四" in html

    def test_preview_en(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        result = runner.invoke(
            cli, ["preview", "--case-dir", str(case), "--lang", "en"],
        )
        assert result.exit_code == 0, result.output
        out = case / "reports" / "preview_en.html"
        assert out.exists()

    def test_preview_custom_output(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case(case)
        custom = tmp_path / "out.html"
        result = runner.invoke(
            cli,
            [
                "preview", "--case-dir", str(case),
                "-o", str(custom),
            ],
        )
        assert result.exit_code == 0, result.output
        assert custom.exists()


class TestValidateCmd:
    def test_validate_case_ok(self, runner: CliRunner, tmp_path: Path):
        c = tmp_path / "c.json"
        c.write_text(
            json.dumps(
                {
                    "company_name": "A",
                    "company_address": "B",
                    "worker_name": "C",
                    "worker_phone": "1",
                }
            ),
            encoding="utf-8",
        )
        result = runner.invoke(cli, ["validate", "case", str(c)])
        assert result.exit_code == 0, result.output

    def test_validate_case_bad(self, runner: CliRunner, tmp_path: Path):
        c = tmp_path / "c.json"
        c.write_text('{"company_name": "A"}', encoding="utf-8")
        result = runner.invoke(cli, ["validate", "case", str(c)])
        assert result.exit_code != 0
        assert "校验失败" in result.output

    def test_validate_scenario_ok(self, runner: CliRunner, tmp_path: Path):
        s = tmp_path / "s.yaml"
        s.write_text(
            "name: t\nsteps:\n  - type: wage\n    lang: zh\n",
            encoding="utf-8",
        )
        result = runner.invoke(cli, ["validate", "scenario", str(s)])
        assert result.exit_code == 0, result.output

    def test_validate_scenario_bad(self, runner: CliRunner, tmp_path: Path):
        s = tmp_path / "s.yaml"
        s.write_text(
            "name: t\nsteps:\n  - type: bogus\n",
            encoding="utf-8",
        )
        result = runner.invoke(cli, ["validate", "scenario", str(s)])
        assert result.exit_code != 0

    def test_validate_institutions_ok(
        self,
        runner: CliRunner,
        tmp_path: Path,
        project_root: Path,
    ):
        path = project_root / "config" / "institutions.yaml"
        result = runner.invoke(cli, ["validate", "institutions", str(path)])
        assert result.exit_code == 0, result.output


class TestCompletionCmd:
    def test_completion_bash_outputs_script(self, runner: CliRunner):
        result = runner.invoke(cli, ["completion", "bash"])
        assert result.exit_code == 0, result.output
        # bash completion 通常含 _wrg_completion 或 complete -F
        assert "wrg" in result.output or "_wrg" in result.output

    def test_completion_zsh_outputs_script(self, runner: CliRunner):
        result = runner.invoke(cli, ["completion", "zsh"])
        assert result.exit_code == 0, result.output
        # zsh completion 含 #compdef wrg
        assert "wrg" in result.output

    def test_completion_fish_outputs_script(self, runner: CliRunner):
        result = runner.invoke(cli, ["completion", "fish"])
        assert result.exit_code == 0, result.output
        # fish completion 通常以 complete -c wrg 开头
        assert "wrg" in result.output
