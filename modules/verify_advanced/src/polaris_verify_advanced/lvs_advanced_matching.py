"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances: dict[str, ToleranceSpec] | None = None,
) -> DeviceMatchResult:
    """带容差的器件参数匹配（R186）。

    对标 KLayout LVS tolerance 与 Calibre nmLVS TOLERANCE 规格。

    匹配规则：
    1. 器件名相同视为候选匹配对
    2. 对每个参数，偏差 = |ref - ext|
    3. 允许偏差 = abs_tol + rel_tol × |ref|（KLayout 公式）
    4. 若所有参数偏差 ≤ 允许偏差 → 匹配成功
    5. 否则记录参数偏差
    6. 参考有但版图无 → 缺失器件
    7. 版图有但参考无 → 多余器件

    Calibre TOLERANCE 公式（百分比）：
    deviation% = |v1 - v2| / max(|v2|, ε) × 100

    Args:
        reference: 参考网表或 {device_name: {param: value}} 字典。
        extracted: 提取网表或 {device_name: {param: value}} 字典。
        tolerances: 参数容差规格 {param_name: ToleranceSpec}，
            None 时默认 5% 相对容差。

    Returns:
        器件匹配结果。

    Raises:
        TypeError: 输入类型不支持。
    """
    ref_params = _to_param_dict(reference)
    ext_params = _to_param_dict(extracted)
    if tolerances is None:
        tolerances = {}

    result = DeviceMatchResult()
    ref_names = set(ref_params.keys())
    ext_names = set(ext_params.keys())
    result.missing_devices = sorted(ref_names - ext_names)
    result.extra_devices = sorted(ext_names - ref_names)

    for name in sorted(ref_names & ext_names):
        ref_p = ref_params[name]
        ext_p = ext_params[name]
        all_keys = set(ref_p.keys()) | set(ext_p.keys())
        matched = True
        for key in all_keys:
            if key not in ref_p or key not in ext_p:
                continue
            rv = float(ref_p[key])
            ev = float(ext_p[key])
            deviation = abs(rv - ev)
            spec = tolerances.get(key, ToleranceSpec(abs_tol=0.0, rel_tol=0.05))
            allowed = spec.abs_tol + spec.rel_tol * abs(rv)
            if deviation > allowed:
                rel_dev = deviation / max(abs(rv), 1e-12) * 100
                result.param_mismatches.append(
                    ParamMismatch(
                        device_name=name,
                        param_name=key,
                        reference_value=rv,
                        extracted_value=ev,
                        deviation=deviation,
                        relative_deviation=rel_dev,
                    )
                )
                matched = False
        if matched:
            result.matched_devices.append(name)
    return result


def _to_param_dict(
    netlist: ExtractedNetlist | dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """将网表或字典统一为 {device_name: {param: value}} 字典。

    Raises:
        TypeError: 输入类型不支持。
    """
    if isinstance(netlist, dict):
        return netlist
    if isinstance(netlist, ExtractedNetlist):
        return {name: {} for name in netlist.devices}
    raise TypeError(f"不支持的网表类型: {type(netlist).__name__}")


__all__ = ["match_devices_with_tolerance"]
