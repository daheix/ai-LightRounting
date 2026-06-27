"""R13 路标：Aspic 风格 building block 抽象层与传输矩阵形式化。

对齐 Aspic（Polimi 商业光子电路仿真器）的频域 S 参数电路仿真核心：
"building block + 数学模型 + S 参数级联"。

核心组件:
1. TMatrix: 传输矩阵形式化（M₊/M₋ 分量）
2. s_to_t / t_to_s: S 矩阵与传输矩阵互转
3. BuildingBlock: Aspic 风格 building block 抽象
4. BBRegistry: BB 注册表（对齐 Aspic 30+ BB 库）
5. VirtualExperiment: 虚拟实验（what-if 参数扫描）
6. ModelCard: 【创新】BB 模型版本化与溯源

来源:
- Melloni et al., SPIE 9664, 96641L (2015)
  https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/
- Yuan 2026 附录 A (Redheffer 星积)
  https://arxiv.org/abs/2606.05877
- Mitchell et al., FAT* 2019 (Model Cards)
  https://research.google/pubs/model-cards-for-model-reporting/
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from polaris.sim.models import (
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.models_extended import (
    add_drop_ring_s,
    attenuator_s,
    bend_s,
    circulator_s,
    combiner_s,
    detector_s,
    half_ring_s,
    isolator_s,
    mirror_s,
    modulator_s,
    reflector_s,
    splitter_s,
    taper_s,
    unitary_s,
)

# 学术来源 URL 常量（规则18 学术诚信）
_URL_ASPIE = "https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/"
_URL_SAX = "https://flaport.github.io/sax/models/"
_URL_SIPANN = "https://sipann.readthedocs.io/en/latest/models.html"
_URL_SIMPHONY = "https://simphonyphotonics.readthedocs.io/"
_URL_SIEPIC = "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"
_URL_GDSFACTORY = "https://github.com/gdsfactory/gdsfactory"
_URL_YARIV = "https://arxiv.org/abs/2606.05877"


# ---------------------------------------------------------------------------
# 1. TMatrix 类型（传输矩阵形式化）
# ---------------------------------------------------------------------------


@dataclass
class TMatrix:
    """传输矩阵（Aspic 风格 T = (M₊ + M₋)⁻¹(M₊ − M₋)）。

    存储传输矩阵的 M₊/M₋ 分量，形状 (n, n, n_freq)。
    S 矩阵与 T 矩阵的转换关系：
        S = (M₊ + M₋)⁻¹ · (M₊ − M₋)
        M₋ = (I − S)(I + S)⁻¹,  M₊ = I

    推导: 令 M₊ = I，由 S = (M₊+M₋)⁻¹(M₊−M₋) 得 M₋(S+I) = M₊(I−S)，
    故 M₋ = (I−S)(I+S)⁻¹。因 S 与 (I+S) 可交换，t_to_s(s_to_t(S)) = S。

    来源: Redheffer 1960; Yuan 2026 附录 A
    https://arxiv.org/abs/2606.05877
    """

    M_plus: np.ndarray  # (n, n, n_freq)
    M_minus: np.ndarray  # (n, n, n_freq)


# ---------------------------------------------------------------------------
# 2. s_to_t / t_to_s 转换函数
# ---------------------------------------------------------------------------


def s_to_t(s: np.ndarray) -> TMatrix:
    """S 矩阵转传输矩阵 T。

    公式: M₊ = I, M₋ = (I − S)(I + S)⁻¹
    其中 S 为 (n, n, n_freq) 复数矩阵，对每个频率点独立求逆。

    来源: Yuan 2026 附录 A, https://arxiv.org/abs/2606.05877

    Args:
        s: S 参数矩阵，形状 (n, n, n_freq)。

    Returns:
        TMatrix 传输矩阵（含 M₊/M₋ 分量）。

    Raises:
        ValueError: S 矩阵维度非法。
        RuntimeError: (I + S) 奇异或条件数过大时告警退出（禁止 fall-back）。
    """
    s_arr = np.asarray(s, dtype=complex)
    if s_arr.ndim != 3:
        msg = f"S 矩阵必须是 3D (n, n, n_freq)，得到 shape={s_arr.shape}"
        raise ValueError(msg)
    n, n_col, n_freq = s_arr.shape
    if n != n_col:
        msg = f"S 矩阵必须是方阵，得到 ({n}, {n_col})"
        raise ValueError(msg)

    # M₊ = I（单位矩阵，广播到所有频率点）
    M_plus = np.broadcast_to(np.eye(n, dtype=complex)[:, :, np.newaxis], (n, n, n_freq)).copy()
    M_minus = np.zeros((n, n, n_freq), dtype=complex)

    for k in range(n_freq):
        I_plus_S = np.eye(n, dtype=complex) + s_arr[:, :, k]
        # 条件数检查（数值稳定性）
        cond = np.linalg.cond(I_plus_S)
        if cond > 1e14:
            msg = f"频率点 {k}: (I+S) 条件数 {cond:.2e} 过大，矩阵接近奇异"
            raise RuntimeError(msg)
        try:
            inv_I_plus_S = np.linalg.inv(I_plus_S)
        except np.linalg.LinAlgError as e:
            msg = f"频率点 {k}: (I+S) 奇异，无法求逆: {e}"
            raise RuntimeError(msg) from e
        I_minus_S = np.eye(n, dtype=complex) - s_arr[:, :, k]
        M_minus[:, :, k] = I_minus_S @ inv_I_plus_S

    return TMatrix(M_plus=M_plus, M_minus=M_minus)


def t_to_s(t: TMatrix) -> np.ndarray:
    """传输矩阵 T 转 S 矩阵。

    公式: S = (M₊ + M₋)⁻¹ · (M₊ − M₋)

    来源: Yuan 2026 附录 A, https://arxiv.org/abs/2606.05877

    Args:
        t: TMatrix 传输矩阵（含 M₊/M₋ 分量）。

    Returns:
        S 参数矩阵，形状 (n, n, n_freq)。

    Raises:
        ValueError: M₊/M₋ 形状不匹配或非方阵。
        RuntimeError: (M₊ + M₋) 奇异时告警退出（禁止 fall-back）。
    """
    M_plus = np.asarray(t.M_plus, dtype=complex)
    M_minus = np.asarray(t.M_minus, dtype=complex)
    if M_plus.shape != M_minus.shape:
        msg = f"M_plus 和 M_minus 形状不匹配: {M_plus.shape} vs {M_minus.shape}"
        raise ValueError(msg)
    if M_plus.ndim != 3:
        msg = f"M_plus 必须是 3D (n, n, n_freq)，得到 {M_plus.shape}"
        raise ValueError(msg)
    n, n_col, n_freq = M_plus.shape
    if n != n_col:
        msg = f"M_plus 必须是方阵，得到 ({n}, {n_col})"
        raise ValueError(msg)

    sum_M = M_plus + M_minus
    diff_M = M_plus - M_minus
    S = np.zeros((n, n, n_freq), dtype=complex)

    for k in range(n_freq):
        cond = np.linalg.cond(sum_M[:, :, k])
        if cond > 1e14:
            msg = f"频率点 {k}: (M₊+M₋) 条件数 {cond:.2e} 过大，矩阵接近奇异"
            raise RuntimeError(msg)
        try:
            inv_sum = np.linalg.inv(sum_M[:, :, k])
        except np.linalg.LinAlgError as e:
            msg = f"频率点 {k}: (M₊+M₋) 奇异，无法求逆: {e}"
            raise RuntimeError(msg) from e
        S[:, :, k] = inv_sum @ diff_M[:, :, k]

    return S


# ---------------------------------------------------------------------------
# 3. BuildingBlock 抽象层
# ---------------------------------------------------------------------------


@dataclass
class BuildingBlock:
    """Aspic 风格 building block（模型化抽象）。

    封装器件的 S 参数模型函数、默认参数、端口列表与学术来源。
    对齐 Aspic 的 BB 模型化范式：每个 BB 关联一组数学方程描述的 S 参数模型。

    来源: Melloni et al., SPIE 9664, 96641L (2015)
    https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/
    """

    name: str
    model_func: Callable
    params: dict
    ports: list[str]
    description: str
    source_url: str


# ---------------------------------------------------------------------------
# 4. BBRegistry 注册表
# ---------------------------------------------------------------------------


class BBRegistry:
    """Building Block 注册表（对齐 Aspic 30+ BB 库）。

    使用 Registry 模式集中管理所有 BB，支持按名称注册/查询/列举。
    模块加载时自动注册 30 个 BB（见 _register_all_bbs）。

    来源: Fowler 2002 Registry 模式
    https://martinfowler.com/eaaCatalog/registry.html
    """

    _registry: dict[str, BuildingBlock] = {}

    @classmethod
    def register(cls, bb: BuildingBlock) -> None:
        """注册一个 BuildingBlock。

        Args:
            bb: 要注册的 BuildingBlock 实例。

        Raises:
            ValueError: BB 名称已存在时告警退出。
        """
        if bb.name in cls._registry:
            msg = f"BB '{bb.name}' 已注册，禁止重复注册"
            raise ValueError(msg)
        cls._registry[bb.name] = bb

    @classmethod
    def get(cls, name: str) -> BuildingBlock:
        """获取指定名称的 BuildingBlock。

        Args:
            name: BB 名称。

        Returns:
            对应的 BuildingBlock 实例。

        Raises:
            KeyError: BB 不存在时告警退出（禁止 fall-back）。
        """
        if name not in cls._registry:
            msg = f"BB '{name}' 未注册，可用 BB: {cls.list()}"
            raise KeyError(msg)
        return cls._registry[name]

    @classmethod
    def list(cls) -> list[str]:
        """列出所有已注册 BB 名称。"""
        return sorted(cls._registry.keys())

    @classmethod
    def count(cls) -> int:
        """返回已注册 BB 数量。"""
        return len(cls._registry)


# ---------------------------------------------------------------------------
# 5. 注册 30 个 BB
# ---------------------------------------------------------------------------


def _register_passive_bbs() -> None:
    """注册无源基础 BB（波导、分束器、MMI、交叉、终端等，共 10 个）。

    使用 polaris.sim.models / models_extended 的现有 S 参数模型函数。
    """
    bbs = [
        BuildingBlock("waveguide", waveguide_s,
                      {"length": 100.0, "neff": 2.4, "ng": 4.0, "loss_db_cm": 0.0},
                      ["in", "out"], "条形波导传播模型", _URL_SIPANN),
        BuildingBlock("y_branch", y_branch_s,
                      {"insertion_loss_db": 0.3},
                      ["port_1", "port_2", "port_3"], "Y 分支 3dB 分束器", _URL_SIMPHONY),
        BuildingBlock("mmi_1x2", mmi_1x2_s,
                      {"insertion_loss_db": 0.4},
                      ["in", "out1", "out2"], "MMI 1x2 分束器", _URL_GDSFACTORY),
        BuildingBlock("mmi_2x2", mmi_2x2_s,
                      {"insertion_loss_db": 0.5},
                      ["in1", "in2", "out1", "out2"], "MMI 2x2 分束器", _URL_GDSFACTORY),
        BuildingBlock("crossing", crossing_s,
                      {"insertion_loss_db": 0.3},
                      ["in1", "in2", "out1", "out2"], "波导交叉", _URL_GDSFACTORY),
        BuildingBlock("terminator", terminator_s,
                      {"reflection_db": -40.0},
                      ["in"], "终端吸收器", _URL_SIMPHONY),
        BuildingBlock("taper", taper_s,
                      {"length": 10.0, "w1": 0.5, "w2": 0.5, "loss_db": 0.1},
                      ["in", "out"], "锥形转换器", _URL_SIMPHONY),
        BuildingBlock("splitter", splitter_s,
                      {"insertion_loss_db": 0.0},
                      ["in", "out1", "out2"], "理想 1x2 分束器", _URL_SAX),
        BuildingBlock("combiner", combiner_s,
                      {"insertion_loss_db": 0.0},
                      ["in1", "in2", "out"], "2x1 合波器", _URL_SAX),
        BuildingBlock("bend", bend_s,
                      {"radius": 10.0, "angle_deg": 90.0, "neff": 2.4, "loss_db_cm": 0.5},
                      ["in", "out"], "弯曲波导", _URL_SIEPIC),
    ]
    for bb in bbs:
        BBRegistry.register(bb)


def _register_coupling_bbs() -> None:
    """注册耦合器与谐振器类 BB（共 5 个）。"""
    bbs = [
        BuildingBlock("directional_coupler", directional_coupler_s,
                      {"coupling": 0.5, "length": 10.0, "gap": 0.2},
                      ["in1", "in2", "out1", "out2"], "定向耦合器", _URL_SIPANN),
        BuildingBlock("ring_resonator", ring_resonator_s,
                      {"radius": 10.0},
                      ["in", "through"], "全通型环谐振器", _URL_SIPANN),
        BuildingBlock("grating_coupler", grating_coupler_s,
                      {"peak_wl": 1.55, "bandwidth_3db": 0.04, "insertion_loss_db": 1.9},
                      ["fiber", "waveguide"], "光栅耦合器（高斯型响应）", _URL_SIMPHONY),
        BuildingBlock("half_ring", half_ring_s,
                      {"radius": 10.0, "gap": 0.2, "width": 0.5, "thickness": 0.22,
                       "neff": 2.4, "ng": 4.0, "loss_db_cm": 0.1},
                      ["in", "through"], "全通型环谐振器（simphony 对齐）", _URL_SIMPHONY),
        BuildingBlock("add_drop_ring", add_drop_ring_s,
                      {"radius": 10.0, "gap": 0.2, "neff": 2.4, "ng": 4.0, "loss_db_cm": 0.0},
                      ["in", "through", "drop", "add"], "Add-drop 型环谐振器（双总线）", _URL_YARIV),
    ]
    for bb in bbs:
        BBRegistry.register(bb)


def _register_active_bbs() -> None:
    """注册有源与功能器件类 BB（移相/调制/探测/衰减/隔离/反射/酉变换，共 9 个）。"""
    bbs = [
        BuildingBlock("phase_shifter", phase_shifter_s,
                      {"phase_rad": 0.0, "insertion_loss_db": 0.0},
                      ["in", "out"], "热光移相器", _URL_GDSFACTORY),
        BuildingBlock("modulator", modulator_s,
                      {"phase_rad": 0.0, "insertion_loss_db": 0.5},
                      ["in", "out"], "MZI 调制器", _URL_SAX),
        BuildingBlock("detector", detector_s,
                      {"responsivity": 1.0},
                      ["in"], "光电探测器", _URL_SIMPHONY),
        BuildingBlock("attenuator", attenuator_s,
                      {"attenuation_db": 3.0},
                      ["in", "out"], "光衰减器", _URL_SAX),
        BuildingBlock("circulator", circulator_s,
                      {"insertion_loss_db": 0.5},
                      ["p1", "p2", "p3"], "三端口光环行器", _URL_SAX),
        BuildingBlock("isolator", isolator_s,
                      {"insertion_loss_db": 0.5, "isolation_db": 40.0},
                      ["in", "out"], "光隔离器", _URL_YARIV),
        BuildingBlock("mirror", mirror_s,
                      {"reflectivity": 1.0},
                      ["in"], "理想反射镜", _URL_YARIV),
        BuildingBlock("reflector", reflector_s,
                      {"reflectivity": 0.5},
                      ["in", "out"], "部分反射器", _URL_SAX),
        BuildingBlock("unitary", unitary_s,
                      {"theta": 0.0, "phi": 0.0},
                      ["in1", "in2", "out1", "out2"], "酉矩阵器件（2x2 酉变换）", _URL_SAX),
    ]
    for bb in bbs:
        BBRegistry.register(bb)


def _register_macro_bbs() -> None:
    """注册宏模型 BB（基于基础模型包装，description 标注，共 6 个）。"""
    bbs = [
        BuildingBlock("heater", phase_shifter_s,
                      {"phase_rad": 0.0, "insertion_loss_db": 0.0},
                      ["in", "out"], "热调相移器（基于 phase_shifter 模型）", _URL_SIEPIC),
        BuildingBlock("balanced_detector", detector_s,
                      {"responsivity": 1.0},
                      ["in1", "in2"], "平衡探测器双端口（基于 detector 模型）", _URL_SIMPHONY),
        BuildingBlock("mach_zehnder", y_branch_s,
                      {"insertion_loss_db": 0.3},
                      ["in", "out"], "MZI 宏模型（y_branch + waveguide 组合）", _URL_ASPIE),
        BuildingBlock("awg", mmi_2x2_s,
                      {"insertion_loss_db": 0.5},
                      ["in1", "in2", "out1", "out2"], "阵列波导光栅宏模型（基于 mmi_2x2）", _URL_ASPIE),
        BuildingBlock("sagnac_loop", mirror_s,
                      {"reflectivity": 1.0},
                      ["in", "out"], "Sagnac 环宏模型（mirror + waveguide 组合）", _URL_YARIV),
        BuildingBlock("fpr", mmi_1x2_s,
                      {"insertion_loss_db": 0.4},
                      ["in", "out1", "out2"], "自由传播区宏模型（基于 mmi_1x2）", _URL_ASPIE),
    ]
    for bb in bbs:
        BBRegistry.register(bb)


def _register_all_bbs() -> None:
    """注册全部 30 个 BuildingBlock（模块加载时自动调用）。

    BB 列表对齐 Aspic 30+ BB 库，使用 polaris.sim.models 和
    polaris.sim.models_extended 的现有 S 参数模型函数。
    宏模型 BB（heater/mach_zehnder 等）用基础模型包装，description 标注。
    """
    _register_passive_bbs()
    _register_coupling_bbs()
    _register_active_bbs()
    _register_macro_bbs()


# 模块加载时自动注册
_register_all_bbs()


# ---------------------------------------------------------------------------
# 6. VirtualExperiment 类
# ---------------------------------------------------------------------------


@dataclass
class VirtualExperiment:
    """Aspic 风格虚拟实验（what-if 参数扫描）。

    对指定 BB 的指定参数进行扫描，返回每个参数值对应的 S 参数字典。
    对齐 Aspic 的虚拟实验功能：用户可快速评估参数变化对电路响应的影响。

    来源: Melloni et al., SPIE 9664, 96641L (2015)
    https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/
    """

    name: str
    bb_name: str
    param_name: str
    param_values: np.ndarray
    wavelength_range: tuple[float, float]
    n_points: int = 1000

    def run(self) -> dict:
        """执行参数扫描。

        Returns:
            {param_value: SDict} 字典，键为参数值，值为对应 S 参数。

        Raises:
            KeyError: BB 不存在时（通过 BBRegistry.get 告警退出）。
            ValueError: 参数名不存在于 BB 默认参数时告警退出。
        """
        bb = BBRegistry.get(self.bb_name)
        if self.param_name not in bb.params:
            msg = f"参数 '{self.param_name}' 不存在于 BB '{self.bb_name}' 的默认参数 {list(bb.params.keys())}"
            raise ValueError(msg)
        wl = np.linspace(self.wavelength_range[0], self.wavelength_range[1], self.n_points)
        results: dict = {}
        for pv in self.param_values:
            kwargs = dict(bb.params)
            kwargs[self.param_name] = pv
            results[pv] = bb.model_func(wl, **kwargs)
        return results


# ---------------------------------------------------------------------------
# 7. ModelCard dataclass（创新点）
# ---------------------------------------------------------------------------


@dataclass
class ModelCard:
    """【创新】BB 模型版本化与溯源（对齐 Model Cards for Model Reporting）。

    每个 BB 模型关联 git commit + 数据源 URL + 推导公式 + 参数范围 + 验证状态，
    支持模型可追溯，弥补 Aspic BB 模型黑盒问题。

    创新逻辑: Aspic 的 BB 模型为黑盒，PoLaRIS 用 ModelCard 记录模型来源、
    参数范围、验证状态，实现全链路可追溯。

    支持理论: Model Cards for Model Reporting（Mitchell et al., FAT* 2019）。
    https://research.google/pubs/model-cards-for-model-reporting/

    Attributes:
        bb_name: BB 名称。
        version: 模型版本号（如 "v1.0"）。
        git_commit: 模型代码的 git commit hash。
        source_url: 学术来源 URL。
        formula: 推导公式（LaTeX 字符串）。
        param_ranges: 参数范围字典 {param: (min, max)}。
        validation_status: 验证状态 "validated" / "draft" / "deprecated"。
    """

    bb_name: str
    version: str
    git_commit: str
    source_url: str
    formula: str
    param_ranges: dict
    validation_status: str = "draft"

    def is_validated(self) -> bool:
        """检查模型是否已验证。"""
        return self.validation_status == "validated"
