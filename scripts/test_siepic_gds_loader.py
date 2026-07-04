#!/usr/bin/env python3
"""SiEPIC GDS 解析器验证脚本（R345）。

验证 ``polaris_gds_tools.gds_loader.load_gds_to_circuit`` 可正确解析
``real_board/siepic/`` 下的 SiEPIC GDS 文件，输出每个文件的器件数 +
连接数 + 使用的识别策略。

## 测试覆盖

默认测试 10 个 GDS 文件，覆盖三种器件识别策略：
- **策略 A（instance）**: 标准 SiEPIC PDK 用法（如 MZI1.gds）
- **策略 B（DEVREC polygon）**: Lumerical CML 导出（如 ebeam_taper_475_500_te1550.gds）
- **策略 C（顶层 cell）**: 单器件测试版图（如 wg_test.gds）

``--all`` 选项跑全量 229 个文件并统计成功率。

## 规则依据

- R03 禁止 fall-back: 解析失败即记录根因，不伪造数据
- R05 Bug 必须修复: 发现解析失败即定位根因
- R12 时间戳规范: 所有输出带时间戳

用法:
    python scripts/test_siepic_gds_loader.py            # 默认测 10 个
    python scripts/test_siepic_gds_loader.py --all      # 全量 229 个
    python scripts/test_siepic_gds_loader.py --file <path>  # 单文件

引用（R02 学术诚信）:
- SiEPIC EBeam PDK (MIT, UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout Database API: https://www.klayout.org/doc-qt5/code/
- Chrostowski & Hochberg, Silicon Photonics Design, CUP 2015
  ISBN 9781107016838: https://www.cambridge.org/9781107016838
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path

# 抑制 klayout GDS 大记录警告（不影响解析结果）
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "modules" / "gds_tools" / "src"))

from polaris_gds_tools.gds_loader import load_gds_to_circuit

SIEPIC_DIR = PROJECT_ROOT / "real_board" / "siepic"

# 默认测试 10 个文件，覆盖三种识别策略
# 来源: 实测确认每个文件触发对应策略
DEFAULT_TEST_FILES = [
    # 策略 A（instance 识别）— 标准 SiEPIC PDK 电路
    "MZI1.gds",
    "RingResonator.gds",
    "Simple_MZI.gds",
    "Crossings.gds",
    "Examples__ebeam__MZI_ebeam_dc_te1550.gds",
    # 策略 B（DEVREC polygon 识别）— Lumerical CML 导出
    "Examples__MZI_bdc.gds",
    "Examples__ebeam_taper_475_500_te1550.gds",
    "Lumerical_EBeam_CML__EBeam__fdtd__ebeam_y_1550__y_500.gds",
    # 策略 C（顶层 cell 自身）— 单器件测试版图
    "Examples__wg_test.gds",
    # 额外覆盖（带 Spice_param 参数）
    "Examples__MZI1.gds",
]


def _now() -> str:
    """当前时间戳（R12）。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _discover_all_gds() -> list[Path]:
    """枚举 siepic 目录全部 GDS 文件（不区分大小写扩展名）。"""
    files: list[Path] = []
    for f in sorted(SIEPIC_DIR.iterdir()):
        if f.suffix.lower() == ".gds":
            files.append(f)
    return files


def _parse_one(gds_path: Path) -> dict:
    """解析单个 GDS 文件，返回结果 dict。

    Returns:
        {name, ok, n_devices, n_connections, strategy, error, elapsed}
    """
    t0 = time.perf_counter()
    try:
        circuit = load_gds_to_circuit(gds_path)
        elapsed = time.perf_counter() - t0
        return {
            "name": gds_path.name,
            "ok": True,
            "n_devices": len(circuit["devices"]),
            "n_connections": len(circuit["connections"]),
            "strategy": _detect_strategy(gds_path),
            "error": "",
            "elapsed": elapsed,
        }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {
            "name": gds_path.name,
            "ok": False,
            "n_devices": 0,
            "n_connections": 0,
            "strategy": "",
            "error": f"{type(e).__name__}: {e}",
            "elapsed": elapsed,
        }


def _detect_strategy(gds_path: Path) -> str:
    """从日志推断使用的策略（简化版：基于文件特征）。

    实际策略选择由 load_gds_to_circuit 内部决定，这里基于文件特征
    推断用于报告展示。准确策略以 load_gds_to_circuit 的 logger 输出为准。
    """
    try:
        import klayout.db as db
        ly = db.Layout()
        ly.read(str(gds_path))
        top = ly.top_cells()[0]
        n_inst = sum(1 for _ in top.each_inst())
        if n_inst > 0:
            return "instance"
        # 无 instance，检查 DEVREC polygon
        for li in ly.layer_indices():
            info = ly.get_info(li)
            if int(info.layer) == 68 and int(info.datatype) == 0:
                for it in top.begin_shapes_rec(li):
                    s = it.shape()
                    if s.is_box() or s.is_polygon():
                        return "devrec_polygon"
        return "top_cell"
    except Exception:
        return "?"


def _print_result(r: dict, idx: int, total: int) -> None:
    """打印单条结果。"""
    status = "OK " if r["ok"] else "ERR"
    strat = r["strategy"][:16] if r["strategy"] else "-"
    print(
        f"[{_now()}] [{idx:3d}/{total}] {status} {r['name'][:55]:55s} "
        f"策略={strat:16s} 器件={r['n_devices']:4d} 连接={r['n_connections']:4d} "
        f"耗时={r['elapsed']:.3f}s"
    )
    if not r["ok"]:
        print(f"           错误: {r['error'][:200]}")


def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(description="SiEPIC GDS 解析器验证脚本")
    parser.add_argument("--all", action="store_true", help="测试全量 229 个文件")
    parser.add_argument("--file", type=str, default="", help="测试单个文件")
    args = parser.parse_args()

    print(f"[{_now()}] PoLaRIS SiEPIC GDS 解析器验证 (R345)")
    print(f"[{_now()}] 解析器: polaris_gds_tools.gds_loader.load_gds_to_circuit")
    print(f"[{_now()}] 数据目录: {SIEPIC_DIR}")
    print()

    # 选择测试文件
    if args.file:
        files = [Path(args.file)]
        if not files[0].exists():
            print(f"[{_now()}] 文件不存在: {args.file}")
            return 1
    elif args.all:
        files = _discover_all_gds()
    else:
        files = []
        for name in DEFAULT_TEST_FILES:
            p = SIEPIC_DIR / name
            if p.exists():
                files.append(p)
        if len(files) < 10:
            # 补齐到 10 个
            all_files = _discover_all_gds()
            existing = {f.name for f in files}
            for f in all_files:
                if f.name not in existing and len(files) < 10:
                    files.append(f)
                    existing.add(f.name)

    total = len(files)
    print(f"[{_now()}] 待测试文件数: {total}")
    print("=" * 100)

    results = []
    strategy_counter: Counter = Counter()
    t_start = time.perf_counter()

    for i, f in enumerate(files, 1):
        r = _parse_one(f)
        results.append(r)
        if r["ok"]:
            strategy_counter[r["strategy"]] += 1
        _print_result(r, i, total)

    elapsed_total = time.perf_counter() - t_start
    n_ok = sum(1 for r in results if r["ok"])
    n_fail = total - n_ok

    print("=" * 100)
    print(f"[{_now()}] 验证完成")
    print(f"  总数: {total}")
    print(f"  成功: {n_ok} ({100 * n_ok / total:.1f}%)" if total else "  无文件")
    print(f"  失败: {n_fail}")
    print(f"  总耗时: {elapsed_total:.2f}s")
    if strategy_counter:
        print(f"  策略分布: {dict(strategy_counter)}")

    if n_fail > 0:
        print()
        print("失败详情:")
        fail_counter: Counter = Counter()
        for r in results:
            if not r["ok"]:
                # 截取错误根因
                err = r["error"]
                if "未匹配到器件" in err:
                    fail_counter["端口未匹配器件"] += 1
                elif "未匹配到任何 PIN path" in err:
                    fail_counter["PIN text 无 path"] += 1
                elif "无顶层 cell" in err:
                    fail_counter["无顶层 cell"] += 1
                else:
                    fail_counter[err[:60]] += 1
        for reason, cnt in fail_counter.most_common():
            print(f"  [{cnt:3d}] {reason}")

    # 退出码：默认测试 10 个时要求 100% 成功；--all 时要求 ≥95%
    if args.all:
        rate = 100 * n_ok / total if total else 0
        return 0 if rate >= 95 else 1
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
