"""命令行界面 (click + rich)。

所有命令以 ``wrg`` 形式注册；``--case-dir`` 全局选项指定案件目录。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from . import __version__
from .evidence import EvidenceManager, classify_extension
from .global_config import GlobalConfig, default_global_config_path
from .institution_db import InstitutionDB
from .i18n import t
from .mail_builder import MailBuilder
from .report_generator import ReportGenerator
from .scenario import load_scenario
from .template_engine import TemplateEngine

console = Console()
console_err = Console(stderr=True)


def _print_version(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if not value:
        return
    click.echo(f"wrg {__version__}")
    ctx.exit()


# =====================================================================
# 共享参数
# =====================================================================


def _case_dir_option(f):
    return click.option(
        "--case-dir",
        "-d",
        default="./cases/default",
        show_default=True,
        type=click.Path(file_okay=False, dir_okay=True),
        help="案件目录路径（包含 case_info.json 与 evidence/）",
    )(f)


def _ensure_case_dir(case_dir: str | Path) -> Path:
    p = Path(case_dir).expanduser().resolve()
    return p


def _load_case_info(case_dir: Path) -> dict[str, Any]:
    """加载案件信息；若不存在抛出异常。"""
    path = case_dir / "case_info.json"
    if not path.exists():
        raise click.ClickException(t("case.case_file_missing"))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"case_info.json 解析失败: {exc}")


def _save_case_info(case_dir: Path, data: dict[str, Any]) -> None:
    path = case_dir / "case_info.json"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


# =====================================================================
# CLI 入口
# =====================================================================


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--version",
    is_flag=True,
    callback=_print_version,
    expose_value=False,
    is_eager=True,
    help="显示版本并退出",
)
def cli() -> None:
    """Worker Rights Guardian — 工人劳动监察举报辅助工具"""


# =====================================================================
# init
# =====================================================================


@cli.command()
@_case_dir_option
@click.option("--force", is_flag=True, help="覆盖已有 case_info.json")
@click.option("--non-interactive", is_flag=True, help="使用空字段初始化（用于 CI）")
@click.option("--use-global-defaults", "use_global", is_flag=True,
              help="用 ~/.wrg/config.yaml 中的 defaults 填充")
def init(case_dir: str, force: bool, non_interactive: bool, use_global: bool) -> None:
    """初始化一个新案件目录。"""
    p = _ensure_case_dir(case_dir)
    p.mkdir(parents=True, exist_ok=True)
    info_file = p / "case_info.json"
    if info_file.exists() and not force:
        raise click.ClickException(
            f"{t('case.existing')}:{info_file}"
        )

    # 全局默认值
    global_cfg = GlobalConfig() if use_global else None
    global_defaults: dict[str, Any] = (
        global_cfg.defaults() if global_cfg else {}
    )

    if non_interactive:
        case_info: dict[str, Any] = {
            "company_name": "",
            "company_address": "",
            "company_legal_person": "",
            "company_credit_code": "",
            "company_phone": "",
            "worker_name": "",
            "worker_phone": "",
            "worker_email": "",
            "worker_id": "",
            "entry_date": "",
            "job_position": "",
            "contract_status": "",
            "created_at": "",
        }
    else:
        console.print(
            Panel.fit(
                "[bold green]Worker Rights Guardian[/bold green]\n"
                "本工具帮助您整理证据、生成劳动监察举报材料。\n"
                "全部数据保存在本地，绝不上传。",
                title="wrg init",
            )
        )
        console.print("\n[bold cyan]第 1 步:填写案件基本信息[/bold cyan]")
        case_info = {
            "company_name": Prompt.ask("被投诉单位名称",
                                       default=global_defaults.get("company_name", "")),
            "company_address": Prompt.ask("单位地址",
                                          default=global_defaults.get("company_address", "")),
            "company_legal_person": Prompt.ask("法定代表人（可选）",
                                                default=global_defaults.get("company_legal_person", "")),
            "company_credit_code": Prompt.ask("统一社会信用代码（可选）",
                                              default=global_defaults.get("company_credit_code", "")),
            "company_phone": Prompt.ask("单位联系电话（可选）",
                                        default=global_defaults.get("company_phone", "")),
            "worker_name": Prompt.ask("您的姓名（或化名）",
                                      default=global_defaults.get("worker_name", "")),
            "worker_phone": Prompt.ask("您的联系电话",
                                       default=global_defaults.get("worker_phone", "")),
            "worker_email": Prompt.ask("电子邮箱（可选）",
                                       default=global_defaults.get("worker_email", "")),
            "worker_id": Prompt.ask("身份证号（可选，留空则隐去）",
                                    default=global_defaults.get("worker_id", "")),
            "entry_date": Prompt.ask("入职时间（如 2023-01-01）",
                                     default=global_defaults.get("entry_date", "")),
            "job_position": Prompt.ask("岗位/职务",
                                       default=global_defaults.get("job_position", "")),
            "contract_status": Prompt.ask(
                "劳动合同签订情况",
                choices=["已签订", "未签订", "口头约定", ""],
                default=global_defaults.get("contract_status", ""),
                show_choices=False,
            ),
            "created_at": "",
        }

    from datetime import datetime

    case_info["created_at"] = datetime.now().isoformat(timespec="seconds")
    _save_case_info(p, case_info)

    console.print(
        f"[green]✓[/green] {t('case.init_done')}:[bold]{info_file}[/bold]"
    )


# =====================================================================
# add-evidence
# =====================================================================


@cli.command("add-evidence")
@_case_dir_option
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--desc", default="", help="证据描述")
@click.option("--tag", "-t", multiple=True, help="标签（可多次指定）")
def add_evidence_cmd(case_dir: str, file_path: str, desc: str, tag: tuple[str, ...]) -> None:
    """添加证据文件到当前案件。"""
    p = _ensure_case_dir(case_dir)
    mgr = EvidenceManager(p)
    try:
        item = mgr.add_evidence(file_path, description=desc, tags=list(tag))
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc))
    console.print(f"[green]✓[/green] {t('evidence.added')}")
    console.print(f"  ID:      {item.id}")
    console.print(f"  名称:    {item.name}")
    console.print(f"  类型:    {item.file_type}")
    console.print(f"  大小:    {item.file_size / 1024:.1f} KB")
    console.print(f"  SHA-256: {item.checksum[:16]}…")


# =====================================================================
# add-text
# =====================================================================


@cli.command("add-text")
@_case_dir_option
@click.option("--name", "-n", required=True, help="证据名称（例如 wechat-record.txt）")
@click.option("--content", "-c", default=None, help="文本内容（默认从 stdin 读取）")
@click.option("--desc", default="", help="证据描述")
@click.option("--tag", "-t", multiple=True, help="标签")
def add_text_cmd(
    case_dir: str,
    name: str,
    content: str | None,
    desc: str,
    tag: tuple[str, ...],
) -> None:
    """添加一段文本作为证据（例如聊天记录）。"""
    p = _ensure_case_dir(case_dir)
    if content is None:
        if sys.stdin.isatty():
            content = ""
        else:
            content = sys.stdin.read()
    if not content:
        raise click.ClickException("文本内容不能为空，可通过 -c 或管道提供")
    mgr = EvidenceManager(p)
    item = mgr.add_text_evidence(content, name, description=desc, tags=list(tag))
    console.print(f"[green]✓[/green] {t('evidence.added')}:{item.id} ({item.name})")


# =====================================================================
# list-evidence
# =====================================================================


@cli.command("list-evidence")
@_case_dir_option
@click.option("--type", "ftype", default=None, help="按文件类型筛选（image/document/audio/video/text）")
@click.option("--tag", default=None, help="按标签筛选")
def list_evidence_cmd(case_dir: str, ftype: str | None, tag: str | None) -> None:
    """列出当前案件下的所有证据。"""
    p = _ensure_case_dir(case_dir)
    mgr = EvidenceManager(p)
    items = mgr.list_evidence(file_type=ftype, tag=tag)
    if not items:
        console.print(f"[yellow]{t('evidence.list_empty')}[/yellow]")
        return
    table = Table(title="证据清单")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("名称", style="green")
    table.add_column("类型", style="blue")
    table.add_column("大小", justify="right")
    table.add_column("描述")
    table.add_column("标签")
    for item in items:
        size = f"{item.file_size / 1024:.1f} KB"
        tags = ", ".join(item.tags) if item.tags else "-"
        table.add_row(
            item.id[:24],
            item.name,
            item.file_type,
            size,
            item.description or "-",
            tags,
        )
    console.print(table)


# =====================================================================
# remove-evidence
# =====================================================================


@cli.command("remove-evidence")
@_case_dir_option
@click.argument("evidence_id")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
def remove_evidence_cmd(case_dir: str, evidence_id: str, yes: bool) -> None:
    """根据 ID 删除证据。"""
    p = _ensure_case_dir(case_dir)
    mgr = EvidenceManager(p)
    item = mgr.get_evidence(evidence_id)
    if item is None:
        raise click.ClickException(f"{t('evidence.not_found')}: {evidence_id}")
    if not yes and not Confirm.ask(f"确认删除 {item.id} ({item.name})?", default=False):
        raise click.Abort()
    ok = mgr.remove_evidence(evidence_id)
    if ok:
        console.print(f"[green]✓[/green] {t('evidence.removed')}")
    else:
        raise click.ClickException(f"{t('evidence.not_found')}: {evidence_id}")


# =====================================================================
# verify
# =====================================================================


@cli.command()
@_case_dir_option
def verify_cmd(case_dir: str) -> None:
    """校验所有证据文件的完整性。"""
    p = _ensure_case_dir(case_dir)
    mgr = EvidenceManager(p)
    results = mgr.verify_integrity()
    if not results:
        console.print("[yellow]暂无证据可校验[/yellow]")
        return
    bad = [eid for eid, ok in results if not ok]
    table = Table(title="校验结果")
    table.add_column("证据 ID", style="cyan")
    table.add_column("状态")
    for eid, ok in results:
        table.add_row(eid, "[green]OK[/green]" if ok else "[red]FAIL[/red]")
    console.print(table)
    if bad:
        raise click.ClickException(f"{len(bad)} 项证据校验失败")


# =====================================================================
# list-institutions
# =====================================================================


@cli.command("list-institutions")
@click.option("--category", "-c", default=None, help="只显示指定类别")
@click.option("--media/--no-media", default=False, help="只显示媒体联系方式")
def list_institutions_cmd(category: str | None, media: bool) -> None:
    """列出所有监督机构和媒体联系方式。"""
    db = InstitutionDB()
    if media:
        pools = db.list_all_media()
        title_prefix = "媒体联系方式"
    elif category:
        pools = {category: db.get_by_category(category)}
        title_prefix = f"类别: {category}"
    else:
        pools = db.list_all()
        title_prefix = "监督机构"

    for cat, items in pools.items():
        if not items:
            continue
        table = Table(title=f"{title_prefix} / {cat}")
        table.add_column("名称", style="green")
        table.add_column("类型", style="blue")
        table.add_column("范围")
        table.add_column("联系方式")
        for inst in items:
            table.add_row(
                inst.name,
                inst.type,
                inst.scope,
                inst.display_contact,
            )
        console.print(table)


# =====================================================================
# search
# =====================================================================


@cli.command()
@click.option("--keyword", "-k", default="", help="关键词")
@click.option("--scope", "-s", default=None, help="按范围筛选")
@click.option("--category", "-c", default=None, help="按类别筛选")
def search(keyword: str, scope: str | None, category: str | None) -> None:
    """搜索监督机构或媒体。"""
    db = InstitutionDB()
    results = db.search(keyword=keyword, scope=scope, category=category)
    if not results:
        console.print(f"[yellow]{t('recipients.empty')}[/yellow]")
        return
    table = Table(title=f"搜索结果: {keyword or '(全部)'}")
    table.add_column("名称", style="green")
    table.add_column("类别", style="cyan")
    table.add_column("范围")
    table.add_column("联系方式")
    for inst in results:
        table.add_row(
            inst.name,
            inst.category,
            inst.scope,
            inst.display_contact,
        )
    console.print(table)


# =====================================================================
# types
# =====================================================================


@cli.command("types")
def types_cmd() -> None:
    """列出支持的申诉类型。"""
    table = Table(title="支持的申诉类型")
    table.add_column("代码", style="cyan")
    table.add_column("中文")
    table.add_column("English")
    types = [
        ("wage", "拖欠工资", "Wage Theft"),
        ("overtime", "违法加班", "Excessive Overtime"),
        ("injury", "工伤 / 职业危害", "Occupational Injury"),
        ("discrim", "歧视 / 性骚扰", "Discrimination / Harassment"),
        ("contract", "违法解雇", "Wrongful Termination"),
        ("social", "拒缴社保", "Social Insurance Evasion"),
        ("child", "使用童工", "Child Labor"),
        ("forced", "强迫劳动", "Forced Labor"),
        ("safety", "安全生产违法", "Workplace Safety"),
        ("union", "阻挠工会 / 集体谈判", "Anti-Union"),
        ("other", "其他", "Other"),
    ]
    for code, zh, en in types:
        table.add_row(code, zh, en)
    console.print(table)


# =====================================================================
# generate
# =====================================================================


@cli.command()
@_case_dir_option
@click.option(
    "--institution",
    "-i",
    "institutions",
    multiple=True,
    help="目标机构名称（可多次指定）",
)
@click.option(
    "--lang",
    "langs",
    default=("zh",),
    type=click.Choice(["zh", "en", "ja", "ko"]),
    multiple=True,
    help="模板语言（可多次指定，默认 zh）",
)
@click.option(
    "--format",
    "fmt",
    default="both",
    type=click.Choice(["eml", "txt", "both"]),
    help="输出格式（.eml 标准邮件，.txt 便于人工预览，both 同时输出）",
)
@click.option(
    "--violation",
    "-V",
    "violations",
    multiple=True,
    help="违法事实（可多次指定），格式: 类型:描述:金额",
)
@click.option("--from-addr", default=None, help="From 头（草稿），默认从全局配置读取")
@click.option("--summary/--no-summary", default=True, help="打印案件摘要")
@click.option("--interactive", "-I", "interactive", is_flag=True,
              help="交互式向导（覆盖命令行参数）")
@click.option("--word/--no-word", default=False,
              help="同时输出 Word 报告（.docx），需要 python-docx")
def generate(
    case_dir: str,
    institutions: tuple[str, ...],
    langs: tuple[str, ...],
    fmt: str,
    violations: tuple[str, ...],
    from_addr: str | None,
    summary: bool,
    interactive: bool,
    word: bool,
) -> None:
    """生成举报邮件草稿（.eml / .txt，可选 Word）。"""
    p = _ensure_case_dir(case_dir)
    case_data = _load_case_info(p)

    # 全局配置
    gcfg = GlobalConfig()
    if from_addr is None:
        from_addr = gcfg.from_addr()
    if not langs:
        langs = (gcfg.default_lang(),)
    langs = tuple(langs)

    # 交互式向导
    if interactive:
        institutions, violations, langs = _wizard_run(case_data, institutions,
                                                     violations, langs, gcfg)

    # 解析 --violation 参数
    parsed_violations: list[dict[str, str]] = []
    for v in violations:
        parts = v.split(":", 2)
        if len(parts) < 2:
            raise click.ClickException(
                f"--violation 格式应为 '类型:描述[:金额]'，实际为:{v}"
            )
        parsed_violations.append(
            {
                "type": parts[0].strip(),
                "description": parts[1].strip(),
                "amount": parts[2].strip() if len(parts) > 2 else "",
            }
        )

    if parsed_violations:
        case_data["violations"] = parsed_violations
    elif not case_data.get("violations"):
        # 交互式询问
        console.print("[cyan]请输入违法事实（留空结束）:[/cyan]")
        while True:
            vtype = Prompt.ask("  类型（如 拖欠工资）", default="")
            if not vtype:
                break
            vdesc = Prompt.ask("  描述", default="")
            vamount = Prompt.ask("  涉及金额（可选）", default="")
            parsed_violations.append(
                {"type": vtype, "description": vdesc, "amount": vamount}
            )
        if parsed_violations:
            case_data["violations"] = parsed_violations

    if not case_data.get("violations"):
        raise click.ClickException("未提供任何违法事实，无法生成邮件")

    # 解析目标机构
    db = InstitutionDB()
    targets: list[Any] = []
    if institutions:
        for name in institutions:
            inst = db.find_by_name(name)
            if not inst:
                # 尝试模糊匹配
                hits = db.search(keyword=name)
                if hits:
                    inst = hits[0]
                    console.print(
                        f"[yellow]未精确匹配 {name}，使用 {inst.name}[/yellow]"
                    )
            if inst is None:
                raise click.ClickException(f"{t('mail.institution_not_found')}: {name}")
            targets.append(inst)
    else:
        # 默认：中国劳动监察类
        hits = db.search(keyword="劳动监察")
        targets = hits[:1] if hits else []
        if not targets:
            console.print("[yellow]未指定目标机构，且默认搜索无结果[/yellow]")

    if not targets:
        raise click.ClickException("没有有效的目标机构")

    mgr = EvidenceManager(p)
    evidence_items = mgr.list_evidence()

    templates = TemplateEngine()
    builder = MailBuilder(templates, db)
    reporter = ReportGenerator(p / "reports")
    mails_dir = p / "mails"
    mails_dir.mkdir(exist_ok=True)

    # 多语言循环
    written_paths: list[str] = []
    for lang in langs:
        for inst in targets:
            mail = builder.build_complaint_mail(
                case_data, inst, evidence_items, language=lang
            )
            safe = _safe_filename(inst.name) or "institution"
            base_path = mails_dir / f"{safe}_{lang}"
            if fmt in ("eml", "both"):
                p_eml = base_path.with_suffix(".eml")
                builder.write_eml(mail, p_eml, from_addr=from_addr)
                written_paths.append(str(p_eml))
            if fmt in ("txt", "both"):
                p_txt = base_path.with_suffix(".txt")
                builder.write_txt(mail, p_txt)
                written_paths.append(str(p_txt))
            console.print(
                f"[green]✓[/green] {t('mail.draft_done')}:{inst.name} ({lang}) → "
                + ", ".join(written_paths[-2:])
            )

    # Word 报告
    if word:
        try:
            from .word_report import WordReportGenerator

            wr = WordReportGenerator(p / "reports")
            for lang in langs:
                path = wr.generate(
                    case_data,
                    [e.to_dict() for e in evidence_items],
                    case_data.get("company_name") or "case",
                    lang=lang,
                )
                console.print(f"[green]✓[/green] {t('mail.word_report')}: {path}")
        except ImportError as exc:
            console_err.print(f"[red]{exc}[/red]")

    # 持久化案件信息（含 violations）
    _save_case_info(p, case_data)

    if summary:
        text = reporter.generate_summary(
            case_data,
            [{"name": inst.name, "email": inst.email} for inst in targets],
            len(evidence_items),
        )
        console.print(Panel(text, title="案件摘要", border_style="green"))


# =====================================================================
# summary
# =====================================================================


@cli.command()
@_case_dir_option
def summary(case_dir: str) -> None:
    """查看当前案件摘要。"""
    p = _ensure_case_dir(case_dir)
    case_data = _load_case_info(p)
    mgr = EvidenceManager(p)
    items = mgr.list_evidence()
    table = Table(title=f"案件摘要 / {p}")
    table.add_column("项目", style="cyan")
    table.add_column("内容", style="green")
    table.add_row("被投诉单位", case_data.get("company_name", "-"))
    table.add_row("单位地址", case_data.get("company_address", "-"))
    table.add_row("投诉人", case_data.get("worker_name", "-"))
    table.add_row("联系电话", case_data.get("worker_phone", "-"))
    table.add_row("电子邮箱", case_data.get("worker_email", "-"))
    table.add_row("入职时间", case_data.get("entry_date", "-"))
    table.add_row("岗位", case_data.get("job_position", "-"))
    table.add_row("证据数量", str(len(items)))
    table.add_row("创建时间", case_data.get("created_at", "-"))
    console.print(table)


def _safe_filename(name: str) -> str:
    keep = "-_.()"
    return "".join(
        ch if (ch.isalnum() or ch in keep) else "_" for ch in name
    )[:80]


# =====================================================================
# 交互式向导（供 generate --interactive 复用）
# =====================================================================


def _wizard_run(
    case_data: dict[str, Any],
    institutions: tuple[str, ...],
    violations: tuple[str, ...],
    langs: tuple[str, ...],
    gcfg: GlobalConfig,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """交互式向导:补全机构 / 违法事实 / 语言。

    跳过已有输入的值。
    """
    console.print(
        Panel.fit(
            "[bold cyan]wrg 向导[/bold cyan]\n按提示输入，直接回车采用默认值。",
            title=t("wizard.welcome"),
        )
    )

    # 1. 机构选择
    if not institutions:
        from rich.prompt import IntPrompt

        db = InstitutionDB()
        n = IntPrompt.ask(
            "要发送给几个机构?", default=2
        )
        picks: list[str] = []
        for i in range(int(n)):
            kw = Prompt.ask(
                f"  机构 #{i + 1} 关键词", default=""
            )
            if not kw:
                continue
            hits = db.search(kw)
            if not hits:
                console.print(f"[yellow]未匹配 {kw}，跳过[/yellow]")
                continue
            if len(hits) == 1:
                picks.append(hits[0].name)
            else:
                # 展示候选
                tbl = Table(title=f"匹配 {kw} 的 {len(hits)} 个机构")
                tbl.add_column("#", style="cyan")
                tbl.add_column("名称", style="green")
                tbl.add_column("联系方式")
                for idx, inst in enumerate(hits[:10], 1):
                    tbl.add_row(str(idx), inst.name, inst.display_contact)
                console.print(tbl)
                choice = IntPrompt.ask("选择", default=1)
                choice = max(1, min(int(choice), len(hits)))
                picks.append(hits[choice - 1].name)
        institutions = tuple(picks)

    # 2. 违法事实
    if not violations and not case_data.get("violations"):
        console.print("[cyan]请输入违法事实（留空结束）:[/cyan]")
        entered: list[str] = []
        while True:
            vtype = Prompt.ask("  类型", default="")
            if not vtype:
                break
            vdesc = Prompt.ask("  描述", default="")
            vamount = Prompt.ask("  涉及金额（可选）", default="")
            entered.append(
                f"{vtype}:{vdesc}:{vamount}" if vamount else f"{vtype}:{vdesc}"
            )
        violations = tuple(entered)

    # 3. 语言
    if len(langs) == 1 and langs[0] == "zh":
        lang = Prompt.ask(
            "邮件语言 (zh/en/ja/ko，逗号分隔多选)",
            default=gcfg.default_lang(),
        )
        langs = tuple(x.strip() for x in lang.split(",") if x.strip()) or ("zh",)

    return institutions, violations, langs


# =====================================================================
# wizard（独立子命令）
# =====================================================================


@cli.command()
@_case_dir_option
def wizard(case_dir: str) -> None:
    """交互式创建案件 + 生成邮件。"""
    p = _ensure_case_dir(case_dir)
    if not (p / "case_info.json").exists():
        console.print("[cyan]案件不存在，先初始化[/cyan]")
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["init", "--case-dir", str(p), "--non-interactive"],
            catch_exceptions=False,
        )
        if result.exit_code != 0:
            raise click.ClickException(f"init 失败:{result.output}")
    case_data = _load_case_info(p)
    gcfg = GlobalConfig()
    institutions, violations, langs = _wizard_run(
        case_data, (), (), (), gcfg
    )
    if not institutions or not violations:
        raise click.ClickException("机构与违法事实不能为空")
    console.print("[cyan]调用 generate 渲染邮件...[/cyan]")
    # 复用 generate 命令逻辑
    from click.testing import CliRunner

    args = [
        "generate",
        "--case-dir", str(p),
        "--format", "both",
    ]
    for inst in institutions:
        args += ["-i", inst]
    for lang in langs:
        args += ["--lang", lang]
    for v in violations:
        args += ["--violation", v]
    result = CliRunner().invoke(cli, args, catch_exceptions=False)
    if result.exit_code != 0:
        raise click.ClickException(result.output or "generate 失败")


# =====================================================================
# play（剧本执行）
# =====================================================================


@cli.command()
@_case_dir_option
@click.argument("scenario_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--from-addr", default=None, help="From 头")
@click.option("--format", "fmt", default="both",
              type=click.Choice(["eml", "txt", "both"]),
              help="输出格式")
def play(case_dir: str, scenario_file: str, from_addr: str | None, fmt: str) -> None:
    """执行剧本，一键生成多封邮件。

    SCENARIO_FILE 是 YAML 剧本文件路径，形如::

        name: 欠薪通用剧本
        description: ...
        steps:
          - type: wage
            lang: zh
            institutions:
              - ILO - 日内瓦总部
              - 中华全国总工会
          - type: wage
            lang: en
            institutions:
              - BBC News
    """
    try:
        scen = load_scenario(scenario_file)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc))
    except ValueError as exc:
        raise click.ClickException(str(exc))

    console.print(
        f"[cyan]{t('scenario.loaded')}:[/cyan] {scen.name} "
        f"({len(scen.steps)} step(s))"
    )

    p = _ensure_case_dir(case_dir)
    case_data = _load_case_info(p)
    db = InstitutionDB()
    mails_dir = p / "mails"
    mails_dir.mkdir(exist_ok=True)
    mgr = EvidenceManager(p)
    evidence_items = mgr.list_evidence()

    templates = TemplateEngine()
    builder = MailBuilder(templates, db)

    if from_addr is None:
        from_addr = GlobalConfig().from_addr()

    rendered = 0
    for vtype, lang, inst_name in scen.expand(db):
        inst = db.find_by_name(inst_name)
        if inst is None:
            console.print(
                f"[yellow]{t('mail.institution_not_found')}: {inst_name}[/yellow]"
            )
            continue
        # 用 case_data 中的现有违法事实；若当前步骤指定 violation_type 则覆盖类型
        cd = dict(case_data)
        if cd.get("violations"):
            new_violations = []
            for v in cd["violations"]:
                v2 = dict(v)
                v2["type"] = vtype
                new_violations.append(v2)
            cd["violations"] = new_violations
        else:
            cd["violations"] = [
                {"type": vtype, "description": "（详见附件证据）", "amount": ""}
            ]
        mail = builder.build_complaint_mail(
            cd, inst, evidence_items, language=lang
        )
        safe = _safe_filename(inst.name) or "institution"
        base = mails_dir / f"{safe}_{lang}"
        if fmt in ("eml", "both"):
            builder.write_eml(mail, base.with_suffix(".eml"), from_addr=from_addr)
        if fmt in ("txt", "both"):
            builder.write_txt(mail, base.with_suffix(".txt"))
        rendered += 1
        console.print(
            f"[green]✓[/green] {t('mail.draft_done')}:{inst.name} ({lang})"
        )

    console.print(f"\n[bold]剧本 {scen.name} 执行完毕，共生成 {rendered} 封邮件[/bold]")


# =====================================================================
# config（全局配置管理）
# =====================================================================


@cli.group()
def config() -> None:
    """管理全局配置 (~/.wrg/config.yaml)。"""


@config.command("show")
def config_show() -> None:
    """显示当前全局配置。"""
    gcfg = GlobalConfig()
    data = gcfg.data
    console.print(
        Panel.fit(
            "\n".join(f"{k}: {v}" for k, v in data.items()) or "(empty)",
            title=t("app.config_path") + ": " + str(gcfg.path),
        )
    )


@config.command("init")
@click.option("--yes", "-y", is_flag=True, help="覆盖已有全局配置")
def config_init(yes: bool) -> None:
    """初始化全局配置文件（含骨架）。"""
    gcfg = GlobalConfig()
    if gcfg.path.exists() and not yes:
        raise click.ClickException(
            f"全局配置已存在:{gcfg.path}。如要覆盖请加 --yes"
        )
    GlobalConfig.ensure_minimal()
    console.print(f"[green]✓[/green] {t('app.config_created')}:[bold]{gcfg.path}[/bold]")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """设置全局配置项。如::

        wrg config set default_lang en
        wrg config set from_addr alice@example.com
    """
    gcfg = GlobalConfig()
    # 智能转换布尔 / 整数
    parsed: Any = value
    if value.lower() in ("true", "false"):
        parsed = value.lower() == "true"
    else:
        try:
            parsed = int(value)
        except ValueError:
            try:
                parsed = float(value)
            except ValueError:
                pass
    gcfg.set(key, parsed)
    gcfg.save()
    console.print(
        f"[green]✓[/green] {t('config.set_ok')}:[bold]{key}[/bold] = {parsed!r}"
    )


@config.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """读取全局配置项。"""
    gcfg = GlobalConfig()
    v = gcfg.get(key, None)
    console.print(f"{key}: {v!r}")


@config.command("path")
def config_path() -> None:
    """显示全局配置文件路径。"""
    console.print(str(default_global_config_path()))


# =====================================================================
# archive（案件打包 / 解包 / 校验 / 加密）
# =====================================================================


@cli.group()
def archive() -> None:
    """案件归档管理:打包成 zip 并附 SHA-256 清单，可选加密。"""


@archive.command("pack")
@_case_dir_option
@click.option(
    "-o",
    "--output",
    default=None,
    help="输出 zip 路径（默认: 案件目录/<案件名>.zip）",
)
@click.option("--level", default=9, type=int, help="压缩级别 0-9，默认 9")
@click.option(
    "--encrypt",
    is_flag=True,
    help="使用 AES-256-GCM 加密输出（需要 cryptography）",
)
@click.option(
    "--password",
    default=None,
    help="加密密码（若 --encrypt;不提供则交互式输入）",
)
@click.option("--yes", "-y", is_flag=True, help="覆盖已有归档")
def archive_pack(
    case_dir: str,
    output: str | None,
    level: int,
    encrypt: bool,
    password: str | None,
    yes: bool,
) -> None:
    """把案件目录打包成 zip 归档（含 manifest.json + manifest.sha256）。"""
    from .archive import (
        ArchiveBuilder,
        ArchiveError,
        encrypt_archive,
    )

    p = _ensure_case_dir(case_dir)
    if output is None:
        output = str(p.with_suffix(".zip"))

    if Path(output).exists() and not yes:
        raise click.ClickException(
            f"归档已存在:{output}。如要覆盖请加 --yes"
        )

    try:
        builder = ArchiveBuilder(
            p,
            tool_version=__version__,
            metadata={"encrypt": encrypt},
        )
        zip_path, manifest = builder.write_zip(
            output, compress_level=max(0, min(level, 9))
        )
    except ArchiveError as exc:
        raise click.ClickException(str(exc))

    console.print(
        f"[green]✓[/green] {t('archive.done')}:[bold]{zip_path}[/bold]"
    )
    console.print(
        f"  文件数: {len(manifest.entries)} · "
        f"大小:   {manifest.total_size / 1024:.1f} KB"
    )

    if encrypt:
        if not password:
            password = click.prompt("加密密码", hide_input=True,
                                    confirmation_prompt=True)
        enc_path = Path(str(zip_path) + ".enc")
        try:
            encrypt_archive(zip_path, enc_path, password)
        except ArchiveError as exc:
            raise click.ClickException(str(exc))
        console.print(
            f"[green]✓[/green] {t('archive.encrypted')}:[bold]{enc_path}[/bold]"
        )


@archive.command("verify")
@click.argument("zip_file", type=click.Path(exists=True, dir_okay=False))
def archive_verify(zip_file: str) -> None:
    """校验 zip 归档的完整性（SHA-256）。"""
    from .archive import verify_archive

    ok, errors = verify_archive(zip_file)
    if ok:
        console.print(
            f"[green]✓[/green] {t('archive.verify_ok')}:[bold]{zip_file}[/bold]"
        )
    else:
        console_err.print(
            f"[red]✗[/red] {t('archive.verify_fail')}:[bold]{zip_file}[/bold]"
        )
        for e in errors:
            console_err.print(f"  - {e}")
        raise click.ClickException("归档校验失败")


@archive.command("extract")
@click.argument("zip_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-o",
    "--output",
    default=None,
    help="解压目标目录（默认: zip 同名目录）",
)
@click.option("--yes", "-y", is_flag=True, help="覆盖已有目录")
@click.option(
    "--password",
    default=None,
    help="解密密码（若归档为加密格式 .enc）",
)
def archive_extract(
    zip_file: str,
    output: str | None,
    yes: bool,
    password: str | None,
) -> None:
    """从 zip（或加密 .enc）归档恢复案件。"""
    from .archive import (
        ArchiveError,
        decrypt_archive,
        extract_archive,
    )

    src = Path(zip_file)
    out = (
        Path(output)
        if output
        else src.with_suffix("").with_suffix("")  # 去掉 .zip 或 .enc
    )
    if out.exists() and any(out.iterdir()) and not yes:
        raise click.ClickException(
            f"目标目录非空:{out}。如要覆盖请加 --yes"
        )

    work_zip = src
    if src.suffix == ".enc":
        if not password:
            password = click.prompt("解密密码", hide_input=True)
        tmp_zip = src.with_suffix("")  # .zip 形式
        try:
            decrypt_archive(src, tmp_zip, password)
        except ArchiveError as exc:
            raise click.ClickException(str(exc))
        work_zip = tmp_zip

    try:
        target = extract_archive(work_zip, out, overwrite=yes)
    except ArchiveError as exc:
        raise click.ClickException(str(exc))
    console.print(
        f"[green]✓[/green] {t('archive.extract_done')}:[bold]{target}[/bold]"
    )


# =====================================================================
# preview（本地 HTML 预览，不联网）
# =====================================================================


@cli.command()
@_case_dir_option
@click.option("--lang", default="zh", type=click.Choice(["zh", "en", "ja", "ko"]),
              help="预览语言（默认 zh）")
@click.option("-o", "--output", default=None, help="输出 HTML 路径")
def preview(case_dir: str, lang: str, output: str | None) -> None:
    """生成本地 HTML 预览（默认打开浏览器）。绝不联网。

    默认输出到 ``<case_dir>/reports/preview_<lang>.html``，可用浏览器
    打开；只读本地文件，不会上传任何内容。
    """
    from .mail_builder import MailBuilder
    from .template_engine import TemplateEngine

    p = _ensure_case_dir(case_dir)
    case_data = _load_case_info(p)
    mgr = EvidenceManager(p)
    evidence = mgr.list_evidence()
    builder = MailBuilder(TemplateEngine())
    # 用一个虚拟机构名渲染 HTML
    from .institution_db import Institution
    inst = Institution(name="本地预览", type="preview", scope="local")
    mail = builder.build_complaint_mail(case_data, inst, evidence,
                                        language=lang, include_html=True)
    if not mail.get("html"):
        raise click.ClickException(f"未找到 {lang} 的 HTML 模板")
    if output is None:
        out = p / "reports" / f"preview_{lang}.html"
    else:
        out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(mail["html"], encoding="utf-8")
    console.print(f"[green]✓[/green] {t('preview.done')}:[bold]{out}[/bold]")


# =====================================================================
# validate（校验）
# =====================================================================


@cli.command()
@click.argument("kind", type=click.Choice(["case", "scenario", "institutions"]))
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
def validate(kind: str, path: str) -> None:
    """校验配置文件格式（JSON Schema 风格）。"""
    from .schema import (
        ValidationError,
        validate_json_file,
        validate_yaml_file,
    )

    try:
        if kind == "case":
            validate_json_file(path, "case_info")
            msg = t("validate.case_ok")
        elif kind == "scenario":
            validate_yaml_file(path, "scenario")
            msg = t("validate.scenario_ok")
        else:
            validate_yaml_file(path, "institutions")
            msg = t("validate.institutions_ok")
    except ValidationError as exc:
        raise click.ClickException(f"校验失败:{exc}")
    console.print(f"[green]✓[/green] {msg}:[bold]{path}[/bold]")


# =====================================================================
# completion（shell 自动补全）
# =====================================================================


@cli.group(hidden=True)
def completion() -> None:
    """生成 shell 自动补全脚本（内部使用）。"""


@completion.command("bash")
@click.option("--name", default="wrg", help="命令名")
def completion_bash(name: str) -> None:
    """输出 bash 补全脚本到 stdout。"""
    from click.shell_completion import BashComplete

    script = BashComplete(cli, {}, name, "_WRG_COMPLETE").source()
    click.echo(script)


@completion.command("zsh")
@click.option("--name", default="wrg", help="命令名")
def completion_zsh(name: str) -> None:
    """输出 zsh 补全脚本到 stdout。"""
    from click.shell_completion import ZshComplete

    script = ZshComplete(cli, {}, name, "_WRG_COMPLETE").source()
    click.echo(script)


@completion.command("fish")
@click.option("--name", default="wrg", help="命令名")
def completion_fish(name: str) -> None:
    """输出 fish 补全脚本到 stdout。"""
    from click.shell_completion import FishComplete

    script = FishComplete(cli, {}, name, "_WRG_COMPLETE").source()
    click.echo(script)


# =====================================================================
# entry point
# =====================================================================


def main() -> None:
    """``wrg`` 命令入口。"""
    try:
        cli(standalone_mode=True)
    except click.ClickException as exc:
        console_err.print(f"[red]错误:[/red] {exc.message}")
        sys.exit(1)
    except click.Abort:
        console_err.print("[yellow]已取消[/yellow]")
        sys.exit(2)
    except KeyboardInterrupt:
        console_err.print("\n[yellow]已中断[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()


__all__ = ["cli", "main"]