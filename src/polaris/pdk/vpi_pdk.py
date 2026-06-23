"""R15 路标：VPIphotonics VPItoolkit PDK <fab> 对齐核心模块。

对齐 VPIphotonics 的 VPItoolkit PDK <fab> 体系，实现：
1. VPIBuildingBlock: VPI 风格 BB（model + certified_range 一体化）
2. VPIToolkitPDK: VPI 风格 PDK 工具包
3. PDAflowExporter: PDAflow API 兼容导出
4. 3 个 Foundry PDK BB 库（LIGENTEC SiN / LioniX TriPleX SiN / HHI InP）
5. VPIPDKRegistry: PDK 注册表（模块加载时自动注册 3 个 PDK）

来源:
- Augustin et al., IEEE JSTQE 24(1), 6100210 (2018)
  https://ieeexplore.ieee.org/document/7937534
- Melloni et al., SPIE 9664, 96641L (2015)
  https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/
- PDAflow API 标准 http://pdaflow.org/
- Smit et al., Semicond. Sci. Technol. 29(8), 083001 (2014)
  https://iopscience.iop.org/article/10.1088/0268-1242/29/8/083001
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from polaris.sim.types import SDict
from polaris.sim.models import (
    RingParams, crossing_s, directional_coupler_s, grating_coupler_s,
    mmi_1x2_s, mmi_2x2_s, phase_shifter_s, ring_resonator_s,
    terminator_s, waveguide_s, y_branch_s,
)
from polaris.sim.models_extended import bend_s, detector_s, modulator_s, taper_s

# 学术来源 URL 常量（规则18 学术诚信）
_URL_AUGUSTIN = "https://ieeexplore.ieee.org/document/7937534"
_URL_MELLONI = "https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/"
_URL_PDAFLOW = "http://pdaflow.org/"
_URL_LIGENTEC = "https://www.vpiphotonics.com/Tools/PDK/PDK_LIGENTEC/"
_URL_LIONIX = "https://www.lionix-international.com/photonics/"
_URL_HHI = "https://www.vpiphotonics.com/Tools/PDK/PDK_HHI/"
_URL_SMIT = "https://iopscience.iop.org/article/10.1088/0268-1242/29/8/083001"


# --- 1. VPIBuildingBlock — VPI 风格 BB（model + certified_range 一体化） ---


@dataclass
class VPIBuildingBlock:
    """VPI 风格 Building Block（model + certified_range 一体化）。

    对齐 VPItoolkit PDK 的 BB 抽象：每个 BB 含 model_func（S 参数模型）、
    params（默认参数）、certified_range（foundry 认证参数范围）、ports（端口列表）。
    BB 模型仅在认证窗口内有效，超出需重新认证（Augustin 2018 JSTQE §IV-C）。

    来源: Melloni et al., SPIE 9664, 96641L (2015)
    https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/
    """

    name: str
    model_func: Callable
    params: dict
    certified_range: dict
    ports: list[str]
    description: str = ""
    source_url: str = ""

    def validate_params(self, **kwargs) -> None:
        """验证参数在认证范围内，超出 raise ValueError（禁止 fall-back）。

        Raises:
            ValueError: 参数超出认证范围时告警退出。
        """
        for key, value in kwargs.items():
            if key not in self.certified_range:
                continue
            if not isinstance(value, int | float | np.floating | np.integer):
                continue
            lo, hi = self.certified_range[key]
            if value < lo or value > hi:
                msg = f"BB '{self.name}' 参数 '{key}'={value} 超出认证范围 [{lo}, {hi}]"
                raise ValueError(msg)

    def evaluate(self, wl, **kwargs) -> SDict:
        """计算 S 参数（先验证参数，再调用 model_func）。

        Raises:
            ValueError: 参数超出认证范围。
        """
        merged = dict(self.params)
        merged.update(kwargs)
        self.validate_params(**merged)
        return self.model_func(wl, **merged)


# --- 2. VPIToolkitPDK — VPI 风格 PDK 工具包 ---


@dataclass
class VPIToolkitPDK:
    """VPI 风格 PDK 工具包（VPItoolkit PDK <fab>）。

    封装 foundry 认证的 BB 库，每个 BB 含 model_func + certified_range。
    来源: Augustin et al., IEEE JSTQE 24(1), 6100210 (2018)
    https://ieeexplore.ieee.org/document/7937534
    """

    name: str
    platform: str
    foundry: str
    bbs: dict[str, VPIBuildingBlock] = field(default_factory=dict)
    source_url: str = ""

    def add_bb(self, bb: VPIBuildingBlock) -> None:
        """添加 BB 到 PDK。"""
        self.bbs[bb.name] = bb

    def get_bb(self, name: str) -> VPIBuildingBlock:
        """获取 BB，不存在 raise KeyError（禁止 fall-back）。"""
        if name not in self.bbs:
            raise KeyError(
                f"BB '{name}' 不在 PDK '{self.name}' 中，可用: {list(self.bbs.keys())}"
            )
        return self.bbs[name]

    def list_bbs(self) -> list[str]:
        """列出所有 BB 名称。"""
        return list(self.bbs.keys())

    def bb_count(self) -> int:
        """返回 BB 数量。"""
        return len(self.bbs)


# --- 3. PDAflowExporter — PDAflow API 兼容导出 ---


class PDAflowExporter:
    """PDAflow API 兼容的 BB 交换格式导出器。

    PDAflow API 定义 BB 的标准交换格式：
    BB = {name, ports, params, model_func, layout_func, sources}
    来源: PDAflow API 标准 http://pdaflow.org/
    """

    @staticmethod
    def export_bb(bb: VPIBuildingBlock) -> dict:
        """导出 BB 为 PDAflow 格式字典。"""
        return {
            "name": bb.name,
            "ports": list(bb.ports),
            "params": dict(bb.params),
            "model_func": getattr(bb.model_func, "__name__", str(bb.model_func)),
            "layout_func": None,  # VPIBuildingBlock 仅含 model_func，layout_func 待后续扩展
            "certified_range": {
                k: [float(v[0]), float(v[1])] for k, v in bb.certified_range.items()
            },
            "sources": [bb.source_url] if bb.source_url else [],
        }

    @staticmethod
    def export_pdk(pdk: VPIToolkitPDK) -> dict:
        """导出整个 PDK 为 PDAflow 格式。"""
        return {
            "name": pdk.name,
            "platform": pdk.platform,
            "foundry": pdk.foundry,
            "source_url": pdk.source_url,
            "bb_count": pdk.bb_count(),
            "bbs": {name: PDAflowExporter.export_bb(bb) for name, bb in pdk.bbs.items()},
        }

    @staticmethod
    def to_json(pdk: VPIToolkitPDK) -> str:
        """导出 PDK 为 JSON 字符串。"""
        return json.dumps(
            PDAflowExporter.export_pdk(pdk), ensure_ascii=False, indent=2, default=str
        )


# --- 4. VPIPDKRegistry — PDK 注册表 ---


class VPIPDKRegistry:
    """VPI PDK 注册表（模块级单例）。

    管理所有已注册的 VPI 风格 PDK，支持按名检索。
    模块加载时自动注册 3 个 foundry PDK（LIGENTEC/LioniX/HHI）。
    """

    _registry: dict[str, VPIToolkitPDK] = {}

    @classmethod
    def register(cls, pdk: VPIToolkitPDK) -> None:
        """注册 PDK。"""
        cls._registry[pdk.name] = pdk

    @classmethod
    def get(cls, name: str) -> VPIToolkitPDK:
        """获取 PDK，不存在 raise KeyError（禁止 fall-back）。"""
        if name not in cls._registry:
            raise KeyError(
                f"PDK '{name}' 不在注册表中，可用: {list(cls._registry.keys())}"
            )
        return cls._registry[name]

    @classmethod
    def list(cls) -> list[str]:
        """列出所有已注册 PDK 名称。"""
        return list(cls._registry.keys())

    @classmethod
    def count(cls) -> int:
        """返回已注册 PDK 数量。"""
        return len(cls._registry)


# --- 5. SOA 辅助模型（HHI InP 有源器件） ---


def _soa_s(wl: float | np.ndarray = 1.55, gain_db: float = 15.0) -> SDict:
    """SOA（半导体光放大器）S 参数模型。

    基于 modulator_s，gain_db > 0 表示增益（insertion_loss_db = -gain_db）。
    端口: in, out
    来源: Smit et al., Semicond. Sci. Technol. 29(8), 083001 (2014) §3
    https://iopscience.iop.org/article/10.1088/0268-1242/29/8/083001
    """
    return modulator_s(wl, phase_rad=0.0, insertion_loss_db=-gain_db)


# --- 6. LIGENTEC SiN PDK（AN800 平台，n_eff ≈ 1.8，损耗 0.5 dB/cm） ---


def build_ligentec_pdk() -> VPIToolkitPDK:
    """构建 LIGENTEC SiN PDK。

    平台: AN800 SiN, n_eff ≈ 1.8, 损耗 0.5 dB/cm, 800nm SiN 厚度。
    来源: https://www.vpiphotonics.com/Tools/PDK/PDK_LIGENTEC/
    """
    pdk = VPIToolkitPDK(name="LIGENTEC", platform="SiN", foundry="LIGENTEC", source_url=_URL_LIGENTEC)
    pdk.add_bb(VPIBuildingBlock(
        name="waveguide", model_func=waveguide_s, ports=["in", "out"],
        params={"length": 100.0, "neff": 1.8, "ng": 2.0, "loss_db_cm": 0.5},
        certified_range={"length": (0.0, 1e4), "neff": (1.7, 1.9), "loss_db_cm": (0.0, 2.0)},
        description="LIGENTEC AN800 SiN 直波导", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="bend", model_func=bend_s, ports=["in", "out"],
        params={"radius": 100.0, "angle_deg": 90.0, "neff": 1.8, "loss_db_cm": 0.5},
        certified_range={"radius": (50.0, 500.0), "angle_deg": (0.0, 180.0)},
        description="LIGENTEC AN800 SiN 弯曲波导", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="dc", model_func=directional_coupler_s, ports=["in1", "in2", "out1", "out2"],
        params={"coupling": 0.5, "length": 100.0, "gap": 0.8},
        certified_range={"coupling": (0.0, 1.0), "length": (0.0, 1e3), "gap": (0.5, 2.0)},
        description="LIGENTEC 定向耦合器", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="mmi_1x2", model_func=mmi_1x2_s, ports=["in", "out1", "out2"],
        params={"insertion_loss_db": 0.4}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="LIGENTEC MMI 1x2 分束器", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="mmi_2x2", model_func=mmi_2x2_s, ports=["in1", "in2", "out1", "out2"],
        params={"insertion_loss_db": 0.5}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="LIGENTEC MMI 2x2 分束器", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="ring", model_func=ring_resonator_s, ports=["in", "through"],
        params={"radius": 100.0, "params": RingParams(neff=1.8, ng=2.0, coupling=0.01, loss_db_cm=0.5)},
        certified_range={"radius": (50.0, 500.0)},
        description="LIGENTEC 环谐振器", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="taper", model_func=taper_s, ports=["in", "out"],
        params={"length": 50.0, "w1": 0.8, "w2": 0.8, "loss_db": 0.1},
        certified_range={"length": (0.0, 500.0), "w1": (0.5, 2.0), "w2": (0.5, 2.0)},
        description="LIGENTEC 锥形转换器", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="crossing", model_func=crossing_s, ports=["in1", "in2", "out1", "out2"],
        params={"insertion_loss_db": 0.3}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="LIGENTEC 波导交叉", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="gc", model_func=grating_coupler_s, ports=["fiber", "waveguide"],
        params={"peak_wl": 1.55, "bandwidth_3db": 0.04, "insertion_loss_db": 1.9},
        certified_range={"peak_wl": (1.5, 1.6), "insertion_loss_db": (0.0, 5.0)},
        description="LIGENTEC 光栅耦合器", source_url=_URL_LIGENTEC))
    pdk.add_bb(VPIBuildingBlock(
        name="terminator", model_func=terminator_s, ports=["in"],
        params={"reflection_db": -40.0}, certified_range={"reflection_db": (-60.0, -20.0)},
        description="LIGENTEC 终端吸收器", source_url=_URL_LIGENTEC))
    return pdk


# --- 7. LioniX TriPleX SiN PDK（n_eff ≈ 1.7，box-shaped 波导） ---


def build_lionix_pdk() -> VPIToolkitPDK:
    """构建 LioniX TriPleX SiN PDK。

    平台: TriPleX SiN, box-shaped waveguide, n_eff ≈ 1.7, 损耗 0.5 dB/cm。
    来源: https://www.lionix-international.com/photonics/
    """
    pdk = VPIToolkitPDK(name="LioniX", platform="SiN", foundry="LioniX International", source_url=_URL_LIONIX)
    pdk.add_bb(VPIBuildingBlock(
        name="waveguide", model_func=waveguide_s, ports=["in", "out"],
        params={"length": 100.0, "neff": 1.7, "ng": 1.8, "loss_db_cm": 0.5},
        certified_range={"length": (0.0, 1e4), "neff": (1.6, 1.8), "loss_db_cm": (0.0, 2.0)},
        description="LioniX TriPleX SiN 直波导", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="bend", model_func=bend_s, ports=["in", "out"],
        params={"radius": 125.0, "angle_deg": 90.0, "neff": 1.7, "loss_db_cm": 0.5},
        certified_range={"radius": (100.0, 500.0), "angle_deg": (0.0, 180.0)},
        description="LioniX TriPleX 弯曲波导", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="dc", model_func=directional_coupler_s, ports=["in1", "in2", "out1", "out2"],
        params={"coupling": 0.5, "length": 100.0, "gap": 1.0},
        certified_range={"coupling": (0.0, 1.0), "length": (0.0, 1e3), "gap": (0.5, 2.0)},
        description="LioniX 定向耦合器", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="mmi_1x2", model_func=mmi_1x2_s, ports=["in", "out1", "out2"],
        params={"insertion_loss_db": 0.5}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="LioniX MMI 1x2 分束器", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="mmi_2x2", model_func=mmi_2x2_s, ports=["in1", "in2", "out1", "out2"],
        params={"insertion_loss_db": 0.6}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="LioniX MMI 2x2 分束器", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="ring", model_func=ring_resonator_s, ports=["in", "through"],
        params={"radius": 125.0, "params": RingParams(neff=1.7, ng=1.8, coupling=0.01, loss_db_cm=0.5)},
        certified_range={"radius": (100.0, 500.0)},
        description="LioniX 环谐振器", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="taper", model_func=taper_s, ports=["in", "out"],
        params={"length": 50.0, "w1": 1.4, "w2": 1.4, "loss_db": 0.1},
        certified_range={"length": (0.0, 500.0), "w1": (1.0, 2.0), "w2": (1.0, 2.0)},
        description="LioniX 锥形转换器", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="crossing", model_func=crossing_s, ports=["in1", "in2", "out1", "out2"],
        params={"insertion_loss_db": 0.4}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="LioniX 波导交叉", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="gc", model_func=grating_coupler_s, ports=["fiber", "waveguide"],
        params={"peak_wl": 1.55, "bandwidth_3db": 0.04, "insertion_loss_db": 2.0},
        certified_range={"peak_wl": (1.5, 1.6), "insertion_loss_db": (0.0, 5.0)},
        description="LioniX 光栅耦合器", source_url=_URL_LIONIX))
    pdk.add_bb(VPIBuildingBlock(
        name="terminator", model_func=terminator_s, ports=["in"],
        params={"reflection_db": -40.0}, certified_range={"reflection_db": (-60.0, -20.0)},
        description="LioniX 终端吸收器", source_url=_URL_LIONIX))
    return pdk


# --- 8. HHI InP PDK（n_eff ≈ 3.3，含有源器件） ---


def build_hhi_pdk() -> VPIToolkitPDK:
    """构建 HHI InP PDK。

    平台: InP, n_eff ≈ 3.3, 损耗 2.0 dB/cm, 含有源器件（SOA/相位调制器/探测器）。
    来源: https://www.vpiphotonics.com/Tools/PDK/PDK_HHI/
    """
    pdk = VPIToolkitPDK(name="HHI", platform="InP", foundry="Fraunhofer HHI", source_url=_URL_HHI)
    pdk.add_bb(VPIBuildingBlock(
        name="waveguide", model_func=waveguide_s, ports=["in", "out"],
        params={"length": 100.0, "neff": 3.3, "ng": 3.5, "loss_db_cm": 2.0},
        certified_range={"length": (0.0, 1e4), "neff": (3.0, 3.5), "loss_db_cm": (0.0, 5.0)},
        description="HHI InP 直波导", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="bend", model_func=bend_s, ports=["in", "out"],
        params={"radius": 50.0, "angle_deg": 90.0, "neff": 3.3, "loss_db_cm": 2.0},
        certified_range={"radius": (30.0, 500.0), "angle_deg": (0.0, 180.0)},
        description="HHI InP 弯曲波导", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="dc", model_func=directional_coupler_s, ports=["in1", "in2", "out1", "out2"],
        params={"coupling": 0.5, "length": 50.0, "gap": 0.5},
        certified_range={"coupling": (0.0, 1.0), "length": (0.0, 1e3), "gap": (0.3, 2.0)},
        description="HHI 定向耦合器", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="mmi_1x2", model_func=mmi_1x2_s, ports=["in", "out1", "out2"],
        params={"insertion_loss_db": 0.5}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="HHI MMI 1x2 分束器", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="mmi_2x2", model_func=mmi_2x2_s, ports=["in1", "in2", "out1", "out2"],
        params={"insertion_loss_db": 0.6}, certified_range={"insertion_loss_db": (0.0, 3.0)},
        description="HHI MMI 2x2 分束器", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="ring", model_func=ring_resonator_s, ports=["in", "through"],
        params={"radius": 50.0, "params": RingParams(neff=3.3, ng=3.5, coupling=0.01, loss_db_cm=2.0)},
        certified_range={"radius": (30.0, 500.0)},
        description="HHI 环谐振器", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="taper", model_func=taper_s, ports=["in", "out"],
        params={"length": 20.0, "w1": 0.5, "w2": 0.5, "loss_db": 0.2},
        certified_range={"length": (0.0, 200.0), "w1": (0.3, 2.0), "w2": (0.3, 2.0)},
        description="HHI 锥形转换器", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="soa", model_func=_soa_s, ports=["in", "out"],
        params={"gain_db": 15.0}, certified_range={"gain_db": (0.0, 30.0)},
        description="HHI 半导体光放大器（SOA）", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="phase_modulator", model_func=phase_shifter_s, ports=["in", "out"],
        params={"phase_rad": 0.0, "insertion_loss_db": 0.5},
        certified_range={"phase_rad": (0.0, 2 * np.pi), "insertion_loss_db": (0.0, 5.0)},
        description="HHI InP 相位调制器", source_url=_URL_HHI))
    pdk.add_bb(VPIBuildingBlock(
        name="photodetector", model_func=detector_s, ports=["in"],
        params={"responsivity": 1.0}, certified_range={"responsivity": (0.0, 2.0)},
        description="HHI InP 光电探测器", source_url=_URL_HHI))
    return pdk


# --- 9. 模块加载时自动注册 3 个 foundry PDK ---

VPIPDKRegistry.register(build_ligentec_pdk())
VPIPDKRegistry.register(build_lionix_pdk())
VPIPDKRegistry.register(build_hhi_pdk())


__all__ = [
    "PDAflowExporter", "VPIBuildingBlock", "VPIPDKRegistry", "VPIToolkitPDK",
    "build_hhi_pdk", "build_ligentec_pdk", "build_lionix_pdk",
]
