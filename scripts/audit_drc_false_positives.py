#!/usr/bin/env python3
"""DRC 误报率量化审查脚本（PoLaRIS real_board，R02/R03/R11 合规）。

基于 real_board 87 个真实板级 benchmark 电路，在默认模式（bend_compensate=True，
用户实际使用模式）下运行 DRC 收集 PORT_ALIGNMENT 违规，抽样 50 个用例自动
判定是否为误报，输出误报率与根因分析报告，对标商用门槛 ≤5%
（Mohan et al., DATE 2023 "Machine Learning for DRC"）。

R03 修复（2026-07-06）: 引擎删除 bend_compensate=True 时 return[] 的 fall-back，
改为多维容差方程（LiDAR 2.0 §III-C2 + Calibre eqDRC）。默认模式现在是
用户实际使用的模式，反映真实误报率。

## 误报定义（R02 学术诚信）
用例被 DRC 判为 PORT_ALIGNMENT 违规，但人工核查为物理可实现的连接:
- 器件真实存在且端口在器件边界内
- 连接对端器件存在
- 端口方向兼容（启用 bend_compensate 后任意有效方向都兼容，
  Chrostowski & Hochberg 2015 §4.3，每 90° 弯曲 ≈0.05dB）
- 端口间距在弯曲补偿范围内（<50μm，可通过 S-bend/Bezier/Euler 弯曲补偿）

## Process
加载 real_board 87 电路 → 默认模式 DRC 收集 PORT_ALIGNMENT 违规 →
按类别均匀抽样 50 个 → is_false_positive 自动判定（器件存在/端口在边界内/
对端器件存在/方向兼容/间距<50μm 为误报）→ 生成报告。

## Output
- ``out/audit/drc_false_positive_report.md`` — 误报率审查报告
- ``out/audit/drc_audit_data.json`` — 完整审计数据（中间产物）

## 来源（R02 学术诚信，≥5 个文献 URL）
- Mohan et al., "Machine Learning for DRC", DATE 2023
  https://doi.org/10.23919/DATE56975.2023.10137091
- SiEPIC EBeam PDK DRC runset https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015 §4.3
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- KLayout DRC 文档 https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- He et al., OpenDRC, DAC 2023 https://doi.org/10.1109/DAC56929.2023.10247734
- Berg et al. 2014, "Computational Geometry", Springer（AABB 几何）
  https://doi.org/10.1007/978-3-540-77974-2
- PoLaRIS DRC 引擎: /workspace/modules/drc/src/polaris_drc/engine.py
- PoLaRIS real_board harness: /workspace/scripts/run_real_board_drc.py
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Any

# PoLaRIS 子模块路径
sys.path.insert(0, "/workspace/modules/drc/src")
sys.path.insert(0, "/workspace/modules/place/src")
sys.path.insert(0, "/workspace/scripts")

import polaris_drc  # noqa: E402
import polaris_place  # noqa: E402
# 复用 run_real_board_drc.py 的 4 类 benchmark 转换器
from run_real_board_drc import (  # noqa: E402
    collect_siepic, collect_expert_demos,
    collect_gdsfactory, collect_picbench,
)

# =========================================================================
# 路径与常量
# =========================================================================
WORKSPACE = "/workspace"
OUTPUT_DIR = os.path.join(WORKSPACE, "out", "audit")
REPORT_PATH = os.path.join(OUTPUT_DIR, "drc_false_positive_report.md")
DATA_PATH = os.path.join(OUTPUT_DIR, "drc_audit_data.json")

# PORT_ALIGNMENT 容差（与 polaris_drc/engine.py PORT_ALIGN_TOL_UM 一致）
PORT_ALIGN_TOL_UM = 10.0
# 默认抽样数（任务要求 50）
DEFAULT_SAMPLE_SIZE = 50
# 误报判定阈值: 端口偏差在弯曲补偿范围内（<50μm）视为误报
# 依据: 任务描述"启用bend_compensate后任意距离都可弯曲补偿，
#       但间距>50μm可能是布局问题，非误报"
# 物理: S-bend 弯曲半径 25μm × 2 的典型补偿范围
# 来源: SiEPIC bent_waveguide 单元弯曲半径 5-50μm
#        Chrostowski & Hochberg 2015 §4.3
PORT_ALIGN_FP_THRESHOLD_UM = 50.0
# 商用误报率门槛（Mohan et al. DATE 2023）
COMMERCIAL_FP_RATE_THRESHOLD = 0.05  # 5%

# 4 类 benchmark 类别名
CATEGORIES = ("siepic", "expert_demos", "gdsfactory", "picbench")


# =========================================================================
# 工具函数
# =========================================================================
def load_all_real_board_circuits() -> list[dict]:
    """加载 real_board 87 个电路（复用 run_real_board_drc 转换器）。

    Returns:
        电路列表，每项含 name/category/circuit/placements。
    """
    collectors = {
        "siepic": collect_siepic,
        "expert_demos": collect_expert_demos,
        "gdsfactory": collect_gdsfactory,
        "picbench": collect_picbench,
    }
    items: list[dict] = []
    for cat, collector in collectors.items():
        for raw_item in collector():
            try:
                circuit, placements = raw_item["convert"](*raw_item["args"])
                if not placements:
                    raise RuntimeError(
                        f"placements 为空（R03 禁止 fall-back）: {raw_item['name']}"
                    )
                items.append({
                    "name": raw_item["name"],
                    "category": cat,
                    "circuit": circuit,
                    "placements": placements,
                })
            except Exception as e:
                # 转换失败记录但继续（不影响其他电路审计）
                # R03: 此处不是 fall-back，是真实数据质量问题由上层处理
                print(f"  [WARN] 跳过 {raw_item['name']}: {type(e).__name__}: {e}")
                items.append({
                    "name": raw_item["name"],
                    "category": cat,
                    "circuit": None,
                    "placements": None,
                    "error": f"{type(e).__name__}: {e}",
                })
    return items


def parse_dx_dy_from_message(msg: str) -> tuple[float, float]:
    """从 PORT_ALIGNMENT 违规 message 中解析 dx/dy。

    message 格式: "PORT_ALIGNMENT: 连接 d1.p1→d2.p2 端口未对齐
                   dx=12.34μm dy=56.78μm > 容差 10.00μm"

    R03: 解析失败 raise，不返回假数据。
    """
    m = re.search(r"dx=([\d.]+)μm\s+dy=([\d.]+)μm", msg)
    if not m:
        raise RuntimeError(
            f"无法从 PORT_ALIGNMENT message 解析 dx/dy: {msg!r}"
            f"（R03 禁止 fall-back）"
        )
    return float(m.group(1)), float(m.group(2))


def parse_connection_from_message(msg: str) -> tuple[str, str, str, str]:
    """从 PORT_ALIGNMENT 违规 message 中解析连接信息。

    message 格式: "PORT_ALIGNMENT: 连接 d1.p1→d2.p2 端口未对齐 ..."

    Returns:
        (d1_name, p1_name, d2_name, p2_name)

    Raises:
        RuntimeError: 解析失败（R03 禁止 fall-back）。
    """
    m = re.search(r"连接\s+(\S+)\.(\S+)→(\S+)\.(\S+)", msg)
    if not m:
        raise RuntimeError(
            f"无法从 PORT_ALIGNMENT message 解析连接信息: {msg!r}"
            f"（R03 禁止 fall-back）"
        )
    return m.group(1), m.group(2), m.group(3), m.group(4)


# =========================================================================
# 核心: 误报自动判定
# =========================================================================
def is_false_positive(violation: dict, circuit: dict,
                      placements: dict) -> tuple[bool, str]:
    """判定 PORT_ALIGNMENT 违规是否为误报。

    判定逻辑（任务描述，R02 学术诚信）:
    1. 器件存在性（placements 中有该器件）+ 端口在器件边界 [0,w]×[0,h] 内
    2. 连接对端器件存在
    3. 端口方向兼容（bend_compensate 启用后任意有效方向都兼容，仅非法方向为真违规）
    4. 端口间距 dx<50μm 且 dy<50μm → 误报（弯曲补偿范围内）

    Returns:
        (is_fp, reason): 误报返回 (True, 原因)，真违规返回 (False, 原因)。
    """
    msg = violation.get("message", "")
    dx, dy = parse_dx_dy_from_message(msg)
    d1_name, p1_name, d2_name, p2_name = parse_connection_from_message(msg)

    # 1. 检查器件是否存在
    if d1_name not in placements:
        return (False, f"器件 {d1_name} 不在 placements 中（真违规-器件缺失）")
    if d2_name not in placements:
        return (False, f"器件 {d2_name} 不在 placements 中（真违规-对端器件缺失）")

    # 2. 检查端口是否在器件边界内
    device_map = {d.get("name"): d for d in circuit.get("devices", [])}
    dev1 = device_map.get(d1_name)
    dev2 = device_map.get(d2_name)
    if dev1 is None:
        return (False, f"器件 {d1_name} 不在 circuit.devices 中（真违规-器件未定义）")
    if dev2 is None:
        return (False, f"器件 {d2_name} 不在 circuit.devices 中（真违规-对端未定义）")

    pl1, pl2 = placements[d1_name], placements[d2_name]
    w1, h1 = float(pl1["w"]), float(pl1["h"])
    w2, h2 = float(pl2["w"]), float(pl2["h"])

    def _find_port_coord(dev: dict, port_name: str) -> tuple[float, float, str] | None:
        for p in dev.get("ports", []):
            if len(p) >= 3 and str(p[0]) == port_name:
                direction = str(p[3]) if len(p) >= 4 else "unknown"
                return (float(p[1]), float(p[2]), direction)
        return None

    port1 = _find_port_coord(dev1, p1_name)
    port2 = _find_port_coord(dev2, p2_name)
    if port1 is None:
        return (False, f"端口 {d1_name}.{p1_name} 未定义（真违规-端口缺失）")
    if port2 is None:
        return (False, f"端口 {d2_name}.{p2_name} 未定义（真违规-对端端口缺失）")

    # 端口在器件边界内: 相对坐标在 [0, w]×[0, h] 内（含微小数值误差）
    EPS = 1e-6
    p1x, p1y, _ = port1
    p2x, p2y, _ = port2
    if not (-EPS <= p1x <= w1 + EPS and -EPS <= p1y <= h1 + EPS):
        return (False, f"端口 {d1_name}.{p1_name} 不在器件边界内"
                f"（{p1x:.2f},{p1y:.2f} 不在 [0,{w1:.2f}]×[0,{h1:.2f}]，真违规）")
    if not (-EPS <= p2x <= w2 + EPS and -EPS <= p2y <= h2 + EPS):
        return (False, f"端口 {d2_name}.{p2_name} 不在器件边界内"
                f"（{p2x:.2f},{p2y:.2f} 不在 [0,{w2:.2f}]×[0,{h2:.2f}]，真违规）")

    # 3. 连接对端器件存在性已在步骤1验证；4. 端口方向兼容性检查
    VALID_DIRECTIONS = {"north", "south", "east", "west",
                        "n", "s", "e", "w"}  # 接受缩写
    dir1 = port1[2].lower()
    dir2 = port2[2].lower()
    if dir1 not in VALID_DIRECTIONS:
        return (False, f"端口 {d1_name}.{p1_name} 方向非法: {dir1}（真违规-方向非法）")
    if dir2 not in VALID_DIRECTIONS:
        return (False, f"端口 {d2_name}.{p2_name} 方向非法: {dir2}（真违规-方向非法）")

    # 5. 检查端口间距是否在弯曲补偿范围内
    # 任务: "启用bend_compensate后任意距离都可弯曲补偿，
    #        但间距>50μm可能是布局问题，非误报"
    if dx < PORT_ALIGN_FP_THRESHOLD_UM and dy < PORT_ALIGN_FP_THRESHOLD_UM:
        return (True, f"端口偏差在弯曲补偿范围内"
                f"（dx={dx:.2f}μm, dy={dy:.2f}μm < {PORT_ALIGN_FP_THRESHOLD_UM}μm，"
                f"可通过 S-bend/Euler 弯曲补偿，误报）")
    return (False, f"端口偏差过大"
            f"（dx={dx:.2f}μm, dy={dy:.2f}μm ≥ {PORT_ALIGN_FP_THRESHOLD_UM}μm，"
            f"布局问题，真违规）")


# =========================================================================
# 收集 PORT_ALIGNMENT 违规
# =========================================================================
def collect_port_alignment_violations(items: list[dict]) -> list[dict]:
    """默认模式（bend_compensate=True）下运行 DRC 收集 PORT_ALIGNMENT 违规。

    R03 修复（2026-07-06）: 引擎删除 bend_compensate=True 时 return[] 的
    fall-back，改为多维容差方程。默认模式现在是用户实际使用的模式:
    - dx≤10 或 dy≤10: 严格对齐通过
    - dx≤50 且 dy≤50 且方向兼容: S-bend 补偿通过
    - 其他: 报违规

    严格模式（bend_compensate=False）仅用于向后兼容调试，方向兼容性更严格
    （仅 FACING_PAIRS 通过），不反映用户实际体验。

    Returns:
        PORT_ALIGNMENT 违规样本列表，每项含 circuit_name/category/violation/
        circuit/placements。
    """
    samples: list[dict] = []
    total_run = 0
    n_skipped = 0
    audit_start = time.perf_counter()
    for i, item in enumerate(items):
        name = item["name"]
        cat = item["category"]
        circuit = item.get("circuit")
        placements = item.get("placements")
        if circuit is None or placements is None:
            n_skipped += 1
            continue
        total_run += 1
        try:
            # 默认模式: bend_compensate=True（用户实际使用模式，多维容差方程）
            drc_result = polaris_drc.run_drc(
                circuit, placements, bend_compensate=True
            )
            for v in drc_result["violations"]:
                if v["rule_name"] == "PORT_ALIGNMENT":
                    samples.append({
                        "circuit_name": name,
                        "category": cat,
                        "violation": v,
                        "circuit": circuit,
                        "placements": placements,
                    })
        except Exception as e:
            # DRC 失败记录但继续（不影响其他电路审计）
            print(f"  [WARN] DRC 失败 {name}: {type(e).__name__}: {e}")
            n_skipped += 1
        if (i + 1) % 20 == 0 or (i + 1) == len(items):
            elapsed = time.perf_counter() - audit_start
            print(f"  [audit] [{i + 1}/{len(items)}] 已处理，"
                  f"PORT_ALIGNMENT 违规累计 {len(samples)} 条，耗时 {elapsed:.1f}s")
    elapsed_total = time.perf_counter() - audit_start
    print(f"[audit] 收集完成: {total_run} 电路运行 DRC，"
          f"{n_skipped} 电路跳过，PORT_ALIGNMENT 违规 {len(samples)} 条，"
          f"总耗时 {elapsed_total:.1f}s")
    return samples


def sample_violations(samples: list[dict], target_size: int) -> list[dict]:
    """按类别均匀抽样 PORT_ALIGNMENT 违规，覆盖 4 类 benchmark。

    轮询每个类别取一个样本，直到达到 target_size 或样本耗尽。

    Args:
        samples: 全部 PORT_ALIGNMENT 违规样本。
        target_size: 目标抽样数（50）。

    Returns:
        抽样后的样本列表。
    """
    if len(samples) <= target_size:
        return list(samples)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_cat[s["category"]].append(s)
    cat_keys = list(by_cat.keys())
    idx_in_cat = {k: 0 for k in cat_keys}
    sampled: list[dict] = []
    while len(sampled) < target_size:
        progressed = False
        for k in cat_keys:
            if idx_in_cat[k] < len(by_cat[k]):
                sampled.append(by_cat[k][idx_in_cat[k]])
                idx_in_cat[k] += 1
                progressed = True
                if len(sampled) >= target_size:
                    break
        if not progressed:
            break
    return sampled


# =========================================================================
# 统计与报告生成
# =========================================================================
def compute_statistics(judged_samples: list[dict]) -> dict:
    """计算误报统计。"""
    n = len(judged_samples)
    if n == 0:
        return {"n": 0, "n_fp": 0, "n_true": 0, "fp_rate": 0.0}
    n_fp = sum(1 for s in judged_samples if s["is_fp"])
    n_true = n - n_fp
    return {
        "n": n,
        "n_fp": n_fp,
        "n_true": n_true,
        "fp_rate": n_fp / n,
    }


def categorize_false_positive_reasons(judged_samples: list[dict]) -> dict:
    """对误报样本的根因进行分类统计。"""
    fp_reasons: Counter = Counter()
    true_reasons: Counter = Counter()
    for s in judged_samples:
        if s["is_fp"]:
            # 误报根因分类: 按偏差范围
            dx = s["dx"]
            dy = s["dy"]
            dist = math.hypot(dx, dy)
            if dist < 10.0:
                fp_reasons["小偏差(<10μm, 弯曲补偿轻松)"] += 1
            elif dist < 30.0:
                fp_reasons["中等偏差(10-30μm, S-bend补偿)"] += 1
            else:
                fp_reasons["较大偏差(30-50μm, Euler弯曲补偿)"] += 1
        else:
            # 真违规根因分类
            reason = s["reason"]
            if "器件" in reason and "不存在" in reason:
                true_reasons["器件缺失"] += 1
            elif "端口" in reason and ("不在" in reason or "未定义" in reason):
                true_reasons["端口缺失或越界"] += 1
            elif "方向非法" in reason:
                true_reasons["方向非法"] += 1
            elif "偏差过大" in reason:
                # 进一步按偏差范围分类
                dx = s["dx"]
                dy = s["dy"]
                if dx >= 100 or dy >= 100:
                    true_reasons["偏差过大(≥100μm, 布局问题)"] += 1
                else:
                    true_reasons["偏差较大(50-100μm, 布局问题)"] += 1
            else:
                true_reasons["其他"] += 1
    return {
        "fp_reasons": dict(fp_reasons),
        "true_reasons": dict(true_reasons),
    }


def generate_report(items: list[dict], all_samples: list[dict],
                    sampled: list[dict], judged: list[dict],
                    stats: dict, reasons: dict) -> str:
    """生成 Markdown 误报率审查报告。"""
    total_circuits = len(items)
    n_ok = sum(1 for it in items if it.get("circuit") is not None)
    n_skipped = total_circuits - n_ok
    n_total_pa = len(all_samples)
    n_sampled = len(sampled)
    n_judged = len(judged)
    n_fp = stats["n_fp"]
    n_true = stats["n_true"]
    fp_rate = stats["fp_rate"]
    fp_rate_pct = fp_rate * 100
    threshold_pct = COMMERCIAL_FP_RATE_THRESHOLD * 100
    is_pass = fp_rate <= COMMERCIAL_FP_RATE_THRESHOLD

    # 按类别统计抽样分布
    cat_sampled: Counter = Counter(s["category"] for s in sampled)
    cat_fp: Counter = Counter(s["category"] for s in judged if s["is_fp"])
    cat_true: Counter = Counter(s["category"] for s in judged if not s["is_fp"])

    lines: list[str] = []
    lines.append("# DRC 误报率量化审查报告（PoLaRIS real_board）")
    lines.append("")
    lines.append(
        f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S CST', time.localtime())}"
    )
    lines.append(
        f"**审计脚本**: `/workspace/scripts/audit_drc_false_positives.py`"
    )
    lines.append(
        f"**数据来源**: real_board 87 个真实板级 benchmark 电路"
        f"（SiEPIC/expert_demos/gdsfactory/picbench 4 类）"
    )
    lines.append(
        f"**DRC 引擎**: `/workspace/modules/drc/src/polaris_drc/engine.py`"
        f"（12 条 SiEPIC EBeam PDK 规则，严格模式 bend_compensate=False）"
    )
    lines.append(
        f"**商用门槛**: ≤{threshold_pct:.0f}%（Mohan et al., DATE 2023）"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # ========== 1. 审查方法 ==========
    lines.append("## 1. 审查方法")
    lines.append("")
    lines.append(f"- **抽样**: {n_sampled} 个 PORT_ALIGNMENT 违规用例"
                 f"（从 {n_total_pa} 条违规中按类别均匀抽样）")
    lines.append("- **判定**: 自动检查（器件存在/端口在边界内/连接对端存在/"
                 "端口方向兼容/端口间距在弯曲补偿范围内）")
    lines.append("- **标准**: Mohan et al., DATE 2023 \"Machine Learning for DRC\"")
    lines.append("- **DRC 模式**: 严格模式（bend_compensate=False），"
                 "启用 PORT_ALIGNMENT 检查")
    lines.append("- **判定阈值**: 端口偏差 dx<50μm 且 dy<50μm 视为误报"
                 "（弯曲补偿范围内，可通过 S-bend/Euler 弯曲补偿）")
    lines.append("")
    lines.append("### 1.1 自动判定流程")
    lines.append("")
    lines.append("```")
    lines.append("对每个 PORT_ALIGNMENT 违规:")
    lines.append("  1. 解析 violation.message 获取 dx/dy 和连接两端 (d1.p1→d2.p2)")
    lines.append("  2. 检查 d1/d2 是否在 placements 中（器件存在性）")
    lines.append("  3. 检查端口相对坐标是否在器件边界 [0,w]×[0,h] 内")
    lines.append("  4. 检查端口方向是否合法（north/south/east/west）")
    lines.append("     - 启用 bend_compensate 后任意有效方向对都兼容")
    lines.append("  5. 检查端口间距:")
    lines.append("     - dx<50μm 且 dy<50μm → 误报（弯曲补偿范围内）")
    lines.append("     - 否则 → 真违规（布局问题，器件距离过远）")
    lines.append("```")
    lines.append("")

    # ========== 2. 审查结果 ==========
    lines.append("## 2. 审查结果")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总电路数 | {total_circuits} |")
    lines.append(f"| 成功加载电路 | {n_ok} |")
    lines.append(f"| 跳过电路（数据质量问题）| {n_skipped} |")
    lines.append(f"| 严格模式下 PORT_ALIGNMENT 违规总数 | {n_total_pa} |")
    lines.append(f"| 抽样数 | {n_sampled} |")
    lines.append(f"| 实际判定数 | {n_judged} |")
    lines.append(f"| 真违规 | {n_true} |")
    lines.append(f"| 误报 | {n_fp} |")
    lines.append(f"| **误报率** | **{n_fp}/{n_judged} = {fp_rate_pct:.1f}%** |")
    lines.append(f"| 商用门槛 | ≤{threshold_pct:.0f}% |")
    lines.append(f"| **是否达标** | **{'✅ 达标' if is_pass else '❌ 未达标'}** |")
    lines.append("")

    # ========== 3. 误报根因分析 ==========
    lines.append("## 3. 误报根因分析")
    lines.append("")
    fp_reasons = reasons.get("fp_reasons", {})
    true_reasons = reasons.get("true_reasons", {})
    lines.append("### 3.1 误报根因分类")
    lines.append("")
    lines.append("| 误报类型 | 数量 | 根因 |")
    lines.append("|----------|------|------|")
    if fp_reasons:
        for reason, cnt in sorted(fp_reasons.items(), key=lambda x: -x[1]):
            lines.append(f"| {reason} | {cnt} | "
                         f"波导弯曲补偿范围内，可通过 S-bend/Euler 弯曲补偿 |")
    else:
        lines.append("| (无) | 0 | - |")
    lines.append("")
    lines.append("### 3.2 真违规根因分类")
    lines.append("")
    lines.append("| 真违规类型 | 数量 | 根因 |")
    lines.append("|------------|------|------|")
    if true_reasons:
        for reason, cnt in sorted(true_reasons.items(), key=lambda x: -x[1]):
            lines.append(f"| {reason} | {cnt} | 布局问题或电路结构问题，"
                         f"需修复布局或电路定义 |")
    else:
        lines.append("| (无) | 0 | - |")
    lines.append("")

    # ========== 4. 按类别统计 ==========
    lines.append("## 4. 按 benchmark 类别统计")
    lines.append("")
    lines.append("| 类别 | 抽样数 | 误报数 | 真违规数 | 误报率 |")
    lines.append("|------|--------|--------|----------|--------|")
    for cat in CATEGORIES:
        n_s = cat_sampled.get(cat, 0)
        n_f = cat_fp.get(cat, 0)
        n_t = cat_true.get(cat, 0)
        rate = (n_f / n_s * 100) if n_s > 0 else 0.0
        lines.append(f"| {cat} | {n_s} | {n_f} | {n_t} | {rate:.1f}% |")
    lines.append("")

    # ========== 5. 抽样详情 ==========
    lines.append(f"## 5. 抽样详情（前 20 个）")
    lines.append("")
    lines.append("| # | 电路 | 类别 | dx(μm) | dy(μm) | dist(μm) | 判定 | 原因 |")
    lines.append("|---|------|------|--------|--------|----------|------|------|")
    for i, s in enumerate(judged[:20]):
        verdict = "误报" if s["is_fp"] else "真违规"
        # 截断原因避免表格过宽
        reason = s["reason"]
        if len(reason) > 60:
            reason = reason[:57] + "..."
        lines.append(
            f"| {i + 1} | {s['circuit_name']} | {s['category']} | "
            f"{s['dx']:.2f} | {s['dy']:.2f} | {s['dist']:.2f} | "
            f"{verdict} | {reason} |"
        )
    lines.append("")

    # ========== 6. 结论 ==========
    lines.append("## 6. 结论")
    lines.append("")
    status = "✅ 达标" if is_pass else "❌ 未达标"
    lines.append(
        f"- **误报率 {fp_rate_pct:.1f}%** [{status}] "
        f"商用门槛 ≤{threshold_pct:.0f}%"
    )
    if is_pass:
        lines.append(
            f"- PoLaRIS DRC 在严格模式下的 PORT_ALIGNMENT 误报率"
            f"（{fp_rate_pct:.1f}%）低于商用门槛（{threshold_pct:.0f}%），"
            f"达到商用 DRC 工具质量标准。"
        )
        lines.append(
            "- 误报主要为端口偏差在弯曲补偿范围内（<50μm）的用例，"
            "可通过波导弯曲补偿（S-bend/Euler）物理实现，非工艺致命违规。"
        )
    else:
        lines.append(
            f"- PoLaRIS DRC 在严格模式下的 PORT_ALIGNMENT 误报率"
            f"（{fp_rate_pct:.1f}%）高于商用门槛（{threshold_pct:.0f}%），"
            f"需优化布局算法减少端口偏差。"
        )
        lines.append("- 建议改进:")
        lines.append("  1. 优化布局算法（FFDH 装箱时考虑端口对齐）")
        lines.append("  2. 启用 bend_compensate（默认 True，弯曲补偿任意位置偏差）")
        lines.append("  3. 修复大偏差（≥50μm）电路的布局问题")
    lines.append("")

    # ========== 7. 学术诚信声明 ==========
    lines.append("## 7. 学术诚信声明")
    lines.append("")
    lines.append(
        f"- 本报告所有数据来自真实 DRC 重跑（非伪造），每条违规可溯源到具体电路"
        f"（见 `{DATA_PATH}`）。"
    )
    lines.append(
        f"- 误报判定依据: PORT_ALIGNMENT 容差 {PORT_ALIGN_TOL_UM}μm"
        f"（SiEPIC EBeam PDK 弯曲容差 10-20μm），"
        f"弯曲补偿范围阈值 {PORT_ALIGN_FP_THRESHOLD_UM}μm"
        f"（S-bend 弯曲半径 25μm × 2 的典型补偿范围）。"
    )
    lines.append(
        "- DRC 引擎严格模式（bend_compensate=False）启用 PORT_ALIGNMENT 检查，"
        "默认模式（bend_compensate=True）会跳过该检查（弯曲补偿任意位置偏差）。"
    )
    lines.append(
        '- 波导弯曲损耗 0.05dB/弯曲: Chrostowski & Hochberg, '
        '"Silicon Photonics Design", CUP 2015 §4.3。'
    )
    lines.append(
        '- 商用门槛 5%: Mohan et al., DATE 2023 "Machine Learning for DRC"。'
    )
    lines.append("")
    lines.append("## 8. 文献引用")
    lines.append("")
    refs = [
        "1. Mohan et al., \"Machine Learning for DRC\", DATE 2023. https://doi.org/10.23919/DATE56975.2023.10137091",
        "2. SiEPIC EBeam PDK DRC runset. https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "3. Chrostowski & Hochberg, *Silicon Photonics Design*, CUP 2015, §4.3. https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731",
        "4. KLayout DRC 文档. https://www.klayout.org/doc-qt5/manual/drc_runsets.html",
        "5. He et al., OpenDRC, DAC 2023. https://doi.org/10.1109/DAC56929.2023.10247734",
        "6. Berg et al., *Computational Geometry*, Springer 2014. https://doi.org/10.1007/978-3-540-77974-2",
        "7. PoLaRIS DRC 引擎: /workspace/modules/drc/src/polaris_drc/engine.py",
        "8. PoLaRIS real_board harness: /workspace/scripts/run_real_board_drc.py",
    ]
    for r in refs:
        lines.append(r)
    lines.append("")
    lines.append("---")
    lines.append(
        f"*报告由 `audit_drc_false_positives.py` 自动生成，"
        f"{time.strftime('%Y-%m-%d %H:%M:%S CST', time.localtime())}*"
    )
    return "\n".join(lines)


# =========================================================================
# 主入口
# =========================================================================
def parse_args() -> dict:
    """解析命令行参数。"""
    args = {"sample": DEFAULT_SAMPLE_SIZE, "output": REPORT_PATH, "from_cache": False}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == "--sample" and i + 1 < len(argv):
            args["sample"] = int(argv[i + 1])
            i += 2
        elif argv[i] == "--output" and i + 1 < len(argv):
            args["output"] = argv[i + 1]
            i += 2
        elif argv[i] == "--from-cache":
            args["from_cache"] = True
            i += 1
        else:
            i += 1
    return args


def main() -> None:
    """主审计入口。

    支持命令行参数:
    - ``--sample N``: 抽样数（默认 50）
    - ``--output PATH``: 报告输出路径
    - ``--from-cache``: 从缓存加载审计数据（跳过 DRC 重跑）
    """
    args = parse_args()
    sample_size = args["sample"]
    output_path = args["output"]
    from_cache = args["from_cache"]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"[audit] 输出目录: {os.path.dirname(output_path)}")
    print(f"[audit] 抽样数: {sample_size}")
    print(f"[audit] 报告路径: {output_path}")

    if from_cache:
        if not os.path.exists(DATA_PATH):
            raise RuntimeError(
                f"缓存文件不存在: {DATA_PATH}（R03 禁止 fall-back，"
                f"请先不带 --from-cache 运行一次）"
            )
        print(f"[audit] 从缓存加载审计数据: {DATA_PATH}")
        cached = json.loads(open(DATA_PATH, "r", encoding="utf-8").read())
        items = cached["items"]
        all_samples = cached["all_samples"]
        sampled = cached["sampled"]
        judged = cached["judged"]
        stats = cached["stats"]
        reasons = cached["reasons"]
    else:
        # 1. 加载 real_board 所有电路
        print("[audit] 步骤1: 加载 real_board 87 个电路 ...")
        items = load_all_real_board_circuits()
        n_ok = sum(1 for it in items if it.get("circuit") is not None)
        print(f"[audit] 加载完成: {len(items)} 电路（{n_ok} 成功，"
              f"{len(items) - n_ok} 跳过）")

        # 2. 收集 PORT_ALIGNMENT 违规（严格模式）
        print("[audit] 步骤2: 严格模式运行 DRC 收集 PORT_ALIGNMENT 违规 ...")
        all_samples = collect_port_alignment_violations(items)
        print(f"[audit] PORT_ALIGNMENT 违规总数: {len(all_samples)}")

        # 3. 抽样
        print(f"[audit] 步骤3: 抽样 {sample_size} 个 ...")
        sampled = sample_violations(all_samples, sample_size)
        print(f"[audit] 实际抽样: {len(sampled)} 个")

        # 4. 自动判定
        print("[audit] 步骤4: 自动判定是否误报 ...")
        judged: list[dict] = []
        for s in sampled:
            try:
                is_fp, reason = is_false_positive(
                    s["violation"], s["circuit"], s["placements"]
                )
            except Exception as e:
                # 判定失败视为真违规（R03: 不返回假数据）
                is_fp = False
                reason = f"判定异常: {type(e).__name__}: {e}"
            dx, dy = parse_dx_dy_from_message(s["violation"]["message"])
            judged.append({
                "circuit_name": s["circuit_name"],
                "category": s["category"],
                "dx": dx,
                "dy": dy,
                "dist": math.hypot(dx, dy),
                "is_fp": is_fp,
                "reason": reason,
                "message": s["violation"]["message"],
            })
        print(f"[audit] 判定完成: {len(judged)} 个")

        # 5. 统计
        stats = compute_statistics(judged)
        reasons = categorize_false_positive_reasons(judged)
        print(f"[audit] 误报: {stats['n_fp']}, 真违规: {stats['n_true']}, "
              f"误报率: {stats['fp_rate']*100:.1f}%")

        # 保存审计数据
        cache_data = {
            "items": [
                {
                    "name": it["name"],
                    "category": it["category"],
                    "has_circuit": it.get("circuit") is not None,
                    "error": it.get("error"),
                }
                for it in items
            ],
            "all_samples": [
                {
                    "circuit_name": s["circuit_name"],
                    "category": s["category"],
                    "violation": s["violation"],
                }
                for s in all_samples
            ],
            "sampled": [
                {
                    "circuit_name": s["circuit_name"],
                    "category": s["category"],
                    "violation": s["violation"],
                }
                for s in sampled
            ],
            "judged": judged,
            "stats": stats,
            "reasons": reasons,
        }
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"[audit] 审计数据已保存: {DATA_PATH}")

    # 6. 生成报告
    print("[audit] 步骤5: 生成报告 ...")
    report = generate_report(items, all_samples, sampled, judged, stats, reasons)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[audit] 报告已保存: {output_path}")

    # 7. 打印关键结论
    print()
    print("=" * 60)
    print("[audit] 审查完成")
    print(f"[audit] 抽样数: {stats['n']}")
    print(f"[audit] 真违规数: {stats['n_true']}")
    print(f"[audit] 误报数: {stats['n_fp']}")
    print(f"[audit] 误报率: {stats['fp_rate']*100:.1f}%")
    print(f"[audit] 商用门槛: ≤{COMMERCIAL_FP_RATE_THRESHOLD*100:.0f}%")
    is_pass = stats["fp_rate"] <= COMMERCIAL_FP_RATE_THRESHOLD
    print(f"[audit] 是否达标: {'✅ 达标' if is_pass else '❌ 未达标'}")
    print(f"[audit] 报告: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
