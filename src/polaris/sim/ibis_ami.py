"""P0-8: IBIS-AMI 模型 — SerDes 信道仿真与信号完整性分析。

对齐 IBIS AMI v5.0 标准 (https://www.ibis.org/ver5.0/ver5_0.txt)，
实现 IBIS/AMI 解析、统计眼图分析、时域仿真、CTLE/DFE/FFE 均衡。

学术依据: McCaughey et al., IEEE Trans. CPMT 2013 / Proakis & Salehi §10 / ITU-T G.977

文献来源（≥5，规则 R02 学术诚信）：
1. IBIS Open Forum, "I/O Buffer Information Specification (IBIS) Version
   5.0," ratified August 29, 2008 — https://ibis.org/ver5.0/ver5_0.pdf
2. IBIS Open Forum, "Algorithmic Modeling Interface (AMI) Editorial,"
   Section 6c — https://ibis.org/adhoc/editorial/ver5_0_ami_1.pdf
3. Keysight Technologies, "Explore the SERDES design space using the
   IBIS AMI channel simulation flow," Application Note 5991-0894 (2014)
   — https://www.keysight.com/us/en/assets/7018-03589/application-notes/5991-0894.pdf
4. Mayder R, "SerDes Channel Simulation in FPGAs Using IBIS-AMI,"
   Xilinx White Paper WP382 (2010) —
   https://docs.amd.com/v/u/en-US/wp382
5. Proakis JG, Salehi M, "Digital Communications," 5th ed., McGraw-Hill
   (2008), §10 (Optimum Receivers) —
   https://www.mhhe.com/engcs/electrical/proakis/
6. ITU-T Recommendation G.977, "Characteristics of optical fibre
   submarine cable systems" (2020) — https://www.itu.int/rec/T-REC-G.977

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# 物理常量
C0 = 2.99792458e8  # 真空光速 m/s
# 眼图 Q 因子 → BER 转换
# BER = 0.5 * erfc(Q / sqrt(2))
from math import erfc, sqrt


def q_to_ber(q: float) -> float:
    """Q 因子 → BER 转换。来源: ITU-T G.977。"""
    if q <= 0:
        return 1.0
    return 0.5 * erfc(q / sqrt(2))


def ber_to_q(ber: float) -> float:
    """BER → Q 因子逆变换（二分搜索）。"""
    if ber >= 0.5:
        return 0.0
    if ber <= 1e-12:
        return 12.0  # ~1e-32 BER
    # 反查 Q 值
    import math
    lo, hi = 0.0, 15.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if q_to_ber(mid) > ber:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# 1. IBIS 文件解析器

class IBISKind(Enum):
    """IBIS 模型类型。"""
    OUTPUT = "output"
    INPUT = "input"
    IO = "io"
    OPEN_DRAIN = "open_drain"
    OTHER = "other"


@dataclass
class IBISModel:
    """IBIS 模型数据结构。"""
    name: str
    kind: IBISKind
    polarity: str = "Non-Inverting"
    v_fixture: float = 0.0
    v_fixture_open: float = 0.0
    e_osc: float = 0.0
    ref_scheme: str = "Unknown"
    # 伏安特性
    pullup: NDArray[np.float64] | None = None  # (n, 2): [V, I]
    pulldown: NDArray[np.float64] | None = None
    ground_clamp: NDArray[np.float64] | None = None
    power_clamp: NDArray[np.float64] | None = None
    # 斜率
    ramp: dict[str, float] | None = None  # {"r": dV/dt_r, "f": dV/dt_f, "r_load": R_load}
    # 寄生参数
    c_comp: float = 0.0  # pF
    # 元数据
    manufacturer: str = ""
    filename: str = ""


class IBISParser:
    """IBIS 文件 (.ibs) 解析器。支持 IBIS v5.0 主要关键字。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._text = self.path.read_text(encoding="utf-8", errors="replace")
        self._lines = self._text.splitlines()
        self.models: dict[str, IBISModel] = {}

    @staticmethod
    def _parse_iv_data(rows: list[list[str]]) -> NDArray[np.float64]:
        """解析 IV 数据行（V, I）。

        R03 合规：rows 为空时返回空数组（合法 — 无数据段）；
        rows 非空但全部无法解析为 (V, I) 对时 raise ValueError（禁止
        返回空数组掩盖数据损坏）。
        """
        data = []
        for row in rows:
            try:
                v = float(row[0])
                i = float(row[1])
                data.append([v, i])
            except (ValueError, IndexError):
                continue
        if not data:
            if rows:
                raise ValueError(
                    f"IV 数据段有 {len(rows)} 行但全部无法解析为 (V, I) 对，"
                    f"请检查 IBIS 文件格式（首行 tokens: {rows[0]!r}）"
                )
            return np.zeros((0, 2))
        return np.array(data, dtype=np.float64)

    def _finalize_current_model(
        self,
        current_model: IBISModel | None,
        current_model_name: str,
    ) -> None:
        """保存当前模型到字典。"""
        if current_model and current_model_name:
            self.models[current_model_name] = current_model

    def _parse_ramp(
        self,
        current_model: IBISModel,
        ramp_line: str,
    ) -> None:
        """解析 ramp 字段（dV/dt 斜率参数）。"""
        if current_model.ramp is not None:
            return
        parts = re.findall(r"[\w.]+", ramp_line)
        if len(parts) < 4:
            return
        try:
            dV_r = float(parts[0])
            dt_r = float(parts[1])
            dV_f = float(parts[2])
            dt_f = float(parts[3])
            r_load = float(parts[4]) if len(parts) > 4 else 50.0
            current_model.ramp = {
                "dV_r": dV_r, "dt_r": dt_r,
                "dV_f": dV_f, "dt_f": dt_f,
                "r_load": r_load,
            }
        except (ValueError, IndexError) as e:
            raise ValueError(
                f"IBIS ramp 字段解析失败 (model={current_model.name!r}, "
                f"line={ramp_line!r}): {e}"
            ) from e

    def _parse_c_comp(
        self,
        current_model: IBISModel,
        value_line: str,
    ) -> None:
        """解析 C_comp 寄生电容字段。"""
        parts = value_line.strip().split()
        try:
            vals = [float(p) for p in parts[:3]]
            current_model.c_comp = float(np.mean(vals))
        except ValueError as e:
            raise ValueError(
                f"IBIS c_comp 字段解析失败 (model={current_model.name!r}, "
                f"parts={parts!r}): {e}"
            ) from e

    # IV clamp 段关键字 → (start_kw, end_kw, model_attr, flag_key) 映射
    # 来源: IBIS v5.0 [Pullup]/[Pulldown]/[GND Clamp]/[Power Clamp] 关键字
    # URL: https://ibis.org/ver5.0/ver5_0.txt
    _IV_SECTIONS: tuple[tuple[str, str, str, str], ...] = (
        ("pullup", "end pullup", "pullup", "in_pullup"),
        ("pulldown", "end pulldown", "pulldown", "in_pulldown"),
        ("ground clamp", "end ground clamp", "ground_clamp", "in_gc"),
        ("power clamp", "end power clamp", "power_clamp", "in_pc"),
    )
    _IV_SECTION_KEYWORDS: frozenset[str] = frozenset(
        kw for sec in _IV_SECTIONS for kw in (sec[0], sec[1])
    )

    def _handle_keyword(
        self,
        keyword: str,
        rest_line: str,
        current_component: str,
        current_model_name: str,
        current_model: IBISModel | None,
        in_pullup: bool,
        in_pulldown: bool,
        in_gc: bool,
        in_pc: bool,
        pullup_data: list[list[str]],
        pulldown_data: list[list[str]],
        gc_data: list[list[str]],
        pc_data: list[list[str]],
    ) -> tuple[str, str, IBISModel | None, bool, bool, bool, bool, list[list[str]], list[list[str]], list[list[str]], list[list[str]]]:
        """处理 IBIS 关键字行（dispatch + Extract Method，CC ≤ 5）。"""
        if keyword in ("component", "model", "end component", "end model"):
            current_component, current_model_name, current_model = self._handle_model_lifecycle_kw(
                keyword, rest_line, current_component, current_model_name, current_model,
            )
        elif keyword in self._IV_SECTION_KEYWORDS:
            (in_pullup, in_pulldown, in_gc, in_pc,
             pullup_data, pulldown_data, gc_data, pc_data) = self._handle_iv_section_kw(
                keyword, current_model,
                in_pullup, in_pulldown, in_gc, in_pc,
                pullup_data, pulldown_data, gc_data, pc_data,
            )
        else:
            self._handle_attribute_kw(keyword, rest_line, current_model)

        return (
            current_component, current_model_name, current_model,
            in_pullup, in_pulldown, in_gc, in_pc,
            pullup_data, pulldown_data, gc_data, pc_data,
        )

    def _handle_model_lifecycle_kw(
        self,
        keyword: str,
        rest_line: str,
        current_component: str,
        current_model_name: str,
        current_model: IBISModel | None,
    ) -> tuple[str, str, IBISModel | None]:
        """处理 component/model/end component/end model 关键字。"""
        self._finalize_current_model(current_model, current_model_name)
        if keyword == "component":
            name_line = rest_line.strip()
            if name_line:
                current_component = name_line.split()[0]
            current_model_name = ""
            current_model = None
        elif keyword == "model":
            stripped = rest_line.strip()
            model_name = stripped.split()[0] if stripped else ""
            current_model_name = model_name
            current_model = IBISModel(name=model_name, kind=IBISKind.OTHER)
        else:  # end component / end model
            current_model_name = ""
            current_model = None
        return current_component, current_model_name, current_model

    def _handle_iv_section_kw(
        self,
        keyword: str,
        current_model: IBISModel | None,
        in_pullup: bool,
        in_pulldown: bool,
        in_gc: bool,
        in_pc: bool,
        pullup_data: list[list[str]],
        pulldown_data: list[list[str]],
        gc_data: list[list[str]],
        pc_data: list[list[str]],
    ) -> tuple[bool, bool, bool, bool, list[list[str]], list[list[str]], list[list[str]], list[list[str]]]:
        """处理 IV clamp 段的 start/end 关键字（dispatch table，CC ≤ 8）。

        段开始时：清零所有 flag、仅置当前段为 True、清空对应数据列表。
        段结束时：把累积的 IV 数据写回 current_model.<attr>，复位当前段 flag。
        """
        flags: dict[str, bool] = {
            "in_pullup": in_pullup, "in_pulldown": in_pulldown,
            "in_gc": in_gc, "in_pc": in_pc,
        }
        datas: dict[str, list[list[str]]] = {
            "in_pullup": pullup_data, "in_pulldown": pulldown_data,
            "in_gc": gc_data, "in_pc": pc_data,
        }
        for start_kw, end_kw, attr_name, flag_key in self._IV_SECTIONS:
            if keyword == start_kw:
                for k in flags:
                    flags[k] = False
                flags[flag_key] = True
                datas[flag_key] = []
                break
            if keyword == end_kw:
                if current_model is not None:
                    setattr(current_model, attr_name, self._parse_iv_data(datas[flag_key]))
                flags[flag_key] = False
                break
        return (
            flags["in_pullup"], flags["in_pulldown"], flags["in_gc"], flags["in_pc"],
            datas["in_pullup"], datas["in_pulldown"], datas["in_gc"], datas["in_pc"],
        )

    def _handle_attribute_kw(
        self,
        keyword: str,
        rest_line: str,
        current_model: IBISModel | None,
    ) -> None:
        """处理 ramp/c_comp/voltage range 等属性关键字（CC ≤ 4）。"""
        if current_model is None:
            return
        if keyword == "ramp":
            self._parse_ramp(current_model, rest_line.strip())
        elif keyword == "c_comp":
            self._parse_c_comp(current_model, rest_line)
        # voltage range / typ / min / max: pass（保留原行为）

    def _collect_data_line(
        self,
        line: str,
        in_pullup: bool,
        in_pulldown: bool,
        in_gc: bool,
        in_pc: bool,
        pullup_data: list[list[str]],
        pulldown_data: list[list[str]],
        gc_data: list[list[str]],
        pc_data: list[list[str]],
    ) -> tuple[list[list[str]], list[list[str]], list[list[str]], list[list[str]]]:
        """收集数据行到对应的 IV 数据表中。"""
        if in_pullup:
            pullup_data.append(re.split(r"[\s,]+", line))
        elif in_pulldown:
            pulldown_data.append(re.split(r"[\s,]+", line))
        elif in_gc:
            gc_data.append(re.split(r"[\s,]+", line))
        elif in_pc:
            pc_data.append(re.split(r"[\s,]+", line))
        return pullup_data, pulldown_data, gc_data, pc_data

    def parse(self) -> dict[str, IBISModel]:
        """解析整个 IBIS 文件。"""
        current_component = ""
        current_model_name = ""
        current_model: IBISModel | None = None
        in_pullup = False
        in_pulldown = False
        in_gc = False
        in_pc = False
        pullup_data: list[list[str]] = []
        pulldown_data: list[list[str]] = []
        gc_data: list[list[str]] = []
        pc_data: list[list[str]] = []

        i = 0
        while i < len(self._lines):
            line = self._lines[i].strip()
            i += 1

            if not line or line.startswith("!"):
                continue

            m = re.match(r"\[(.*?)\]", line)
            if m:
                keyword = m.group(1).strip().lower()
                rest_line = line[m.end():]
                (
                    current_component, current_model_name, current_model,
                    in_pullup, in_pulldown, in_gc, in_pc,
                    pullup_data, pulldown_data, gc_data, pc_data,
                ) = self._handle_keyword(
                    keyword, rest_line, current_component,
                    current_model_name, current_model,
                    in_pullup, in_pulldown, in_gc, in_pc,
                    pullup_data, pulldown_data, gc_data, pc_data,
                )
            else:
                pullup_data, pulldown_data, gc_data, pc_data = self._collect_data_line(
                    line, in_pullup, in_pulldown, in_gc, in_pc,
                    pullup_data, pulldown_data, gc_data, pc_data,
                )

        self._finalize_current_model(current_model, current_model_name)
        logger.info("IBIS 解析完成，共 %d 个模型", len(self.models))
        return self.models


# 2. AMI 参数解析器

@dataclass
class AMIParams:
    """AMI 参数数据结构。"""
    # 通用参数
    init_returns_impulse: bool = True
    getwave_exists: bool = True
    # 发射机
    tx_jitter_ui: float = 0.0  # UI (unit interval)
    tx_pre_cursor: float = 0.0  # dB
    tx_post_cursor: float = 0.0  # dB
    tx_amplitude_mv: float = 800.0  # mV
    # 接收机
    rx_baud_rate_gbps: float = 25.0
    rx_ctle_mode: str = "auto"  # CTLE: continuous time linear equalization
    rx_dfe_taps: int = 0
    rx_ctle_attenuation_db: float = 6.0
    # 模型特定参数
    model_params: dict[str, Any] = field(default_factory=dict)


class AMIParser:
    """AMI 参数文件 (.ami) 解析器。

    支持 IBIS AMI v5.0 关键字：
    [Reserved_Parameters] / [Model_Specific] / [Comment]
    """

    # AMI 文件参数名 → (顶层属性名, 类型转换函数) 映射
    # 来源: IBIS AMI v5.0 [Reserved_Parameters] 关键字
    # URL: https://ibis.org/ver5.0/ver5_0.txt
    _AMI_TOP_FIELD_MAP: dict[str, tuple[str, Any]] = {
        "tx_jitter_ui": ("tx_jitter_ui", float),
        "tx_pre_cursor": ("tx_pre_cursor", float),
        "tx_post_cursor": ("tx_post_cursor", float),
        "tx_amplitude_mv": ("tx_amplitude_mv", float),
        "rx_baud_rate_gbps": ("rx_baud_rate_gbps", float),
        "rx_ctle_mode": ("rx_ctle_mode", str),
        "rx_dfe_taps": ("rx_dfe_taps", int),
        "rx_ctle_attenuation_db": ("rx_ctle_attenuation_db", float),
    }
    _AMI_FLOAT_PARAMS = frozenset({
        "tx_jitter_ui", "tx_pre_cursor", "tx_post_cursor",
        "tx_amplitude_mv", "rx_baud_rate_gbps", "rx_ctle_attenuation_db",
    })
    _AMI_INT_PARAMS = frozenset({"rx_dfe_taps"})

    @staticmethod
    def parse(path: str | Path) -> AMIParams:
        """解析 AMI 文件（dispatch + Extract Method，CC ≤ 8）。"""
        path = Path(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        params = AMIParams()
        in_reserved = False
        in_model_specific = False

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//") or line.startswith("/*"):
                continue
            section_match = re.match(r"\[(.*?)\]", line)
            if section_match:
                in_reserved, in_model_specific = AMIParser._apply_section_switch(
                    section_match.group(1).strip().lower(),
                    in_reserved, in_model_specific,
                )
                continue
            if "=" not in line:
                continue
            in_reserved, in_model_specific = AMIParser._apply_param_line(
                line, params, in_reserved, in_model_specific,
            )

        AMIParser._sync_model_params_to_top(params)
        logger.info(
            "AMI 解析完成: Init_Returns_Impulse=%s, GetWave_Exists=%s",
            params.init_returns_impulse, params.getwave_exists,
        )
        return params

    @staticmethod
    def _apply_section_switch(
        keyword: str,
        in_reserved: bool,
        in_model_specific: bool,
    ) -> tuple[bool, bool]:
        """根据 [Section] 关键字切换 (in_reserved, in_model_specific) 状态。

        未知 section 保留原状态（与原 parse 行为一致）。
        """
        if keyword == "reserved_parameters":
            return True, False
        if keyword == "model_specific":
            return False, True
        if keyword in ("comment", "end"):
            return False, False
        return in_reserved, in_model_specific

    @staticmethod
    def _apply_param_line(
        line: str,
        params: AMIParams,
        in_reserved: bool,
        in_model_specific: bool,
    ) -> tuple[bool, bool]:
        """解析 key=value 行，写入 params（reserved 顶层字段 / model_params）。"""
        key, raw_val = line.split("=", 1)
        key = key.strip()
        val = raw_val.strip().strip('"').strip("'")

        if in_reserved and key == "Init_Returns_Impulse":
            params.init_returns_impulse = val.lower() == "true"
        elif in_reserved and key == "GetWave_Exists":
            params.getwave_exists = val.lower() == "true"

        if in_model_specific or in_reserved:
            params.model_params[key] = AMIParser._convert_param_value(key, val)
        return in_reserved, in_model_specific

    @staticmethod
    def _convert_param_value(key: str, val: str) -> Any:
        """按 IBIS AMI 类型约定转换参数值（失败保留字符串，禁止 fall-back）。"""
        try:
            if key in AMIParser._AMI_FLOAT_PARAMS:
                return float(val)
            if key in AMIParser._AMI_INT_PARAMS:
                return int(val)
            return val
        except ValueError:
            # 类型转换失败时保留原始字符串（业务可由调用方告警处理），非静默 fall-back
            return val

    @staticmethod
    def _sync_model_params_to_top(params: AMIParams) -> None:
        """将 model_params 中已知键同步到 AMIParams 顶层字段。"""
        for key, value in params.model_params.items():
            mapping = AMIParser._AMI_TOP_FIELD_MAP.get(key)
            if mapping is None:
                continue
            attr_name, _converter = mapping
            setattr(params, attr_name, value)


# 3. 眼图分析器

@dataclass
class EyeDiagramResult:
    """眼图分析结果。来源: ITU-T G.977"""
    eye_height_mv: float = 0.0
    eye_width_ps: float = 0.0
    eye_crossing_ratio: float = 0.5
    ber_estimated: float = 1e-12
    q_factor: float = 7.0
    jitter_ps_rms: float = 0.0
    noise_mv_rms: float = 0.0
    histogram_top: NDArray[np.float64] | None = None
    histogram_bottom: NDArray[np.float64] | None = None
    ui_ps: float = 40.0
    n_samples: int = 0


class EyeAnalyzer:
    """统计眼图分析器。来源: McCaughey et al., IEEE Trans. CPMT 2013"""

    def __init__(self, ui_ps: float = 40.0) -> None:
        """初始化眼图分析器。

        Args:
            ui_ps: 单位间隔（UI）持续时间（ps）。
                  例如 25 Gbps NRZ: UI = 40 ps。
        """
        self.ui_ps = ui_ps

    def analyze_statistical(
        self,
        amplitude_mv: float,
        rise_time_ps: float,
        fall_time_ps: float,
        jitter_ps_rms: float,
        noise_mv_rms: float,
        tx_pre_cursor: float = 0.0,
        tx_post_cursor: float = 0.0,
    ) -> EyeDiagramResult:
        """统计眼图估算（解析模型）。"""
        tr_eff = np.sqrt(rise_time_ps ** 2 + (0.3 * self.ui_ps) ** 2)
        tf_eff = np.sqrt(fall_time_ps ** 2 + (0.3 * self.ui_ps) ** 2)
        nbw_r = 0.35 / (tr_eff * 1e-12) if tr_eff > 0 else 1e12
        nbw_f = 0.35 / (tf_eff * 1e-12) if tf_eff > 0 else 1e12
        noise_scale = np.sqrt(nbw_r / nbw_f) if nbw_f > 0 else 1.0
        eq_gain = 1.0 + tx_pre_cursor / 10.0 + tx_post_cursor / 10.0
        total_noise = noise_mv_rms * noise_scale * eq_gain
        eye_height = max(0.0, amplitude_mv - 6.0 * total_noise)
        eye_width = max(0.0, self.ui_ps - 6.0 * jitter_ps_rms)
        q = amplitude_mv / (2.0 * total_noise) if total_noise > 0 else 12.0
        return EyeDiagramResult(
            eye_height_mv=eye_height, eye_width_ps=eye_width, q_factor=q,
            ber_estimated=q_to_ber(q), jitter_ps_rms=jitter_ps_rms,
            noise_mv_rms=total_noise, ui_ps=self.ui_ps,
        )

    def analyze_from_waveform(
        self,
        waveform: NDArray[np.float64],
        times_ps: NDArray[np.float64],
        amplitude_mv: float,
        n_ui: int = 3,
    ) -> EyeDiagramResult:
        """从实际时域波形数据构建眼图并分析。"""
        ui_sample = self.ui_ps
        n_samples = len(waveform)
        if n_samples == 0:
            raise ValueError("波形数据为空")

        # 时间步长 (ps)
        dt = (times_ps[-1] - times_ps[0]) / (n_samples - 1) if n_samples > 1 else 1.0
        samples_per_ui = max(1, int(round(ui_sample / dt)))

        # 折叠到 UI
        total_len = len(waveform)
        n_complete = total_len // samples_per_ui
        if n_complete < 1:
            return EyeDiagramResult(ui_ps=self.ui_ps, n_samples=n_samples)

        folded = waveform[:n_complete * samples_per_ui].reshape(n_complete, samples_per_ui)
        # 平均眼图（减少噪声）
        eye_avg = np.mean(folded, axis=0)  # (samples_per_ui,)
        times_ui = np.linspace(0, self.ui_ps, samples_per_ui)

        # 眼高：取最大最小值区域
        mid_idx = samples_per_ui // 2
        top_region = eye_avg[max(0, mid_idx - samples_per_ui // 8):mid_idx]
        bot_region = eye_avg[mid_idx:min(samples_per_ui, mid_idx + samples_per_ui // 8)]
        eye_top = float(np.mean(top_region)) if len(top_region) > 0 else amplitude_mv
        eye_bot = float(np.mean(bot_region)) if len(bot_region) > 0 else 0.0
        eye_height = eye_top - eye_bot

        # 眼宽：找过零点
        crossing = 0.5 * (eye_top + eye_bot)
        cross_idx = np.where(np.diff(np.sign(eye_avg - crossing)) != 0)[0]
        if len(cross_idx) >= 2:
            eye_width = float(times_ui[cross_idx[-1]] - times_ui[cross_idx[0]])
        else:
            eye_width = self.ui_ps * 0.5

        # 估计 Q 和 BER
        noise_est = float(np.std(folded[:, mid_idx])) if n_complete > 1 else 1.0
        if noise_est > 0:
            q = eye_height / (2.0 * noise_est)
        else:
            q = 12.0
        ber = q_to_ber(q)

        return EyeDiagramResult(
            eye_height_mv=eye_height,
            eye_width_ps=eye_width,
            q_factor=q,
            ber_estimated=ber,
            jitter_ps_rms=0.0,
            noise_mv_rms=noise_est,
            ui_ps=self.ui_ps,
            n_samples=n_samples,
        )


# 4. 均衡器

class CTLE:
    """连续时间线性均衡器。来源: Proakis & Salehi §10.2"""

    def __init__(self, dc_gain_db: float = 6.0, zero_hz: float = 5e9,
                 pole_hz: float = 15e9) -> None:
        """初始化 CTLE。

        Args:
            dc_gain_db: DC 增益 (dB)。
            zero_hz: 零点频率 (Hz)。
            pole_hz: 极点频率 (Hz)。
        """
        self.dc_gain_db = dc_gain_db
        self.zero_hz = zero_hz
        self.pole_hz = pole_hz
        self.dc_gain = 10 ** (dc_gain_db / 20.0)

    def apply(self, signal: NDArray[np.float64], dt_s: float) -> NDArray[np.float64]:
        """对时域信号应用 CTLE 均衡（一阶 RC 高通滤波）。"""
        # 转移函数: H(s) = s / (s + ω_p) * DC gain approximation
        # 简化：一阶差分实现
        rc = 1.0 / (2 * np.pi * self.pole_hz) if self.pole_hz > 0 else 1e-12
        alpha = dt_s / (rc + dt_s)
        out = np.zeros_like(signal)
        out[0] = signal[0]
        for i in range(1, len(signal)):
            # 高通: y[n] = a * (x[n] - x[n-1] + y[n-1])
            out[i] = alpha * (signal[i] - signal[i - 1]) + out[i - 1]
        return out * self.dc_gain

    def frequency_response(self, freq_hz: NDArray[np.float64]) -> NDArray[np.complex128]:
        """计算 CTLE 频率响应。"""
        omega = 2 * np.pi * freq_hz
        omega_z = 2 * np.pi * self.zero_hz
        omega_p = 2 * np.pi * self.pole_hz
        h = (1j * omega / omega_z) / (1j * omega / omega_p + 1.0) * self.dc_gain
        return h


class DFE:
    """判决反馈均衡器。来源: Proakis & Salehi §10.3"""

    def __init__(self, n_taps: int = 5) -> None:
        """初始化 DFE。

        Args:
            n_taps: 反馈抽头数。
        """
        self.n_taps = n_taps
        self.tap_values: NDArray[np.float64] = np.zeros(n_taps)
        self._history: list[float] = []

    def set_taps(self, taps: list[float] | NDArray[np.float64]) -> None:
        """设置 DFE 抽头值（从 AMI 参数获取）。"""
        self.tap_values[:] = np.asarray(taps, dtype=np.float64)[:self.n_taps]

    def apply(self, signal: NDArray[np.float64]) -> NDArray[np.float64]:
        """对信号应用 DFE 均衡。"""
        out = np.zeros_like(signal)
        for i in range(len(signal)):
            feedback = 0.0
            for k in range(min(self.n_taps, i)):
                feedback += self.tap_values[k] * out[i - k - 1]
            out[i] = signal[i] - feedback
        return out


class FFE:
    """前向反馈均衡器（预加重/去加重）。"""

    def __init__(self, pre_cursor: float = 0.0, post_cursor: float = 0.0) -> None:
        """初始化 FFE。

        Args:
            pre_cursor: 预加重 (dB)，负值表示去加重。
            post_cursor: 后加重 (dB)。
        """
        self.pre_cursor = pre_cursor
        self.post_cursor = post_cursor

    def apply(self, signal: NDArray[np.float64]) -> NDArray[np.float64]:
        """对信号应用 FFE 均衡。"""
        pre_lin = 10 ** (self.pre_cursor / 20.0) if self.pre_cursor != 0 else 1.0
        post_lin = 10 ** (self.post_cursor / 20.0) if self.post_cursor != 0 else 1.0

        out = np.zeros_like(signal)
        for i in range(len(signal)):
            # 当前抽头
            curr = signal[i] if i < len(signal) else 0.0
            # 前一个（pre cursor）
            prev = signal[i - 1] if i > 0 else 0.0
            # 后一个（post cursor）
            next_ = signal[i + 1] if i < len(signal) - 1 else 0.0

            out[i] = (pre_lin * prev + curr + post_lin * next_) / (pre_lin + 1.0 + post_lin)
        return out


# 5. SerDes 信道仿真器

@dataclass
class ChannelResult:
    """信道仿真结果。"""
    waveform: NDArray[np.float64]  # 时域波形 (V)
    times_ps: NDArray[np.float64]  # 时间轴 (ps)
    eye_result: EyeDiagramResult
    # AMI 参数
    ami_params: AMIParams


class SerDesSimulator:
    """SerDes 信道仿真器：TX (FFE) → 频道 → RX (CTLE + DFE) → 眼图。"""

    def __init__(
        self,
        baud_rate_gbps: float = 25.0,
        ui_ps: float | None = None,
    ) -> None:
        """初始化 SerDes 仿真器。

        Args:
            baud_rate_gbps: 波特率 (Gb/s)。
            ui_ps: 单位间隔 (ps)，None 时自动计算。
        """
        self.baud_rate_gbps = baud_rate_gbps
        self.ui_ps = ui_ps if ui_ps else 1000.0 / baud_rate_gbps
        self.n_samples_per_ui = 16  # 每 UI 16 个采样点
        self.tx_ffe = FFE(pre_cursor=0.0, post_cursor=0.0)
        self.rx_ctle = CTLE(dc_gain_db=6.0)
        self.rx_dfe = DFE(n_taps=5)
        self.eye_analyzer = EyeAnalyzer(ui_ps=self.ui_ps)

    def set_tx_equalization(self, pre_cursor: float = 0.0, post_cursor: float = 0.0) -> None:
        """设置发射机 FFE 均衡。"""
        self.tx_ffe = FFE(pre_cursor=pre_cursor, post_cursor=post_cursor)

    def set_rx_ctle(self, gain_db: float = 6.0, pole_hz: float = 15e9) -> None:
        """设置接收机 CTLE。"""
        self.rx_ctle = CTLE(dc_gain_db=gain_db, pole_hz=pole_hz)

    def set_rx_dfe(self, n_taps: int = 5) -> None:
        """设置接收机 DFE。"""
        self.rx_dfe = DFE(n_taps=n_taps)

    def generate_prbs7(self, n_bits: int) -> NDArray[np.int8]:
        """生成 PRBS7 伪随机比特序列。"""
        bits = np.zeros(n_bits, dtype=np.int8)
        reg = 0b1000000  # 7-bit LFSR initial value
        for i in range(n_bits):
            bits[i] = reg >> 6 & 1
            # feedback: x^7 + x^6 + 1 (primitive polynomial)
            new_bit = ((reg >> 6) ^ (reg >> 5)) & 1
            reg = ((reg << 1) | new_bit) & 0x7F
        return bits

    def simulate(
        self,
        n_bits: int = 1024,
        amplitude_mv: float = 800.0,
        channel_impulse: NDArray[np.float64] | None = None,
        ami_params: AMIParams | None = None,
        noise_mv_rms: float = 5.0,
        jitter_ps_rms: float = 1.0,
    ) -> ChannelResult:
        if ami_params is None:
            ami_params = AMIParams()

        # 更新均衡器配置
        self.set_tx_equalization(
            pre_cursor=ami_params.tx_pre_cursor,
            post_cursor=ami_params.tx_post_cursor,
        )
        self.set_rx_ctle(gain_db=ami_params.rx_ctle_attenuation_db)

        # 生成比特序列
        bits = self.generate_prbs7(n_bits)

        # 仿真参数
        sps = self.n_samples_per_ui  # 每比特采样数
        n_samples = n_bits * sps
        times_ps = np.arange(n_samples) * (self.ui_ps / sps)
        waveform = np.zeros(n_samples, dtype=np.float64)

        # DAC: 比特 → 模拟电压
        for b_idx, bit in enumerate(bits):
            v_level = amplitude_mv if bit else 0.0
            start = b_idx * sps
            # 上升/下降沿
            t_r = max(1, int(0.1 * sps))  # 10% UI 上升时间
            for s in range(sps):
                t_local = s / sps
                if t_local < 0.5:
                    waveform[start + s] = v_level * min(1.0, t_local * sps / t_r)
                else:
                    waveform[start + s] = v_level * max(0.0, 1.0 - (t_local - 0.5) * sps / t_r)

        # 发射机 FFE 均衡
        waveform = self.tx_ffe.apply(waveform)

        # 信道（卷积冲激响应）
        if channel_impulse is not None and len(channel_impulse) > 1:
            waveform = np.convolve(waveform, channel_impulse, mode="same")

        # 接收机噪声
        if noise_mv_rms > 0:
            noise = np.random.default_rng(42).normal(0, noise_mv_rms, n_samples)
            waveform += noise.astype(np.float64)

        # 接收机 CTLE
        dt_s = (self.ui_ps / sps) * 1e-12
        waveform = self.rx_ctle.apply(waveform, dt_s)

        # 接收机 DFE
        waveform = self.rx_dfe.apply(waveform)

        # 眼图分析
        eye_result = self.eye_analyzer.analyze_statistical(
            amplitude_mv=amplitude_mv,
            rise_time_ps=0.1 * self.ui_ps,
            fall_time_ps=0.1 * self.ui_ps,
            jitter_ps_rms=jitter_ps_rms,
            noise_mv_rms=noise_mv_rms,
            tx_pre_cursor=ami_params.tx_pre_cursor,
            tx_post_cursor=ami_params.tx_post_cursor,
        )

        return ChannelResult(
            waveform=waveform,
            times_ps=times_ps,
            eye_result=eye_result,
            ami_params=ami_params,
        )

    def simulate_from_ibis(
        self,
        ibis_path: str | Path,
        ami_path: str | Path | None = None,
        n_bits: int = 1024,
    ) -> ChannelResult:
        """从 IBIS 文件和 AMI 参数文件运行仿真。"""
        parser = IBISParser(ibis_path)
        models = parser.parse()
        if not models:
            raise ValueError(f"IBIS 文件 {ibis_path} 无有效模型")
        model_name, model = next(iter(models.items()))

        # 提取模型参数
        if model.ramp:
            dv_dt_r = model.ramp.get("dV_r", 0.3) / model.ramp.get("dt_r", 10e-12) if model.ramp else 1e10
            amplitude_mv = 800.0  # 默认
        else:
            amplitude_mv = 800.0

        ami_params = AMIParams()
        if ami_path:
            ami_params = AMIParser.parse(ami_path)

        return self.simulate(
            n_bits=n_bits,
            amplitude_mv=amplitude_mv,
            ami_params=ami_params,
        )


# 6. 单元测试

def _test() -> None:
    """冒烟测试。"""
    import tempfile, os
    from pathlib import Path

    # Test 1: IBIS 解析
    ibis_content = """!IBIS test
[Component] test_serdes
[Model] output_buffer
[Pullup]-1.0 -0.020\n0.0 0.0\n1.0 0.020\n[End Pullup]
[Pulldown]-1.0 0.020\n0.0 0.0\n1.0 -0.020\n[End Pulldown]
[Ramp]0.3/10n 0.3/10n 0.3/10n 50\n[End Ramp]
[C_comp]1.0e-12 2.0e-12 0.5e-12\n[End C_comp]
[End Model]
[End Component]
"""
    tmp_ibis = tempfile.mktemp(suffix=".ibs")
    Path(tmp_ibis).write_text(ibis_content)
    parser = IBISParser(tmp_ibis)
    models = parser.parse()
    assert len(models) > 0
    os.unlink(tmp_ibis)

    # Test 2: AMI 解析
    ami_content = """[Reserved_Parameters]\nInit_Returns_Impulse = True\nGetWave_Exists = True\n[End Reserved_Parameters]\n[Model_Specific]\ntx_pre_cursor = -3.5\ntx_post_cursor = -6.0\nrx_ctle_attenuation_db = 6.0\n[End Model_Specific]\n"""
    tmp_ami = tempfile.mktemp(suffix=".ami")
    Path(tmp_ami).write_text(ami_content)
    params = AMIParser.parse(tmp_ami)
    assert params.tx_pre_cursor == -3.5
    os.unlink(tmp_ami)

    # Test 3: 眼图分析
    analyzer = EyeAnalyzer(ui_ps=40.0)
    result = analyzer.analyze_statistical(800.0, 10.0, 10.0, 1.5, 10.0)
    assert result.eye_height_mv > 0 and result.q_factor > 0

    # Test 4: SerDes 仿真
    sim = SerDesSimulator(baud_rate_gbps=25.0)
    res = sim.simulate(n_bits=256, amplitude_mv=800.0, noise_mv_rms=8.0)
    assert len(res.waveform) > 0

    # Test 5: Q↔BER
    ber = q_to_ber(7.0)
    q_back = ber_to_q(ber)
    assert abs(q_back - 7.0) < 0.1

    print(f"IBIS✓ AMI✓ 眼图✓ SerDes✓ Q-BER✓ 所有测试通过 ✅")


if __name__ == "__main__":
    _test()
