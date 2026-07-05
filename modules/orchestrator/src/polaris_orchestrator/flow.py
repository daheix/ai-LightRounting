"""PoLaRIS EDA 流程编排主体（polaris-orchestrator）。

实现 ``run_eda_flow``，组合 18 个独立子模块为完整 EDA 流程，9 个 stage 顺序
执行（polaris_pdk 在 stage 1 与 stage 7 各用一次）::

    1. PDK 目录       polaris_pdk.list_platforms
    2. 电路验证       polaris_core.validate_circuit
    3. AI 布局        polaris_place.place_circuit  mode="analytical"
    4. 智能布线       polaris_route.route_circuit
    5. 仿真验证       polaris_sparam.simulate_mzi_sparam + compute_clements_unitary
                     + polaris_pam4.simulate_pam4 + polaris_fdtd.simulate_waveguide_fdtd
    6. DRC / LVS      polaris_drc.run_drc + polaris_lvs.run_lvs
    7. GDS 导出       polaris_gdsio.export_gds
    8. 逆向设计       polaris_inverse.optimize_waveguide_width  n_iterations=10
    9. 量子验证       polaris_klm.klm_cnot + polaris_boson.hom_interference

注: polaris-fde / polaris-eme / polaris-bpm / polaris-fdfd 为独立仿真子模块，
提供单职责 API 但不进入主流程 stage（按需调用，避免主流程耗时膨胀）。

## 编排策略 vs R03 fall-back 禁令（*创新*）

- R03 禁止业务 fall-back: 子模块内部失败必须 raise，禁止假数据兜底。
- 编排层例外: 编排层允许某 stage 失败后继续执行后续 stage（``strict=False``
  默认），这是**编排策略**而非业务 fall-back。
  - 底层逻辑: EDA 流程中仿真失败不应阻塞 GDS 导出，DRC 失败不应阻塞量子
    验证——用户需要全流程诊断报告而非单点中断。OpenROAD / klayout 流程也采用
    "best-effort + 报告"模式（OpenROAD GitHub Actions 2024）。
  - 支持理论: TILOS MacroPlacement 流程强调 stage 解耦 + 全报告
    （https://github.com/TILOS-AI-CAD-Institute/MacroPlacement）。
  - 上游 stage 失败时，下游 stage 不使用假数据 fall-back，而是让子模块自身
    抛 RuntimeError（如 placements=None → route_circuit raise），编排层捕获
    后记录为 stage 失败。即"失败向上传播，编排层汇总"，子模块内部仍零 fall-back。
- ``strict=True``: 首个 stage 失败立即 raise，供需要严格流水线的场景使用。

## 来源（R02 学术诚信，≥5 个文献 URL）

- OpenROAD RTL-to-GDS21 流程: https://github.com/The-OpenROAD-Project/OpenROAD
- TILOS MacroPlacement benchmark:
  https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- gdsfactory 流程编排: https://gdsfactory.github.io/gdsfactory/
- Hamard et al., "Open source photonic integrated circuits"),
  https://doi.org/10.1364/OE.391040
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, §10
- pytest 测试框架: https://docs.pytest.org/
"""

from __future__ import annotations

import json
import os
import time
import traceback
from typing import Any, Callable

import polaris_core
import polaris_gdsio
import polaris_inverse
import polaris_pdk
import polaris_place
import polaris_boson
import polaris_route
import polaris_sparam
import polaris_pam4
import polaris_fdtd
import polaris_drc
import polaris_klm
import polaris_lvs

# 编排层版本（与子模块对齐到 5.0.0）
__version__ = "5.0.0"

# Stage 元数据：stage_id -> (name, callable)
# callable 签名: (circuit, ctx) -> Any
#   - circuit: 用户传入的 polaris-core circuit dict
#   - ctx: 编排上下文 dict（含 placements / output_dir 等跨 stage 共享数据）
# 返回值会写入 stage dict 的 "result" 字段（若可 JSON 序列化则原样，否则转 str）
_STAGE_LIST: list[tuple[int, str, Callable[[dict, dict], Any]]] = []


def _stage_pdk_catalog(_circuit: dict, _ctx: dict) -> Any:
    """Stage 1: PDK 目录 - 列出所有 PDK 平台。"""
    return polaris_pdk.list_platforms()


def _stage_validate_circuit(circuit: dict, _ctx: dict) -> Any:
    """Stage 2: 电路验证 - 校验 circuit 结构完整性（失败 raise）。"""
    return polaris_core.validate_circuit(circuit)


def _stage_place(circuit: dict, ctx: dict) -> Any:
    """Stage 3: AI 布局 - analytical 解析法布局，结果存入 ctx 供下游 stage 复用。"""
    result = polaris_place.place_circuit(circuit, mode="analytical")
    # 将 placements 写入上下文，供 stage 4 / stage 6 复用
    ctx["placements"] = result["placements"]
    ctx["hpwl"] = result["hpwl"]
    return result


def _stage_route(circuit: dict, ctx: dict) -> Any:
    """Stage 4: 智能布线 - 使用 stage 3 的 placements 执行曲线波导布线 + 弯曲补偿。

    流程:
        1. ``route_circuit`` 生成初始曲线波导路径
        2. ``bend_compensate`` 后处理: 检测 PORT_ALIGNMENT 端口偏差
           (dx>10μm 且 dy>10μm) 的连接，自动调整下游器件位置使端口对齐
           （S 弯曲波导补偿，半径 ≥5μm，SiEPIC EBeam PDK 标准），
           重新生成受影响路径

    若上游 stage 3 失败导致 ctx["placements"] 缺失，则传 None 给
    route_circuit，由子模块自身 raise RuntimeError（R03: 不假数据 fall-back）。

    *创新*（弯曲波导补偿）: 在布线后自动调整下游器件位置使端口对齐，
    消除 PORT_ALIGNMENT DRC 违规。底层逻辑: SiEPIC EBeam PDK 波导弯曲
    容差 10μm，超过此容差需 S-bend 补偿；本步骤移动器件使偏差归零，
    路径变为直线（0 弯曲）或单轴偏移（S-bend，2 弯曲），弯曲半径由
    CurvyRouter 保证 ≥5μm。

    来源（R02 学术诚信）:
        - Chrostowski & Hochberg 2015 §4.2 Silicon Photonics Design
          波导弯曲半径 ≥5μm，弯曲损耗 0.05 dB/bend
          https://www.cambridge.org/core/books/silicon-photonics-design/
        - SiEPIC EBeam PDK bend_euler radius=5μm
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - LiDAR ISPD'25 §3.2 curvy waveguide detailed routing
          https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    """
    placements = ctx.get("placements")
    route_result = polaris_route.route_circuit(circuit, placements, mode="curvy")
    # 弯曲波导补偿后处理: 检测 PORT_ALIGNMENT 违规并调整下游器件位置
    # 仅当有 placements 和 paths 时执行（缺一则跳过，非 fall-back）
    if placements is not None and isinstance(route_result, dict) \
            and route_result.get("paths"):
        new_placements, new_route = polaris_route.bend_compensate(
            circuit, placements, route_result
        )
        ctx["placements"] = new_placements
        return new_route
    return route_result


def _stage_simulate(_circuit: dict, _ctx: dict) -> Any:
    """Stage 5: 仿真验证 - MZI S 参数扫描 + Clements 酉矩阵 + PAM4 眼图 + FDTD 全波仿真。

    使用 polaris_sparam（频域 S 参数 + MZI + Clements）、polaris_pam4（PAM4 信号）、
    polaris_fdtd（时域 FDTD 全波仿真，与解析模型交叉验证）。
    """
    mzi = polaris_sparam.simulate_mzi_sparam()
    clements = polaris_sparam.compute_clements_unitary(n_modes=4)
    pam4 = polaris_pam4.simulate_pam4()
    # FDTD 全波仿真（与 sparam 解析模型交叉验证；n_steps=200 限速）
    try:
        fdtd = polaris_fdtd.simulate_waveguide_fdtd(dx_um=0.1, n_steps=200)
    except Exception as exc:
        # FDTD 失败不阻塞 stage 5（编排策略：解析模型已提供主要结论，
        # FDTD 仅作交叉验证；失败原因记录，供诊断）
        fdtd = {"error": f"FDTD 失败（不阻塞 stage 5）: {type(exc).__name__}: {exc}"}
    return {
        "mzi_sparam": mzi,
        "clements_unitary": clements,
        "pam4": pam4,
        "fdtd_waveguide": fdtd,
    }


def _stage_drc_lvs(circuit: dict, ctx: dict) -> Any:
    """Stage 6: DRC / LVS - 设计规则检查 + 网表一致性比对。

    若 stage 3 失败导致 placements 缺失，run_drc 自身 raise（R03）。
    """
    placements = ctx.get("placements")
    drc = polaris_drc.run_drc(circuit, placements)
    lvs = polaris_lvs.run_lvs(circuit)
    return {
        "drc": drc,
        "lvs": lvs,
    }


def _stage_export_gds(circuit: dict, ctx: dict) -> Any:
    """Stage 7: GDS 导出 - 将 circuit 导出为 GDSII 文件。"""
    output_dir = ctx["output_dir"]
    os.makedirs(output_dir, exist_ok=True)
    gds_path = os.path.join(output_dir, f"{circuit.get('name', 'circuit')}.gds")
    return polaris_gdsio.export_gds(circuit, gds_path)


def _stage_inverse(_circuit: dict, _ctx: dict) -> Any:
    """Stage 8: 逆向设计 - JAX jax.grad 波导宽度优化（n_iterations=10 省时）。"""
    return polaris_inverse.optimize_waveguide_width(n_iterations=10)


def _stage_quantum(_circuit: dict, _ctx: dict) -> Any:
    """Stage 9: 量子验证 - KLM CNOT 量子门 + HOM 双光子干涉。

    polaris_klm 提供 KLM CNOT（Ralph 2002，成功率 1/9），
    polaris_boson 提供 HOM 双光子干涉（Hong-Ou-Mandel 1987）。
    """
    klm = polaris_klm.klm_cnot()
    hom = polaris_boson.hom_interference(theta=0.0)
    return {
        "klm_cnot": klm,
        "hom_interference": hom,
    }


# 注册 stage 顺序（stage_id 从 1 开始）
_STAGE_LIST = [
    (1, "PDK目录", _stage_pdk_catalog),
    (2, "电路验证", _stage_validate_circuit),
    (3, "AI布局", _stage_place),
    (4, "智能布线", _stage_route),
    (5, "仿真验证", _stage_simulate),
    (6, "DRC_LVS", _stage_drc_lvs),
    (7, "GDS导出", _stage_export_gds),
    (8, "逆向设计", _stage_inverse),
    (9, "量子验证", _stage_quantum),
]


def _to_jsonable(obj: Any) -> Any:
    """将 stage 结果转为 JSON 可序列化形式，不可序列化则转 str。

    用于把 stage result 安全写入编排层返回 dict（polaris-inverse 的
    fom_history 是 list[float]，polaris-quantum 的酉矩阵是 list of list of
    [real, imag]，均原生 JSON 可序列化；此处仅做兜底转换，不修改原对象）。

    Args:
        obj: 任意 Python 对象。

    Returns:
        JSON 可序列化对象（dict/list/str/number/bool/None）。
    """
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def run_eda_flow(
    circuit: dict,
    output_dir: str,
    skip_stages: list | None = None,
    strict: bool = False,
) -> dict:
    """一键运行完整 PoLaRIS EDA 流程（9 个 stage，对应 8 个子模块）。

    顺序执行 PDK 目录 → 电路验证 → AI 布局 → 智能布线 → 仿真验证 →
    DRC/LVS → GDS 导出 → 逆向设计 → 量子验证。每 stage 用 try/except 捕获
    异常，失败记录 ``error`` 但不中断（除非 ``strict=True``）。

    Args:
        circuit: polaris-core 风格 circuit dict（含 name/devices/connections/
            canvas_w/canvas_h/optical_wavelength_nm）。
        output_dir: 输出目录路径（GDS 等产物落盘位置，不存在则创建）。
        skip_stages: 跳过的 stage id 列表（如 ``[8]`` 跳过逆向设计省时），
            None 表示不跳过任何 stage。
        strict: 严格模式。``True`` 时首个 stage 失败即 raise；``False``（默认）
            时 stage 失败仅记录 error，继续后续 stage，最终汇总 n_failed。

    Returns:
        编排结果 dict::

            {
                "stages": [
                    {
                        "stage_id": int,       # 1-9
                        "name": str,           # stage 名称
                        "status": str,         # "success"/"failed"/"skipped"
                        "duration": float,     # 耗时 (秒)
                        "result": Any,         # stage 返回值（失败时为 None）
                        "error": str | None,   # 失败时的异常信息，成功时 None
                    },
                    ...
                ],
                "n_success": int,             # 成功 stage 数
                "n_failed": int,              # 失败 stage 数
                "n_skipped": int,             # 跳过 stage 数
                "total_duration": float,      # 总耗时 (秒，含失败 stage)
            }

    Raises:
        RuntimeError: ``strict=True`` 且某 stage 失败时，立即 raise 该 stage
            的异常（含 stage_id 与 traceback）。
    """
    if not isinstance(circuit, dict):
        raise RuntimeError(
            f"circuit 必须是 dict，得到 {type(circuit).__name__}"
            f"（R03 禁止 fall-back）"
        )
    if not isinstance(output_dir, str) or not output_dir:
        raise RuntimeError(
            f"output_dir 必须是非空 str，得到 {output_dir!r}"
            f"（R03 禁止 fall-back）"
        )

    skip_set = set(skip_stages) if skip_stages else set()
    # 编排上下文：跨 stage 共享 placements / hpwl / output_dir
    ctx: dict[str, Any] = {
        "output_dir": output_dir,
        "placements": None,
        "hpwl": None,
    }

    stages: list[dict] = []
    n_success = 0
    n_failed = 0
    n_skipped = 0
    flow_start = time.perf_counter()

    for stage_id, name, stage_fn in _STAGE_LIST:
        # 跳过指定 stage
        if stage_id in skip_set:
            stages.append({
                "stage_id": stage_id,
                "name": name,
                "status": "skipped",
                "duration": 0.0,
                "result": None,
                "error": None,
            })
            n_skipped += 1
            continue

        stage_start = time.perf_counter()
        try:
            result = stage_fn(circuit, ctx)
            duration = time.perf_counter() - stage_start
            stages.append({
                "stage_id": stage_id,
                "name": name,
                "status": "success",
                "duration": float(duration),
                "result": _to_jsonable(result),
                "error": None,
            })
            n_success += 1
        except Exception as exc:
            duration = time.perf_counter() - stage_start
            err_msg = f"{type(exc).__name__}: {exc}"
            tb = traceback.format_exc()
            stages.append({
                "stage_id": stage_id,
                "name": name,
                "status": "failed",
                "duration": float(duration),
                "result": None,
                "error": err_msg,
                "traceback": tb,
            })
            n_failed += 1
            if strict:
                # strict 模式：首个失败立即 raise（编排策略，非 R03 fall-back）
                raise RuntimeError(
                    f"stage {stage_id} ({name}) 失败 [{strict=}]: {err_msg}"
                ) from exc

    total_duration = time.perf_counter() - flow_start
    return {
        "stages": stages,
        "n_success": n_success,
        "n_failed": n_failed,
        "n_skipped": n_skipped,
        "total_duration": float(total_duration),
    }


__all__ = [
    "run_eda_flow",
    "__version__",
]
