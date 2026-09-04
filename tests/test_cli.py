"""CLI 集成测试(使用 click.testing.CliRunner)。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from wrg.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestInit:
    def test_init_non_interactive(self, runner: CliRunner, tmp_path: Path):
        result = runner.invoke(
            cli,
            [
                "init",
                "--case-dir",
                str(tmp_path / "case1"),
                "--non-interactive",
            ],
        )
        assert result.exit_code == 0, result.output
        info_file = tmp_path / "case1" / "case_info.json"
        assert info_file.exists()
        data = json.loads(info_file.read_text("utf-8"))
        assert "company_name" in data
        assert "created_at" in data

    def test_init_force_overwrites(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        case.mkdir()
        (case / "case_info.json").write_text('{"x": 1}', encoding="utf-8")
        result = runner.invoke(
            cli,
            [
                "init",
                "--case-dir",
                str(case),
                "--non-interactive",
                "--force",
            ],
        )
        assert result.exit_code == 0
        data = json.loads((case / "case_info.json").read_text("utf-8"))
        assert "company_name" in data

    def test_init_existing_without_force_fails(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        (case / "case_info.json").write_text('{"x": 1}', encoding="utf-8")
        result = runner.invoke(
            cli,
            ["init", "--case-dir", str(case), "--non-interactive"],
        )
        assert result.exit_code != 0
        assert "已存在" in result.output or "exists" in result.output.lower()


class TestAddEvidence:
    def test_add_text_file(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            [
                "add-evidence",
                "--case-dir",
                str(case),
                str(sample_text_file),
                "--desc",
                "示例",
                "--tag",
                "测试",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "EVD_" in result.output
        assert "示例" not in result.output or "测试" in result.output

    def test_add_missing_file(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), "/nonexistent.txt"],
        )
        assert result.exit_code != 0

    def test_add_unsupported_file(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        bin_file = tmp_path / "weird.bin"
        bin_file.write_bytes(b"\x00\x00\x00")
        result = runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(bin_file)],
        )
        assert result.exit_code != 0
        assert "不支持" in result.output or "unsupported" in result.output.lower()


class TestAddText:
    def test_add_text_inline(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            [
                "add-text",
                "--case-dir",
                str(case),
                "--name",
                "chat.txt",
                "--content",
                "聊天记录内容",
                "--desc",
                "微信记录",
            ],
        )
        assert result.exit_code == 0, result.output
        index = json.loads((case / "evidence_index.json").read_text("utf-8"))
        assert len(index) == 1

    def test_add_text_stdin(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            [
                "add-text",
                "--case-dir",
                str(case),
                "--name",
                "chat.txt",
                "--desc",
                "x",
            ],
            input="管道输入的文本",
        )
        assert result.exit_code == 0, result.output

    def test_add_text_empty_fails(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            [
                "add-text",
                "--case-dir",
                str(case),
                "--name",
                "chat.txt",
            ],
            input="",  # 空内容
        )
        assert result.exit_code != 0


class TestListEvidence:
    def test_empty(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            ["list-evidence", "--case-dir", str(case)],
        )
        assert result.exit_code == 0
        assert "暂无证据" in result.output

    def test_with_data(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
        sample_png_file: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_png_file)],
        )
        result = runner.invoke(
            cli,
            ["list-evidence", "--case-dir", str(case)],
        )
        assert result.exit_code == 0
        # 两个证据都应显示
        assert sample_text_file.name in result.output
        assert sample_png_file.name in result.output


class TestRemoveEvidence:
    def test_remove_yes_flag(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        index = json.loads((case / "evidence_index.json").read_text("utf-8"))
        eid = index[0]["id"]
        result = runner.invoke(
            cli,
            ["remove-evidence", "--case-dir", str(case), eid, "--yes"],
        )
        assert result.exit_code == 0

    def test_remove_missing(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            ["remove-evidence", "--case-dir", str(case), "EVD_NOPE", "--yes"],
        )
        assert result.exit_code != 0


class TestVerify:
    def test_verify_clean(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        result = runner.invoke(
            cli,
            ["verify", "--case-dir", str(case)],
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_verify_tamper(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        index = json.loads((case / "evidence_index.json").read_text("utf-8"))
        file_path = index[0]["file_path"]
        Path(file_path).write_text("篡改", encoding="utf-8")
        result = runner.invoke(
            cli,
            ["verify", "--case-dir", str(case)],
        )
        assert result.exit_code != 0


class TestListInstitutions:
    def test_default(self, runner: CliRunner):
        result = runner.invoke(cli, ["list-institutions"])
        assert result.exit_code == 0
        # 至少应出现"全国劳动保障监察投诉热线"
        assert "12333" in result.output or "全国" in result.output

    def test_media_flag(self, runner: CliRunner):
        result = runner.invoke(cli, ["list-institutions", "--media"])
        assert result.exit_code == 0
        # 媒体池应包含 BBC
        assert "BBC" in result.output or "Reuters" in result.output

    def test_category(self, runner: CliRunner):
        result = runner.invoke(cli, ["list-institutions", "--category", "usa"])
        assert result.exit_code == 0
        assert "USA" in result.output or "DOL" in result.output or "OSHA" in result.output


class TestSearch:
    def test_keyword_match(self, runner: CliRunner):
        result = runner.invoke(cli, ["search", "--keyword", "ILO"])
        assert result.exit_code == 0
        assert "ILO" in result.output

    def test_no_match(self, runner: CliRunner):
        result = runner.invoke(cli, ["search", "--keyword", "完全不存在xyzzy"])
        assert result.exit_code == 0
        assert "未找到" in result.output or "暂无" in result.output


class TestTypes:
    def test_types(self, runner: CliRunner):
        result = runner.invoke(cli, ["types"])
        assert result.exit_code == 0
        assert "拖欠工资" in result.output
        assert "wage" in result.output


class TestGenerate:
    def test_generate_basic(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        # init + add evidence
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        # 写入必要字段
        info_file = case / "case_info.json"
        info = json.loads(info_file.read_text("utf-8"))
        info.update(
            {
                "company_name": "ACME",
                "company_address": "上海市某路 1 号",
                "worker_name": "王五",
                "worker_phone": "13900139000",
                "worker_email": "w@x.com",
                "entry_date": "2024-01-01",
                "job_position": "工程师",
                "contract_status": "已签订",
            }
        )
        info_file.write_text(
            json.dumps(info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "-i",
                "ILO - 日内瓦总部",
                "--violation",
                "拖欠工资:9月工资至今未发:15000",
                "--no-summary",
                "--from-addr",
                "anon@example.com",
            ],
        )
        assert result.exit_code == 0, result.output
        mails_dir = case / "mails"
        assert mails_dir.exists()
        files = list(mails_dir.iterdir())
        assert len(files) > 0
        # 检查 .eml 内容(标题是 base64 编码,需解码)
        import base64 as _base64

        eml = mails_dir / "ILO_-_日内瓦总部_zh.eml"
        if eml.exists():
            raw = eml.read_bytes()
            text = raw.decode("utf-8", errors="replace")
            try:
                b64_subject = text.split("Subject: ", 1)[1].split("\n", 1)[0]
                b64 = b64_subject.split("?b?", 1)[1].split("?=", 1)[0]
                decoded_subject = _base64.b64decode(b64).decode("utf-8")
            except (IndexError, ValueError, _base64.binascii.Error):
                decoded_subject = text
            assert "ACME" in decoded_subject

    def test_generate_invalid_violation_format(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "--violation",
                "只有类型没有描述",
            ],
        )
        assert result.exit_code != 0

    def test_generate_unknown_institution_fails(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        result = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "-i",
                "完全不存在机构",
                "--violation",
                "拖欠工资:测试:0",
            ],
        )
        assert result.exit_code != 0

    def test_generate_no_case_info_fails(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        result = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "--violation",
                "拖欠工资:测试:0",
            ],
        )
        assert result.exit_code != 0


class TestSummary:
    def test_summary(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        case.mkdir()
        runner.invoke(cli, ["init", "--case-dir", str(case), "--non-interactive"])
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        result = runner.invoke(
            cli,
            ["summary", "--case-dir", str(case)],
        )
        assert result.exit_code == 0
        assert "证据数量" in result.output


class TestVersion:
    def test_version(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.3.0" in result.output


class TestMainEntryPoint:
    def test_main_function_exists(self):
        from wrg.cli import main

        assert callable(main)


# ============================================================
# v0.2 新增 CLI 子命令测试
# ============================================================


def _make_case_info(path: Path, **overrides) -> None:
    """写出最小可用 case_info.json。"""
    path.mkdir(parents=True, exist_ok=True)
    data = {
        "company_name": "ACME",
        "company_address": "上海市某路 1 号",
        "company_legal_person": "Alice",
        "company_credit_code": "",
        "company_phone": "",
        "worker_name": "王五",
        "worker_phone": "13900139000",
        "worker_email": "w@x.com",
        "worker_id": "",
        "entry_date": "2024-01-01",
        "job_position": "工程师",
        "contract_status": "已签订",
        "created_at": "2026-09-03T00:00:00",
        "violations": [],
    }
    data.update(overrides)
    (path / "case_info.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class TestGenerateMultiLanguage:
    """验证 generate 命令支持多语言模板同时输出。"""

    def test_generate_en(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        _make_case_info(case)
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        result = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "-i",
                "ILO - 日内瓦总部",
                "--lang",
                "en",
                "-V",
                "Wage Theft:September unpaid:15000",
            ],
        )
        assert result.exit_code == 0, result.output
        mails = list((case / "mails").glob("*.eml"))
        assert len(mails) == 1

    def test_generate_multi_langs(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        _make_case_info(case)
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        result = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "-i",
                "ILO - 日内瓦总部",
                "--lang",
                "zh",
                "--lang",
                "en",
                "-V",
                "wage:9月:15000",
            ],
        )
        assert result.exit_code == 0, result.output
        mails = list((case / "mails").glob("*_zh.eml")) + list(
            (case / "mails").glob("*_en.eml")
        )
        assert len(mails) >= 2

    def test_generate_with_word(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        """--word 标志生成 .docx 报告(若 python-docx 可用)。"""
        try:
            import docx  # noqa: F401
        except ImportError:
            pytest.skip("需要 python-docx")

        case = tmp_path / "case"
        _make_case_info(case)
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        result = runner.invoke(
            cli,
            [
                "generate",
                "--case-dir",
                str(case),
                "-i",
                "ILO - 日内瓦总部",
                "--lang",
                "zh",
                "--word",
                "-V",
                "wage:9月:15000",
            ],
        )
        assert result.exit_code == 0, result.output
        word_files = list((case / "reports").glob("*.docx"))
        assert len(word_files) >= 1


class TestConfigCmd:
    """全局配置 config 子命令测试。"""

    def test_config_path(self, runner: CliRunner):
        result = runner.invoke(cli, ["config", "path"])
        assert result.exit_code == 0
        assert ".wrg" in result.output

    def test_config_set_and_get(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        """config set/get 应能保存与读取。"""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        # set
        r1 = runner.invoke(
            cli, ["config", "set", "default_lang", "en"]
        )
        assert r1.exit_code == 0, r1.output
        # get
        r2 = runner.invoke(cli, ["config", "get", "default_lang"])
        assert r2.exit_code == 0, r2.output
        assert "'en'" in r2.output

    def test_config_set_bool(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        """config set 应自动转换 true/false。"""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        runner.invoke(cli, ["config", "set", "debug", "true"])
        runner.invoke(cli, ["config", "set", "level", "5"])
        r = runner.invoke(cli, ["config", "show"])
        assert r.exit_code == 0

    def test_config_init(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        result = runner.invoke(cli, ["config", "init", "--yes"])
        assert result.exit_code == 0, result.output
        from wrg.global_config import default_global_config_path
        assert default_global_config_path().exists()

    def test_config_init_existing_fails(
        self,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        runner.invoke(cli, ["config", "init", "--yes"])
        # 第二次不加 --yes 应失败
        result = runner.invoke(cli, ["config", "init"])
        assert result.exit_code != 0

    def test_config_get_missing_returns_none(
        self,
        runner: CliRunner,
    ):
        result = runner.invoke(cli, ["config", "get", "绝对不存在的键"])
        assert result.exit_code == 0
        assert "None" in result.output


class TestPlayCmd:
    """剧本执行 play 子命令测试。"""

    def test_play_basic(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
    ):
        case = tmp_path / "case"
        scn = tmp_path / "sc.yaml"
        scn.write_text(
            "name: t\n"
            "description: 测试\n"
            "steps:\n"
            "  - type: wage\n"
            "    lang: zh\n"
            "    institutions:\n"
            "      - ILO - 日内瓦总部\n",
            encoding="utf-8",
        )
        # 案件信息里预设 violation
        _make_case_info(
            case,
            violations=[
                {"type": "wage", "description": "测试欠薪", "amount": "100"}
            ],
        )
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        result = runner.invoke(
            cli,
            ["play", "--case-dir", str(case), str(scn)],
        )
        assert result.exit_code == 0, result.output
        mails = list((case / "mails").glob("*.eml"))
        assert len(mails) >= 1

    def test_play_missing_file(self, runner: CliRunner, tmp_path: Path):
        case = tmp_path / "case"
        _make_case_info(case)
        result = runner.invoke(
            cli,
            ["play", "--case-dir", str(case), str(tmp_path / "nope.yaml")],
        )
        assert result.exit_code != 0

    def test_play_with_sample_scenario(
        self,
        runner: CliRunner,
        tmp_path: Path,
        sample_text_file: Path,
        project_root: Path,
    ):
        """执行项目自带剧本。"""
        case = tmp_path / "case"
        _make_case_info(
            case,
            violations=[
                {"type": "wage", "description": "欠薪", "amount": "1000"}
            ],
        )
        runner.invoke(
            cli,
            ["add-evidence", "--case-dir", str(case), str(sample_text_file)],
        )
        scen_path = project_root / "config" / "scenarios" / "wage_default.yaml"
        result = runner.invoke(
            cli,
            ["play", "--case-dir", str(case), str(scen_path)],
        )
        assert result.exit_code == 0, result.output
        mails = list((case / "mails").glob("*.eml"))
        assert len(mails) >= 1


class TestWizardCmd:
    """独立 wizard 子命令测试。"""

    def test_wizard_requires_inputs(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ):
        """无机构无违法事实时,wizard 应失败(空输入)。"""
        case = tmp_path / "case"
        # 先初始化,确保 case_info.json 存在
        result = runner.invoke(
            cli,
            ["wizard", "--case-dir", str(case)],
            input="\n\n\n",
        )
        # 没有提供任何机构 / 违法事实,应报错
        assert result.exit_code != 0


class TestInitWithGlobalDefaults:
    """init --use-global-defaults 整合全局配置。"""

    def test_init_with_global(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        # 先写入全局 defaults
        from wrg.global_config import GlobalConfig

        g = GlobalConfig(tmp_path / ".wrg" / "config.yaml")
        g.set("defaults", {"worker_name": "默认名"})
        g.save()

        case = tmp_path / "case"
        result = runner.invoke(
            cli,
            [
                "init",
                "--case-dir",
                str(case),
                "--non-interactive",
                "--use-global-defaults",
            ],
        )
        assert result.exit_code == 0, result.output
