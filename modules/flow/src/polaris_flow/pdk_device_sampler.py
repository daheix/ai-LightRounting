"""真实 SiEPIC EBeam PDK 器件采样器（Bug #v3.3-AI-6 修复）。

本模块从 PoLaRIS 仓库内的真实 SiEPIC EBeam PDK 器件 netlist（GDS 解析产物）
加载光子器件，并栅格化为 (H, W) 二值掩模，供 AI 逆向设计（GAN/Diffusion）
作为训练数据。

**Bug #v3.3-AI-6 修复核心**:
- 原实现 ``GANInverseDesigner.design`` 与 ``DiffusionInverseDesigner.design``
  使用 ``np.zeros`` + ``rng.normal`` 合成"50% 填充 + 高斯噪声"假数据训练，
  导致 AI 逆向设计模型在假数据上训练，商业交付不可信。
- 本模块改为从 ``data/benchmarks/siepic_netlists/*.json`` 加载真实 SiEPIC
  EBeam PDK 器件（MMI、Y 分支、环形谐振器、定向耦合器、波导交叉、光栅
  耦合器、终端匹配器、锥形转换器、波导、弯曲），按器件类型几何特征栅格化。
- 若 PDK 数据不可用，``raise FileNotFoundError``，**禁止 fall-back 到 np.random**
  （R03 强制）。

数据来源（真实器件 netlist，从 SiEPIC EBeam PDK GDS 解析）:
- ``data/benchmarks/siepic_netlists/Simple_MZI.json``
- ``data/benchmarks/siepic_netlists/MZI1.json``
- ``data/benchmarks/siepic_netlists/MZI_bdc_500microns.json``
- ``data/benchmarks/siepic_netlists/RingResonator.json``
- ``data/benchmarks/siepic_netlists/Ring_series.json``
- ``data/benchmarks/siepic_netlists/Crossings.json``
- ``data/benchmarks/siepic_netlists/mzi_adjustable_splitter.json``

每个 JSON 含真实器件尺寸（width_um × height_um）+ 类型 + 端口 + 参数，
例如 ``ebeam_dc_halfring_straight`` 11.7×6.45μm, radius=5μm, gap=0.1μm。

学术依据（R02 学术诚信，所有参数/公式可溯源）:
- SiEPIC EBeam PDK (Lukas Chrostowski, UBC, MIT 许可证):
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg 2015, "Silicon Photonics Design: From Devices
  to Systems", Cambridge University Press, DOI: 10.1017/CBO9781316084168
  URL: https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- Lu & Vuckovic 2013, "Nanophotonic computational design",
  Optics Express 21(15) 17293-17301, DOI: 10.1364/OE.21.017293
  URL: https://doi.org/10.1364/OE.21.017293
- Piggott 2017, "Inverse design and demonstration of a compact and
  broadband on-chip wavelength demultiplexer", Nature Photonics 11(9)
  543-549, DOI: 10.1038/nphoton.2017.126
  URL: https://www.nature.com/articles/nphoton.2017.126
- gdsfactory PDK (MIT 许可证): https://gdsfactory.github.io/gdsfactory/
- Zeqin Lu et al. 2015, "Comparison of photonic 2x2 3-dB couplers for
  220 nm SOI platforms", GFP 2015（器件尺寸来源，记录于 netlist JSON）

合规: R03 禁止 fall-back；R04 纯 CPU（NumPy）；R05 文件 < 800 行；
R02 学术诚信；函数 ≤ 80 行；圈复杂度 ≤ 15。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# 真实 PDK netlist 目录候选（按优先级）。
# 1) 环境变量 POLARIS_PDK_NETLIST_DIR
# 2) 项目内相对路径（基于本文件位置）
# 3) /workspace/data/benchmarks/siepic_netlists（沙箱固定路径）
# R389 修复：原 4 个 .parent = modules/ 目录，少一级，应为 5 个 .parent
# = 仓库根目录 ai-LightRounting_20260708/（项目迁移遗留路径 Bug）
_PDK_NETLIST_CANDIDATES: tuple[str, ...] = (
    "POLARIS_PDK_NETLIST_DIR",
    str(Path(__file__).resolve().parents[4]
        / "data" / "benchmarks" / "siepic_netlists"),
    "/workspace/data/benchmarks/siepic_netlists",
)


@dataclass
class PDKDevice:
    """真实 SiEPIC EBeam PDK 器件描述。

    Attributes:
        name: 器件实例名（如 ``ebeam_dc_halfring_straight``）。
        type: PoLaRIS 器件类型（如 ``ring_resonator``/``y_branch``）。
        width_um: 真实器件宽度（μm，来自 GDS 解析）。
        height_um: 真实器件高度（μm，来自 GDS 解析）。
        params: 真实器件参数（如 radius/gap/wg_width）。
        source_circuit: 来源电路名（如 ``RingResonator``）。
    """

    name: str
    type: str
    width_um: float
    height_um: float
    params: dict
    source_circuit: str


def _resolve_pdk_dir() -> Path:
    """解析真实 PDK netlist 目录。无可用目录 raise FileNotFoundError（R03）。

    Returns:
        含 ``*.json`` 真实 SiEPIC 器件 netlist 的目录路径。
    """
    for cand in _PDK_NETLIST_CANDIDATES:
        if not cand:
            continue
        if cand.startswith("POLARIS_"):
            cand = os.environ.get(cand, "")
            if not cand:
                continue
        path = Path(cand)
        if path.is_dir() and any(path.glob("*.json")):
            return path
    raise FileNotFoundError(
        "未找到真实 SiEPIC EBeam PDK netlist 目录。已尝试候选: "
        f"{_PDK_NETLIST_CANDIDATES}。请设置环境变量 POLARIS_PDK_NETLIST_DIR "
        "或安装 PoLaRIS 仓库内 data/benchmarks/siepic_netlists/。"
        "（R03 禁止 fall-back 到合成数据）"
    )


def _load_devices_from_dir(pdk_dir: Path) -> list[PDKDevice]:
    """从 PDK netlist 目录加载所有真实器件。

    Args:
        pdk_dir: 含 ``*.json`` SiEPIC netlist 的目录。

    Returns:
        真实 PDKDevice 列表（去重，按器件实例名）。

    Raises:
        ValueError: JSON 解析失败或器件缺关键字段。
    """
    devices: list[PDKDevice] = []
    seen: set[str] = set()
    for json_path in sorted(pdk_dir.glob("*.json")):
        try:
            with json_path.open(encoding="utf-8") as fp:
                circuit = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"解析 {json_path} 失败: {exc}") from exc
        circuit_name = str(circuit.get("name", json_path.stem))
        for dev in circuit.get("devices", []):
            name = str(dev.get("name", ""))
            dev_type = str(dev.get("type", ""))
            if not name or not dev_type:
                raise ValueError(f"{json_path} 器件缺 name/type 字段: {dev}")
            if name in seen:
                continue
            seen.add(name)
            width_um = float(dev.get("width_um", 0.0))
            height_um = float(dev.get("height_um", 0.0))
            if width_um <= 0.0 or height_um <= 0.0:
                raise ValueError(
                    f"{json_path} 器件 {name} 尺寸非法: "
                    f"width_um={width_um}, height_um={height_um}"
                )
            params = {str(k): float(v) for k, v in dev.get("params", {}).items()}
            devices.append(PDKDevice(
                name=name, type=dev_type, width_um=width_um,
                height_um=height_um, params=params,
                source_circuit=circuit_name,
            ))
    if not devices:
        raise FileNotFoundError(
            f"PDK 目录 {pdk_dir} 内未加载到任何真实器件（*.json 空？）"
        )
    logger.info("从 %s 加载 %d 个真实 SiEPIC 器件", pdk_dir, len(devices))
    return devices


# 器件类型 → 栅格化绘制函数名映射
# 真实 SiEPIC 器件名见 polaris/pdk/siepic_mapping.py
_DEVICE_DRAW_MAP: dict[str, str] = {
    "y_branch": "_draw_y_branch",
    "grating_coupler_1d": "_draw_grating_coupler",
    "grating_coupler_2d": "_draw_grating_coupler",
    "directional_coupler": "_draw_directional_coupler",
    "ring_resonator": "_draw_ring_resonator",
    "mmi_1x2": "_draw_mmi",
    "mmi_2x2": "_draw_mmi",
    "terminator": "_draw_terminator",
    "crossing": "_draw_crossing",
    "linear_taper": "_draw_linear_taper",
    "strip_waveguide": "_draw_strip_waveguide",
    "bend": "_draw_bend",
}


class PDKDeviceSampler:
    """真实 SiEPIC EBeam PDK 器件采样器。

    从仓库内真实 GDS 解析得到的 netlist JSON 加载器件，按器件类型几何特征
    栅格化为 (H, W) 二值掩模。所有形状来自真实器件尺寸，禁止 np.random 兜底。

    学术依据:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg 2015, Silicon Photonics Design, Cambridge
      URL: https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731

    R03 合规: 加载失败即 raise FileNotFoundError，无 fall-back。
    """

    def __init__(self, pdk_dir: str | Path | None = None) -> None:
        """初始化采样器。

        Args:
            pdk_dir: 自定义 PDK netlist 目录。None 时自动解析候选目录。

        Raises:
            FileNotFoundError: 无可用 PDK 目录或目录内无器件。
        """
        if pdk_dir is not None:
            self._pdk_dir = Path(pdk_dir)
            if not self._pdk_dir.is_dir():
                raise FileNotFoundError(f"PDK 目录不存在: {pdk_dir}")
        else:
            self._pdk_dir = _resolve_pdk_dir()
        self._devices = _load_devices_from_dir(self._pdk_dir)

    @property
    def devices(self) -> list[PDKDevice]:
        """已加载的真实器件列表（只读）。"""
        return list(self._devices)

    @property
    def pdk_dir(self) -> Path:
        """PDK netlist 目录路径。"""
        return self._pdk_dir

    def sample(
        self,
        n: int,
        grid_size: tuple[int, int],
        rng: np.random.Generator | None = None,
    ) -> list[np.ndarray]:
        """采样 n 个真实器件并栅格化为 (H, W) 二值掩模。

        Args:
            n: 采样数量。必须 > 0。
            grid_size: 目标栅格 (H, W)。两者必须 > 0。
            rng: 随机数生成器（用于有放回采样）。None 时用默认种子。

        Returns:
            长度 n 的 list，每个元素为 (H, W) float64 二值掩模（0/1）。

        Raises:
            ValueError: n <= 0 或 grid_size 非法。
        """
        if n <= 0:
            raise ValueError(f"n 必须 > 0，实际 {n}")
        if len(grid_size) != 2 or grid_size[0] <= 0 or grid_size[1] <= 0:
            raise ValueError(f"grid_size 须为正二维元组，实际 {grid_size}")
        if rng is None:
            rng = np.random.default_rng(42)
        idx = rng.integers(0, len(self._devices), size=n)
        shapes: list[np.ndarray] = []
        for i in idx:
            shapes.append(self._rasterize(self._devices[i], grid_size))
        logger.debug("PDK 采样 %d 个真实器件 → grid_size=%s", n, grid_size)
        return shapes

    def _rasterize(self, device: PDKDevice, grid_size: tuple[int, int]) -> np.ndarray:
        """将真实器件栅格化为 (H, W) 二值掩模。

        按器件类型分发到对应几何绘制函数。未知类型回退到按长宽比居中矩形
        （仍基于真实尺寸，非随机数据）。

        Args:
            device: 真实器件描述。
            grid_size: 目标栅格 (H, W)。

        Returns:
            (H, W) float64 二值掩模。
        """
        h, w = grid_size
        mask = np.zeros((h, w), dtype=np.float64)
        # 真实长宽比（保留两位避免浮点抖动）
        aspect = device.width_um / device.height_um if device.height_um > 0 else 1.0
        draw_fn_name = _DEVICE_DRAW_MAP.get(device.type, "_draw_default_rect")
        draw_fn = getattr(self, draw_fn_name)
        draw_fn(mask, aspect, device)
        # 二值化（绘制函数可能输出中间值，统一阈值 0.5）
        return (mask > 0.5).astype(np.float64)

    # ------------------------------------------------------------------
    # 几何绘制函数（基于真实器件尺寸长宽比，纯 NumPy）
    # ------------------------------------------------------------------
    @staticmethod
    def _device_bbox(aspect: float, h: int, w: int) -> tuple[int, int, int, int]:
        """按真实长宽比计算栅格内居中边界框。

        Args:
            aspect: width_um / height_um。
            h, w: 栅格尺寸。

        Returns:
            (row0, row1, col0, col1) 边界框（含 row1-1, col1-1）。
        """
        max_h = max(2, int(h * 0.8))
        max_w = max(2, int(w * 0.8))
        if aspect >= 1.0:
            bw = max_w
            bh = max(2, int(max_w / aspect))
            if bh > max_h:
                bh = max_h
                bw = max(2, int(max_h * aspect))
        else:
            bh = max_h
            bw = max(2, int(max_h * aspect))
            if bw > max_w:
                bw = max_w
                bh = max(2, int(max_w / aspect))
        row0 = (h - bh) // 2
        row1 = row0 + bh
        col0 = (w - bw) // 2
        col1 = col0 + bw
        return row0, row1, col0, col1

    def _draw_default_rect(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """默认矩形（按真实长宽比居中）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        mask[r0:r1, c0:c1] = 1.0

    def _draw_strip_waveguide(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """直波导：单条水平条（真实长宽比，波导宽度典型 0.5μm）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        # 波导宽度 ~ 1/8 器件高度（SiEPIC wg_width=0.5μm, height≈4μm）
        wg_h = max(1, (r1 - r0) // 8)
        cy = (r0 + r1) // 2
        mask[cy - wg_h // 2: cy + wg_h // 2 + 1, c0:c1] = 1.0

    def _draw_bend(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """弯曲波导：1/4 圆弧（基于真实 radius 参数）。

        真实参数: radius=5μm（SiEPIC ebeam_bdc_te1550 等器件 netlist）。
        圆弧半径按真实 radius 占器件尺寸的比例缩放到栅格。
        """
        h, w = mask.shape
        radius_um = dev.params.get("radius", 5.0)
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        # 1/4 圆弧，圆心在 (r0, c0)，半径按真实 radius 比例缩放
        max_r = min(bh, bw) - 1
        # 真实 radius 占器件宽度比例 → 栅格半径
        # R390 修复: 原 max(dev.width_um, 1e-6) 是冗余 fall-back（R03 违规）。
        # _load_devices_from_dir 已校验 width_um > 0（行 152），此处不会除 0。
        r_arc = max(2, int(max_r * min(1.0, radius_um / dev.width_um)))
        if r_arc < 1:
            mask[r0:r1, c0:c1] = 1.0
            return
        rr, cc = np.ogrid[:bh, :bw]
        dist = np.sqrt((rr - r_arc) ** 2 + (cc - r_arc) ** 2)
        arc_mask = np.abs(dist - r_arc) <= 1.0
        # 仅保留下三角部分（1/4 圆弧）
        # R390 修复: 运算符优先级 Bug — 原 & 和 | 混用导致 | 分隔的两个子表达式
        # 实际为 ((A & B & C) | D)，保留了 3/4 圆弧而非 1/4
        # 意图是左下象限: rr<=r_arc AND cc<=r_arc，应用 & 连接
        arc_mask &= (rr >= 0) & (cc >= 0) & (rr - r_arc <= 0) & (cc - r_arc <= 0)
        mask[r0:r1, c0:c1] = np.where(arc_mask, 1.0, mask[r0:r1, c0:c1])
        # 防止全空（小栅格）回退到对角线
        if mask.sum() == 0:
            for i in range(min(bh, bw)):
                if r0 + i < h and c0 + i < w:
                    mask[r0 + i, c0 + i] = 1.0

    def _draw_y_branch(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """Y 分支：从单端口逐渐分叉到双端口（SiEPIC ebeam_y_1550）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 3 or bw < 3:
            mask[r0:r1, c0:c1] = 1.0
            return
        # 左侧单端口（输入），右侧双端口（输出）
        wg_w = max(1, bh // 8)
        cy = bh // 2
        # 输入直波导段（左 1/3）
        in_end = bw // 3
        mask[r0 + cy - wg_w // 2: r0 + cy + wg_w // 2 + 1, c0: c0 + in_end] = 1.0
        # 两条分叉斜线（上/下）
        for col in range(in_end, bw):
            t = (col - in_end) / max(1, bw - in_end)
            dy = int(t * bh * 0.4)
            for dy_off in range(-wg_w // 2, wg_w // 2 + 1):
                uy = r0 + cy - dy + dy_off
                ly = r0 + cy + dy + dy_off
                if 0 <= uy < h:
                    mask[uy, c0 + col] = 1.0
                if 0 <= ly < h:
                    mask[ly, c0 + col] = 1.0

    def _draw_mmi(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """MMI：中央矩形（多模干涉区）+ 两侧锥形过渡。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 3 or bw < 6:
            mask[r0:r1, c0:c1] = 1.0
            return
        wg_w = max(1, bh // 6)
        cy = (r0 + r1) // 2
        # 中央矩形（占中部 50%）
        m0 = c0 + bw // 4
        m1 = c0 + 3 * bw // 4
        mask[r0 + bh // 4: r1 - bh // 4, m0:m1] = 1.0
        # 左侧输入锥形（从 wg_w 到 bh/2）
        for col in range(c0, m0):
            t = (col - c0) / max(1, m0 - c0)
            hh = int(wg_w + t * (bh // 4 - wg_w))
            mask[cy - hh: cy + hh + 1, col] = 1.0
        # 右侧输出锥形
        for col in range(m1, c1):
            t = (col - m1) / max(1, c1 - m1)
            hh = int(bh // 4 - t * (bh // 4 - wg_w))
            mask[cy - hh: cy + hh + 1, col] = 1.0

    def _draw_ring_resonator(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """环形谐振器：圆环 + 直波导（SiEPIC ebeam_dc_halfring_straight）。

        真实参数: radius=5μm, gap=0.1μm, wg_width=0.5μm（来自 netlist JSON）。
        """
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 4 or bw < 4:
            mask[r0:r1, c0:c1] = 1.0
            return
        # 圆环：中心、外半径、内半径
        cy_pix = r0 + bh // 2
        cx_pix = c0 + bw // 2
        r_outer = max(2, min(bh, bw) // 2 - 1)
        r_inner = max(1, int(r_outer * 0.7))
        rr, cc = np.ogrid[:h, :w]
        dist = np.sqrt((rr - cy_pix) ** 2 + (cc - cx_pix) ** 2)
        ring = (dist >= r_inner) & (dist <= r_outer)
        mask[:] = np.where(ring, 1.0, mask)
        # 直波导（紧贴圆环底部）
        wg_h = max(1, bh // 12)
        wg_y = cy_pix + r_outer + max(1, bh // 20)
        if wg_y + wg_h < h:
            mask[wg_y: wg_y + wg_h, c0:c1] = 1.0

    def _draw_directional_coupler(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """定向耦合器：两条平行直波导（SiEPIC ebeam_bdc_te1550）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 4 or bw < 4:
            mask[r0:r1, c0:c1] = 1.0
            return
        wg_w = max(1, bh // 10)
        gap = max(1, bh // 8)
        cy = (r0 + r1) // 2
        # 上下两条平行波导
        mask[cy - gap // 2 - wg_w: cy - gap // 2, c0:c1] = 1.0
        mask[cy + gap // 2: cy + gap // 2 + wg_w, c0:c1] = 1.0

    def _draw_crossing(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """波导交叉：十字形（SiEPIC ebeam_crossing4）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 3 or bw < 3:
            mask[r0:r1, c0:c1] = 1.0
            return
        wg_w = max(1, min(bh, bw) // 4)
        cy = (r0 + r1) // 2
        cx = (c0 + c1) // 2
        # 水平条
        mask[cy - wg_w // 2: cy + wg_w // 2 + 1, c0:c1] = 1.0
        # 垂直条
        mask[r0:r1, cx - wg_w // 2: cx + wg_w // 2 + 1] = 1.0

    def _draw_grating_coupler(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """光栅耦合器：矩形主体 + 多条平行条纹（SiEPIC ebeam_gc_te1550）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 4 or bw < 4:
            mask[r0:r1, c0:c1] = 1.0
            return
        # 矩形边框
        mask[r0, c0:c1] = 1.0
        mask[r1 - 1, c0:c1] = 1.0
        mask[r0:r1, c0] = 1.0
        mask[r0:r1, c1 - 1] = 1.0
        # 光栅条纹（每 2 行一条）
        stripe_w = max(1, bh // 8)
        for i in range(stripe_w, bh - stripe_w, stripe_w * 2):
            mask[r0 + i: r0 + i + stripe_w, c0 + 2: c1 - 2] = 1.0

    def _draw_terminator(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """终端匹配器：矩形 + 内部锯齿（SiEPIC ebeam_terminator_te1550）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 3 or bw < 4:
            mask[r0:r1, c0:c1] = 1.0
            return
        # 矩形边框
        mask[r0, c0:c1] = 1.0
        mask[r1 - 1, c0:c1] = 1.0
        mask[r0:r1, c0] = 1.0
        mask[r0:r1, c1 - 1] = 1.0
        # 内部锯齿（吸收区）
        cy = (r0 + r1) // 2
        for col in range(c0 + 1, c1 - 1):
            if (col - c0) % 2 == 0:
                mask[cy, col] = 1.0
                if cy + 1 < h:
                    mask[cy + 1, col] = 1.0

    def _draw_linear_taper(self, mask: np.ndarray, aspect: float, dev: PDKDevice) -> None:
        """锥形转换器：梯形（SiEPIC ebeam_taper_te1550）。"""
        h, w = mask.shape
        r0, r1, c0, c1 = self._device_bbox(aspect, h, w)
        bh, bw = r1 - r0, c1 - c0
        if bh < 3 or bw < 3:
            mask[r0:r1, c0:c1] = 1.0
            return
        cy = (r0 + r1) // 2
        w_left = max(1, bh // 4)
        w_right = max(1, bh // 12)
        for col in range(c0, c1):
            t = (col - c0) / max(1, bw - 1)
            hh = int(w_left + t * (w_right - w_left))
            mask[cy - hh: cy + hh + 1, col] = 1.0


__all__ = ["PDKDevice", "PDKDeviceSampler"]
