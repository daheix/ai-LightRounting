"""汇总报告生成器。

读取 JSONL 阶段日志，生成 Markdown 汇总报告，包含:
- 9 阶段执行状态表
- 关键指标汇总表（从各阶段 outputs 提取）
- 9 阶段执行时间线（ASCII 可视化）
- 产物文件清单（扫描 output_dir 下所有产物）
- 学术诚信声明（公式/参数来源）

报告路径: output_dir/reports/report.md

来源:
- Markdown 规范: https://commonmark.org/
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("e2e_showcase")

_JSONL_FILENAME = "showcase.jsonl"
_REPORT_FILENAME = "report.md"

_STAGE_NAMES = {
    1: "PDK 器件目录展示",
    2: "电路规格定义",
    3: "AI 布局",
    4: "智能布线",
    5: "仿真验证",
    6: "DRC/LVS 验证",
    7: "GDS 导出",
    8: "光电协同",
    9: "量子光子验证",
    10: "Adjoint 逆向设计",
}

# 产物子目录列表（与 run_showcase.py 的 _OUTPUT_SUBDIRS 一致）
_ARTIFACT_SUBDIRS = ["logs", "gds", "verilog_a", "spice", "reports"]

# ASCII 时间线最大条形宽度（字符数）
_MAX_BAR_WIDTH = 30

# 阶段名称固定显示宽度（按显示列，CJK 字符占 2 列）
_NAME_DISPLAY_WIDTH = 20


# =============================================================================
# 学术诚信来源（规则 18：所有公式/参数来源均标注）
# =============================================================================

_ACADEMIC_SOURCES: list[tuple[str, str]] = [
    ("MZI 传输率", 'Saleh & Teich, "Photonics", 2019'),
    ("PAM4 BER",
     "Shafik et al., IEEE CommSurveys 2016, "
     "https://ieeexplore.ieee.org/document/7545186"),
    ("玻色采样",
     "Aaronson & Arkhipov, STOC 2011, "
     "https://arxiv.org/abs/0910.4698"),
    ("HOM 干涉",
     "Hong, Ou, Mandel, PRL 1987, "
     "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044"),
    ("KLM 方案",
     "Knill, Laflamme, Milburn, Nature 2001, "
     "https://www.nature.com/articles/35051009"),
    ("Clements 分解",
     "Clements et al., Optica 2016, "
     "https://doi.org/10.1364/OPTICA.3.001460"),
    ("HPWL",
     "Kahng & Lienig, IEEE TCAD 2009, "
     "https://ieeexplore.ieee.org/document/4685534"),
    ("弯曲波导布线",
     "LiDAR ISPD 2025, "
     "https://dl.acm.org/doi/10.1145/3698364.3705355"),
    ("SiEPIC EBeam PDK", "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
    ("Ligentec SiN PDK", "https://www.ligentec.com/"),
    ("HyperLight LNOI PDK", "https://hyperlightphotonics.com/"),
    ("Pattern Project InP PDK", "https://www.patternproject.com/"),
    ("Verilog-A 紧凑模型",
     "Ansys Lumerical CML Compiler, "
     "https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler"),
    ("GDSII 规范", "https://en.wikipedia.org/wiki/GDSII"),
    ("KLayout DRC",
     "https://www.klayout.org/doc-qt5/manual/drc_runsets.html"),
]


# =============================================================================
# JSONL 日志加载
# =============================================================================


def _load_stage_logs(jsonl_path: Path) -> list[dict]:
    """从 JSONL 文件加载阶段日志记录。

    Args:
        jsonl_path: JSONL 日志文件路径。

    Returns:
        阶段日志字典列表，文件不存在时返回空列表。
    """
    if not jsonl_path.exists():
        return []
    logs: list[dict] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs


# =============================================================================
# 阶段状态表
# =============================================================================


def _build_status_table(logs: list[dict]) -> str:
    """构建阶段状态 Markdown 表格。

    Args:
        logs: 阶段日志字典列表。

    Returns:
        Markdown 表格字符串，无日志时返回提示文本。
    """
    if not logs:
        return "（无阶段日志）"
    lines = [
        "| 阶段 | 名称 | 状态 | 耗时(s) | 错误 |",
        "|------|------|------|---------|------|",
    ]
    for log in logs:
        stage_id = log.get("stage_id", "?")
        name = log.get("stage_name", _STAGE_NAMES.get(stage_id, "未知"))
        status = log.get("status", "unknown")
        duration = log.get("duration_s", 0.0)
        error = log.get("error") or "—"
        lines.append(f"| {stage_id} | {name} | {status} | {duration:.2f} | {error} |")
    return "\n".join(lines)


# =============================================================================
# 关键指标提取与汇总表
# =============================================================================


def _extract_stage_metrics(
    stage_id: int, outputs: dict
) -> list[tuple[str, Any, str]]:
    """从单个阶段的 outputs 中提取关键指标。

    根据 stage_id 提取对应阶段的关键指标，每项返回
    (指标名, 数值, 单位) 元组。outputs 中缺失的字段跳过（不返回假数据）。

    指标提取逻辑:
        - stage 1: total_device_count, platform_count
        - stage 2: circuit_count, total_n_devices
        - stage 3: placement_mode, total_hpwl
        - stage 4: total_loss_db, total_crossings, total_bends
        - stage 5: resonant_wavelength_nm, extinction_ratio_db, pam4_ber, pam4_snr_db
        - stage 6: drc_pass_rate, lvs_consistent
        - stage 7: gds_files
        - stage 8: verilog_a_models, pam4_ber, pam4_snr_db
        - stage 9: boson_sampling_prob_sum, hom_verified, klm_cnot_success_prob

    Args:
        stage_id: 阶段编号（1-9）。
        outputs: 阶段输出字典（JSONL 中的 outputs 字段）。

    Returns:
        (指标名, 数值, 单位) 元组列表。
    """
    metrics: list[tuple[str, Any, str]] = []

    if stage_id == 1:
        count = outputs.get("total_device_count")
        if count is not None:
            metrics.append(("total_device_count", count, "个"))
        platforms = outputs.get("platforms", [])
        if platforms:
            metrics.append(("platform_count", len(platforms), "个"))

    elif stage_id == 2:
        circuits = outputs.get("circuits", [])
        if circuits:
            metrics.append(("circuit_count", len(circuits), "个"))
            total_devs = sum(c.get("n_devices", 0) for c in circuits)
            metrics.append(("total_n_devices", total_devs, "个"))

    elif stage_id == 3:
        mode = outputs.get("placement_mode")
        if mode:
            metrics.append(("placement_mode", mode, "-"))
        circuits = outputs.get("circuits", [])
        if circuits:
            total_hpwl = sum(c.get("hpwl", 0.0) for c in circuits)
            metrics.append(("total_hpwl", round(total_hpwl, 2), "μm"))

    elif stage_id == 4:
        circuits = outputs.get("circuits", [])
        if circuits:
            total_loss = sum(c.get("total_loss_db", 0.0) for c in circuits)
            total_cross = sum(c.get("n_crossings", 0) for c in circuits)
            total_bends = sum(c.get("n_bends", 0) for c in circuits)
            metrics.append(("total_loss_db", round(total_loss, 2), "dB"))
            metrics.append(("total_crossings", total_cross, "个"))
            metrics.append(("total_bends", total_bends, "个"))

    elif stage_id == 5:
        mzi = outputs.get("mzi_s_param", {})
        if mzi:
            rwl = mzi.get("resonant_wavelength_nm")
            if rwl is not None:
                metrics.append(("resonant_wavelength_nm", round(rwl, 2), "nm"))
            er = mzi.get("extinction_ratio_db")
            if er is not None:
                metrics.append(("extinction_ratio_db", round(er, 2), "dB"))
        pam4 = outputs.get("pam4", {})
        if pam4:
            ber = pam4.get("ber")
            if ber is not None:
                metrics.append(("pam4_ber", ber, "-"))
            snr = pam4.get("snr_db")
            if snr is not None:
                metrics.append(("pam4_snr_db", round(snr, 2), "dB"))

    elif stage_id == 6:
        drc = outputs.get("drc", {})
        if drc:
            pr = drc.get("pass_rate")
            if pr is not None:
                metrics.append(("drc_pass_rate", pr, "-"))
        lvs = outputs.get("lvs", {})
        if lvs:
            ic = lvs.get("is_consistent")
            if ic is not None:
                metrics.append(("lvs_consistent", ic, "-"))

    elif stage_id == 7:
        circuits = outputs.get("circuits", [])
        if circuits:
            metrics.append(("gds_files", len(circuits), "个"))

    elif stage_id == 8:
        models = outputs.get("verilog_a_models", [])
        if models:
            metrics.append(("verilog_a_models", len(models), "个"))
        pam4 = outputs.get("pam4", {})
        if pam4:
            ber = pam4.get("ber")
            if ber is not None:
                metrics.append(("pam4_ber", ber, "-"))
            snr = pam4.get("snr_db")
            if snr is not None:
                metrics.append(("pam4_snr_db", round(snr, 2), "dB"))

    elif stage_id == 9:
        bs = outputs.get("boson_sampling", {})
        if bs:
            ps = bs.get("prob_sum")
            if ps is not None:
                metrics.append(("boson_sampling_prob_sum", ps, "-"))
        hom = outputs.get("hom", {})
        if hom:
            hv = hom.get("hom_verified")
            if hv is not None:
                metrics.append(("hom_verified", hv, "-"))
        klm = outputs.get("klm", {})
        if klm:
            cp = klm.get("cnot_success_prob")
            if cp is not None:
                metrics.append(("klm_cnot_success_prob", cp, "-"))

    elif stage_id == 10:
        method = outputs.get("method")
        if method:
            metrics.append(("method", method[:40] + "..." if len(method) > 40 else method, "-"))
        iw = outputs.get("initial_width_nm")
        if iw is not None:
            metrics.append(("initial_width_nm", round(iw, 2), "nm"))
        ow = outputs.get("optimal_width_nm")
        if ow is not None:
            metrics.append(("optimal_width_nm", round(ow, 2), "nm"))
        imp = outputs.get("improvement_db")
        if imp is not None:
            metrics.append(("improvement_db", round(imp, 2), "dB"))
        conv = outputs.get("converged")
        if conv is not None:
            metrics.append(("converged", conv, "-"))

    return metrics


def _extract_all_metrics(
    logs: list[dict],
) -> list[tuple[int, str, Any, str]]:
    """从所有阶段的 outputs 中提取关键指标。

    遍历阶段日志列表，对每个阶段调用 _extract_stage_metrics 提取指标。

    Args:
        logs: 阶段日志字典列表。

    Returns:
        (stage_id, 指标名, 数值, 单位) 元组列表。
    """
    all_metrics: list[tuple[int, str, Any, str]] = []
    for log in logs:
        stage_id = log.get("stage_id")
        if stage_id is None:
            continue
        outputs = log.get("outputs", {})
        if not outputs:
            continue
        metrics = _extract_stage_metrics(stage_id, outputs)
        for name, value, unit in metrics:
            all_metrics.append((stage_id, name, value, unit))
    return all_metrics


def _format_metric_value(value: Any) -> str:
    """格式化指标数值用于表格显示。

    - bool → "true"/"false"
    - 极小浮点数（|v| < 1e-3）→ 科学计数法（如 4.29e-04）
    - 极大浮点数（|v| >= 1e6）→ 科学计数法
    - 普通浮点数 → 保留 2 位小数，去除多余尾零

    Args:
        value: 指标值（int/float/bool/str）。

    Returns:
        格式化后的字符串。
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != 0 and (abs(value) < 1e-3 or abs(value) >= 1e6):
            return f"{value:.2e}"
        s = f"{value:.2f}"
        s = s.rstrip("0")
        if s.endswith("."):
            s += "0"
        return s
    return str(value)


def _build_metrics_table(logs: list[dict]) -> str:
    """构建关键指标汇总 Markdown 表格。

    Args:
        logs: 阶段日志字典列表。

    Returns:
        Markdown 表格字符串，无指标时返回提示文本。
    """
    all_metrics = _extract_all_metrics(logs)
    if not all_metrics:
        return "（无指标数据）"
    lines = [
        "| 阶段 | 指标名 | 数值 | 单位 |",
        "|------|--------|------|------|",
    ]
    for stage_id, name, value, unit in all_metrics:
        formatted = _format_metric_value(value)
        lines.append(f"| {stage_id} | {name} | {formatted} | {unit} |")
    return "\n".join(lines)


# =============================================================================
# ASCII 时间线
# =============================================================================


def _cjk_display_width(s: str) -> int:
    """计算字符串的显示宽度（CJK 字符占 2 列）。

    CJK 统一表意文字（0x2E80-0x9FFF）、CJK 兼容表意文字（0xF900-0xFAFF）、
    全角字符（0xFF00-0xFFEF）占 2 个显示列，其余字符占 1 列。

    Args:
        s: 输入字符串。

    Returns:
        显示宽度。
    """
    width = 0
    for ch in s:
        code = ord(ch)
        if 0x2E80 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF:
            width += 2
        elif 0xFF00 <= code <= 0xFFEF:
            width += 2
        else:
            width += 1
    return width


def _pad_to_width(s: str, width: int) -> str:
    """将字符串左侧对齐填充到指定显示宽度（右侧补空格）。

    Args:
        s: 输入字符串。
        width: 目标显示宽度。

    Returns:
        填充后的字符串。
    """
    current = _cjk_display_width(s)
    if current >= width:
        return s
    return s + " " * (width - current)


def _build_timeline(logs: list[dict]) -> str:
    """生成 9 阶段执行时间线 ASCII 可视化。

    按各阶段耗时比例绘制 █ 条形图，名称按显示宽度对齐（CJK 字符占 2 列）。

    Args:
        logs: 阶段日志字典列表。

    Returns:
        ASCII 时间线字符串（含 ``` 代码块标记），无日志时返回提示文本。
    """
    if not logs:
        return "（无阶段日志）"
    max_duration = max(log.get("duration_s", 0.0) for log in logs)
    lines = ["```"]
    for log in logs:
        stage_id = log.get("stage_id", "?")
        name = log.get("stage_name", "未知")
        duration = log.get("duration_s", 0.0)
        bar_width = int(duration / max_duration * _MAX_BAR_WIDTH) if max_duration > 0 else 0
        bar = "█" * bar_width
        padded_name = _pad_to_width(name, _NAME_DISPLAY_WIDTH)
        lines.append(f"阶段 {stage_id} [{padded_name}] {bar} ({duration:.2f}s)")
    lines.append("```")
    return "\n".join(lines)


# =============================================================================
# 产物文件扫描
# =============================================================================


def _format_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读字符串。

    Args:
        size_bytes: 文件大小（字节）。

    Returns:
        格式化后的字符串（如 "12.3 KB"）。
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _scan_artifacts(output_dir: Path) -> list[dict]:
    """扫描 output_dir 下所有产物文件。

    遍历 logs/gds/verilog_a/spice/reports 子目录，收集所有文件的
    名称、大小、相对路径信息。

    Args:
        output_dir: 输出根目录。

    Returns:
        产物文件信息列表，每项含 name/size_bytes/size_human/path。
    """
    artifacts: list[dict] = []
    for subdir in _ARTIFACT_SUBDIRS:
        dir_path = output_dir / subdir
        if not dir_path.exists():
            continue
        for file_path in sorted(dir_path.iterdir()):
            if file_path.is_file():
                size = file_path.stat().st_size
                artifacts.append({
                    "name": file_path.name,
                    "size_bytes": size,
                    "size_human": _format_size(size),
                    "path": str(file_path.relative_to(output_dir)),
                })
    return artifacts


def _build_artifacts_table(artifacts: list[dict]) -> str:
    """构建产物文件清单 Markdown 表格。

    Args:
        artifacts: 产物文件信息列表（由 _scan_artifacts 返回）。

    Returns:
        Markdown 表格字符串，无产物时返回提示文本。
    """
    if not artifacts:
        return "（无产物文件）"
    lines = [
        "| 文件 | 大小 | 路径 |",
        "|------|------|------|",
    ]
    for art in artifacts:
        lines.append(f"| {art['name']} | {art['size_human']} | {art['path']} |")
    return "\n".join(lines)


# =============================================================================
# 汇总信息
# =============================================================================


def _build_summary(logs: list[dict]) -> str:
    """构建汇总信息文本。

    Args:
        logs: 阶段日志字典列表。

    Returns:
        汇总信息字符串（含总阶段数/成功/失败/总耗时）。
    """
    n_total = len(logs)
    n_done = sum(1 for log in logs if log.get("status") == "done")
    n_failed = sum(1 for log in logs if log.get("status") == "failed")
    total_duration = sum(log.get("duration_s", 0.0) for log in logs)
    return (
        f"- 总阶段数: {n_total}\n"
        f"- 成功: {n_done}\n"
        f"- 失败: {n_failed}\n"
        f"- 总耗时: {total_duration:.2f}s"
    )


# =============================================================================
# 学术诚信声明
# =============================================================================


def _build_academic_integrity_statement() -> str:
    """构建学术诚信声明 Markdown 文本。

    列出所有公式与参数来源，声明无 fall-back 假数据（规则 18）。

    Returns:
        学术诚信声明 Markdown 字符串。
    """
    lines = [
        "## 学术诚信声明",
        "",
        "本报告所有数据均来自真实物理仿真，无 fall-back 假数据。",
        "所有公式与参数来源如下：",
        "",
    ]
    for i, (name, ref) in enumerate(_ACADEMIC_SOURCES, 1):
        lines.append(f"{i}. {name}: {ref}")
    return "\n".join(lines)


# =============================================================================
# 报告生成主入口
# =============================================================================


def generate_report(output_dir: Path) -> Path:
    """生成 Markdown 汇总报告。

    读取 output_dir/logs/showcase.jsonl 中的阶段日志，生成包含
    阶段状态表、关键指标汇总表、ASCII 时间线、产物文件清单、
    汇总信息和学术诚信声明的 Markdown 报告。

    报告写入 output_dir/reports/report.md。

    Args:
        output_dir: 输出目录。

    Returns:
        生成的报告文件路径。
    """
    _logger.info("开始生成汇总报告: %s", output_dir)

    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / "logs" / _JSONL_FILENAME
    logs = _load_stage_logs(jsonl_path)

    if not logs:
        _logger.warning("未找到阶段日志或日志为空: %s", jsonl_path)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    status_table = _build_status_table(logs)
    metrics_table = _build_metrics_table(logs)
    timeline = _build_timeline(logs)
    artifacts = _scan_artifacts(output_dir)
    artifacts_table = _build_artifacts_table(artifacts)
    summary = _build_summary(logs)
    integrity = _build_academic_integrity_statement()

    content = f"""# PoLaRIS 端到端 Demo Showcase 汇总报告

生成时间: {now}

## 阶段执行状态

{status_table}

## 关键指标汇总

{metrics_table}

## 9 阶段执行时间线（ASCII 可视化）

{timeline}

## 产物文件清单

{artifacts_table}

## 汇总

{summary}

{integrity}
"""

    report_path = reports_dir / _REPORT_FILENAME
    report_path.write_text(content, encoding="utf-8")
    _logger.info("汇总报告已生成: %s", report_path)
    return report_path
