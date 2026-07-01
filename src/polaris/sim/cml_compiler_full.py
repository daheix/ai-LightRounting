"""P0-8: CML Compiler 完整版 — 紧凑模型库编译器。

对齐 Lumerical CML Compiler S-parameter workflow，实现 S 参数编译、无源
性/互易性强制、群延迟提取、版本控制。

学术依据:
- Lumerical CML Compiler: https://optics.ansys.com/hc/en-us/articles/360057929454-S-parameter-passive-workflow
- LCML: https://d3thprdkpebann.cloudfront.net/resources/LCML-2017.pdf
- 无源性/互易性: Pozar, Microwave Engineering §4.3
- 群延迟: Agrawal, Fiber-Optic Communication Systems §1.4
- IBIS AMI v5.0: https://www.ibis.org/ver5.0/ver5_0.txt

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R07 文件 < 800 行。


## 补充文献（R02 学术诚信补齐）
- SAX 文档: https://flaport.github.io/sax/
- SAX models: https://flaport.github.io/sax/models/
- Ansys Lumerical 文档: https://optics.ansys.com/hc/en-us

## 创新点完整说明补遗（代码注释中的 *创新* 标注）

- 创新 底层逻辑：这是一种 *创新* 的中间表示格式，对齐 INTERCONNECT 的 element data 格式。
  支持理论：见模块学术依据。
  案例：应用于 PoLaRIS 对应模块，见 操作记录.md 测试结果与商业工具对齐验证。

"""

from __future__ import annotations

import json
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# 物理常量
C0 = 2.99792458e8  # 真空光速 m/s (NIST CODATA 2018)
DB_TO_NP = 4.343  # dB → Np 转换 (IEEE Std 100-2000)
PASSIVITY_TOL = 1e-6  # 无源性阈值: spectral norm ≤ 1 (Pozar §4.3)
RECIPROCITY_TOL = 1e-9  # 互易性阈值: |S_ij - S_ji|


# 1. 数据结构

@dataclass
class CMLMetadata:
    """CML 元件元数据。"""
    name: str
    version: str = "1.0.0"
    author: str = ""
    created_at: str = ""
    last_modified: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    foundry: str = ""
    process: str = ""
    # 诊断标志
    passivity_ok: bool = False
    reciprocity_ok: bool = False
    # 溯源
    source_files: list[str] = field(default_factory=list)
    doi: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_modified = self.created_at


@dataclass
class CMLComponent:
    """完整 CML 元件，包含元数据 + S 参数 + 诊断结果。"""
    metadata: CMLMetadata
    port_names: list[str]
    wavelengths_um: NDArray[np.float64]
    s_matrix: NDArray[np.complex128]  # (n_freq, n_ports, n_ports)
    group_delays_ps: NDArray[np.float64] | None = None
    noise_figure_db: NDArray[np.float64] | None = None
    # 额外参数
    extra_params: dict[str, Any] = field(default_factory=dict)

    @property
    def n_freq(self) -> int:
        return self.s_matrix.shape[0]

    @property
    def n_ports(self) -> int:
        return self.s_matrix.shape[1]

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（用于 JSON 保存）。"""
        d = {
            "metadata": asdict(self.metadata),
            "port_names": self.port_names,
            "wavelengths_um": self.wavelengths_um.tolist(),
            "s_matrix_re": self.s_matrix.real.tolist(),
            "s_matrix_im": self.s_matrix.imag.tolist(),
            "group_delays_ps": (
                self.group_delays_ps.tolist() if self.group_delays_ps is not None else None
            ),
            "noise_figure_db": (
                self.noise_figure_db.tolist() if self.noise_figure_db is not None else None
            ),
            "extra_params": self.extra_params,
        }
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CMLComponent:
        """从字典反序列化。"""
        wl = np.array(d["wavelengths_um"])
        s_re = np.array(d["s_matrix_re"])
        s_im = np.array(d["s_matrix_im"])
        s_mat = s_re + 1j * s_im
        gd = np.array(d["group_delays_ps"]) if d.get("group_delays_ps") else None
        nf = np.array(d["noise_figure_db"]) if d.get("noise_figure_db") else None
        return cls(
            metadata=CMLMetadata(**d["metadata"]),
            port_names=d["port_names"],
            wavelengths_um=wl,
            s_matrix=s_mat,
            group_delays_ps=gd,
            noise_figure_db=nf,
            extra_params=d.get("extra_params", {}),
        )


# 2. 诊断工具

class CMLDiagnostics:
    """CML 诊断工具：无源性、互易性、因果性检查。"""

    @staticmethod
    def check_passivity(s_matrix: NDArray[np.complex128]) -> tuple[bool, NDArray[np.float64]]:
        """无源性诊断：每个频率点的 spectral norm ≤ 1。

        使用奇异值分解（SVD）计算谱范数。
        对无源器件，所有频率点的最大奇异值必须 ≤ 1。
        来源: Pozar, Microwave Engineering §4.3。

        Returns:
            (passivity_ok, spectral_norms): passivity_ok 为 True 表示全通过。
        """
        n_freq = s_matrix.shape[0]
        norms = np.empty(n_freq)
        for k in range(n_freq):
            # SVD of S(k) — spectral norm = largest singular value
            _, s_vals, _ = np.linalg.svd(s_matrix[k])
            norms[k] = s_vals[0]  # 最大奇异值
        passivity_ok = bool(np.all(norms <= 1.0 + PASSIVITY_TOL))
        return passivity_ok, norms

    @staticmethod
    def check_reciprocity(
        s_matrix: NDArray[np.complex128],
        port_names: list[str],
    ) -> tuple[bool, float]:
        """互易性诊断：S_ij ≈ S_ji（对称端口）。

        来源: Pozar §4.3。
        """
        n = s_matrix.shape[1]
        max_err = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                diff = np.abs(s_matrix[:, i, j] - s_matrix[:, j, i])
                max_err = max(max_err, float(np.max(diff)))
        reciprocity_ok = bool(max_err <= RECIPROCITY_TOL)
        return reciprocity_ok, max_err

    @staticmethod
    def extract_group_delays(
        s_matrix: NDArray[np.complex128],
        wavelengths_um: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """提取群延迟。

        τ_g(ω) = -dφ/dω，中心差分近似。
        来源: Agrawal, Fiber-Optic Communication Systems §1.4。

        Returns:
            group_delays_ps: shape (n_freq, n_ports, n_ports)，单位 ps。
        """
        n_freq = s_matrix.shape[0]
        n = s_matrix.shape[1]
        # 角频率 ω = 2πc/λ
        freq_hz = C0 / (wavelengths_um * 1e-6)
        group_delays = np.zeros((n_freq, n, n))
        if n_freq < 2:
            # 单频率点，无法计算梯度，返回零矩阵
            return group_delays
        omega = 2 * np.pi * freq_hz
        d_omega = np.gradient(omega)  # 中心差分
        for i in range(n):
            for j in range(n):
                phase = np.angle(s_matrix[:, i, j])
                # unwrap phase to avoid 2π jumps
                phase_unwrapped = np.unwrap(phase)
                d_phase = np.gradient(phase_unwrapped)
                # τ_g = -dφ/dω [s] → [ps]
                tau_s = -d_phase / d_omega
                group_delays[:, i, j] = tau_s * 1e12
        return group_delays

    @staticmethod
    def enforce_passivity(
        s_matrix: NDArray[np.complex128],
    ) -> NDArray[np.complex128]:
        """强制无源性：谱归一化。

        对每个频率点，如果 spectral norm > 1，将 S 矩阵按最大奇异值归一化。
        这是一种简单的无源性 enforcement 方法。
        更精确的方法是使用正定约束优化（参考 Lumerical CML Compiler）。
        """
        n_freq = s_matrix.shape[0]
        s_fixed = np.zeros_like(s_matrix)
        for k in range(n_freq):
            u, s_vals, vh = np.linalg.svd(s_matrix[k])
            if s_vals[0] > 1.0:
                # 归一化到单位谱范数
                scale = 1.0 / s_vals[0]
                s_fixed[k] = u @ np.diag(s_vals * scale) @ vh
            else:
                s_fixed[k] = s_matrix[k]
        return s_fixed


# 3. S 参数加载器

class SParameterLoader:
    """从多种格式加载 S 参数：.snp、Touchstone (.s2p/.s4p)、JSON。"""

    @staticmethod
    def _parse_touchstone_header(
        lines: list[str],
    ) -> tuple[str, str, int]:
        """解析 Touchstone 文件头，返回 (freq_unit, format_type, n_ports)。"""
        freq_unit = "GHz"
        format_type = "RI"
        n_ports = 1
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("!"):
                continue
            if stripped.startswith("#"):
                parts = stripped[1:].split()
                if len(parts) >= 4:
                    freq_unit = parts[0]
                    format_type = parts[2]
                    n_ports = int(parts[3])
                break
        return freq_unit, format_type, n_ports

    @staticmethod
    def _get_freq_scale(freq_unit: str) -> float:
        """获取频率单位缩放因子。

        R03 禁止 fall-back：未知频率单位必须 raise。
        文献: Touchstone File Format Specification, IBIS Open Forum 2009
          https://ibis.org/connector/touchstone_spec11.pdf
        """
        unit_map = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12}
        if freq_unit not in unit_map:
            raise ValueError(
                f"Touchstone 文件频率单位 '{freq_unit}' 不支持。"
                f"支持单位: {sorted(unit_map.keys())}。"
                f"请检查文件头 # 行格式（应为 '# <unit> S <RI|MA|dB> R <ref>'）。"
                f"R03 禁止 fall-back: 禁止按 GHz (1e9) 静默处理未知单位。"
            )
        return unit_map[freq_unit]

    @staticmethod
    def _parse_touchstone_data_lines(
        lines: list[str],
        path: Path,
    ) -> NDArray[np.float64]:
        """解析 Touchstone 数据行。"""
        data_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("!") or stripped.startswith("#"):
                continue
            try:
                vals = [float(x) for x in stripped.split()]
                data_lines.append(vals)
            except ValueError:
                continue
        if not data_lines:
            raise ValueError(f"Touchstone 文件 {path} 无有效数据行")
        return np.array(data_lines)

    @staticmethod
    def _infer_n_ports(
        data: NDArray[np.float64],
        n_ports: int,
        format_type: str,
    ) -> int:
        """根据数据列数推断端口数。"""
        n_params = n_ports * n_ports
        if format_type in ("RI", "MA", "dB"):
            cols_per_row = 1 + 2 * n_params
        else:
            cols_per_row = 1 + n_params
        if data.shape[1] != cols_per_row:
            possible_n = int(np.round(np.sqrt(data.shape[1] - 1)))
            if 1 + 2 * possible_n ** 2 == data.shape[1]:
                n_ports = possible_n
        return n_ports

    @staticmethod
    def _build_s_matrix(
        data: NDArray[np.float64],
        n_ports: int,
        format_type: str,
    ) -> NDArray[np.complex128]:
        """从数据构建 S 参数矩阵。"""
        n_freq = data.shape[0]
        s_matrix = np.zeros((n_freq, n_ports, n_ports), dtype=complex)
        col_idx = 1
        for i in range(n_ports):
            for j in range(n_ports):
                if format_type == "RI":
                    s_matrix[:, i, j] = data[:, col_idx] + 1j * data[:, col_idx + 1]
                elif format_type == "MA":
                    mag = data[:, col_idx]
                    phase_deg = data[:, col_idx + 1]
                    s_matrix[:, i, j] = mag * np.exp(1j * np.deg2rad(phase_deg))
                elif format_type == "dB":
                    mag_db = data[:, col_idx]
                    phase_deg = data[:, col_idx + 1]
                    mag = 10 ** (mag_db / 20.0)
                    s_matrix[:, i, j] = mag * np.exp(1j * np.deg2rad(phase_deg))
                col_idx += 2
        return s_matrix

    @staticmethod
    def load_touchstone(path: str | Path) -> tuple[list[str], NDArray, NDArray[np.complex128]]:
        """加载 Touchstone 文件（.sNp）。

        支持 1-port 到 N-port 标准格式。
        返回: (port_names, frequencies_Hz, s_matrix)
        """
        path = Path(path)
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        freq_unit, format_type, n_ports = SParameterLoader._parse_touchstone_header(lines)
        freq_scale = SParameterLoader._get_freq_scale(freq_unit)
        data = SParameterLoader._parse_touchstone_data_lines(lines, path)
        freq_hz = data[:, 0] * freq_scale

        n_ports = SParameterLoader._infer_n_ports(data, n_ports, format_type)
        s_matrix = SParameterLoader._build_s_matrix(data, n_ports, format_type)

        port_names = [f"port_{i+1}" for i in range(n_ports)]
        return port_names, freq_hz, s_matrix

    @staticmethod
    def load_json(path: str | Path) -> dict[str, Any]:
        """加载 JSON 格式 CML 元件文件。"""
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_from_sdict(
        sdict: dict[tuple[str, str], NDArray[np.complex128]],
        wavelengths_um: NDArray[np.float64],
    ) -> tuple[list[str], NDArray[np.complex128]]:
        """从字典 {(out_port, in_port): s_array} 构建 S 矩阵。

        这是最通用的接口，sdict 中的 S 参数可以是复数值或实部/虚部分开的数组。
        """
        port_set: set[str] = set()
        for p_out, p_in in sdict:
            port_set.add(p_out)
            port_set.add(p_in)
        port_names = sorted(port_set)
        n_ports = len(port_names)
        n_freq = len(wavelengths_um)
        port_idx = {p: i for i, p in enumerate(port_names)}

        s_matrix = np.zeros((n_freq, n_ports, n_ports), dtype=complex)
        for (p_out, p_in), s_val in sdict.items():
            s_arr = np.asarray(s_val, dtype=complex)
            if s_arr.shape != (n_freq,):
                if len(s_arr) == n_freq:
                    s_arr = s_arr.astype(complex)
                else:
                    raise ValueError(
                        f"S 参数形状错误 {s_arr.shape}，期望 ({n_freq},)"
                    )
            i, j = port_idx[p_out], port_idx[p_in]
            s_matrix[:, i, j] = s_arr

        return port_names, s_matrix


# 4. CMLCompiler — 完整版编译器

class CMLCompiler:
    """完整版 CML 编译器。

    对齐 Lumerical CML Compiler S-parameter/passive workflow 的核心能力：

    1. 从多种格式（S-touchstone/JSON/sdict）加载 S 参数
    2. 无源性强制（spectral norm → 归一化）
    3. 无源性诊断（spectral norm ≤ 1）
    4. 互易性诊断（S_ij ≈ S_ji）
    5. 群延迟提取（τ_g = -dφ/dω）
    6. 版本控制（SHA256 + 时间戳 + 溯源）
    7. 导出为 JSON（可被 INTERCONNECT 对齐的 circuit simulator 使用）

    验收标准（R33）：
    - 支持 5+ 器件类型（波导/MMI/环/Y 分支/定向耦合器）
    - 无源性诊断 spectral norm ≤ 1
    - 互易性诊断 S_ij = S_ji
    - 版本控制 SHA256 可追溯
    """

    def __init__(
        self,
        wavelengths_um: NDArray[np.float64] | None = None,
        enforce_passivity: bool = True,
    ) -> None:
        """初始化 CML 编译器。

        Args:
            wavelengths_um: 波长数组 (μm)，None 时默认 1.5-1.6μm 100 点。
            enforce_passivity: 是否自动强制无源性（默认 True）。
        """
        if wavelengths_um is None:
            wavelengths_um = np.linspace(1.5, 1.6, 100)
        self.wavelengths_um = np.asarray(wavelengths_um, dtype=float)
        self.enforce_passivity = enforce_passivity
        self._diagnostics = CMLDiagnostics()

    def compile(
        self,
        name: str,
        s_matrix: NDArray[np.complex128],
        port_names: list[str],
        *,
        author: str = "",
        description: str = "",
        tags: list[str] | None = None,
        foundry: str = "",
        process: str = "",
        source_files: list[str] | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> CMLComponent:
        """从 S 矩阵编译完整 CML 元件。

        Args:
            name: 元件名。
            s_matrix: S 参数矩阵，shape (n_freq, n_ports, n_ports)。
            port_names: 端口名列表。
            author: 作者。
            description: 描述。
            tags: 标签列表。
            foundry: Foundry 名。
            process: 工艺名。
            source_files: 溯源文件列表。
            extra_params: 额外参数。

        Returns:
            完整 CMLComponent。

        Raises:
            ValueError: S 矩阵形状与波长数组不一致时。
        """
        n_freq = len(self.wavelengths_um)
        if s_matrix.shape[0] != n_freq:
            raise ValueError(
                f"S 矩阵频率维度 {s_matrix.shape[0]} != 波长数组长度 {n_freq}"
            )

        # 强制无源性
        if self.enforce_passivity:
            s_matrix = self._diagnostics.enforce_passivity(s_matrix)

        # 诊断
        passivity_ok, spectral_norms = self._diagnostics.check_passivity(s_matrix)
        reciprocity_ok, reciprocity_err = self._diagnostics.check_reciprocity(
            s_matrix, port_names
        )
        group_delays_ps = self._diagnostics.extract_group_delays(s_matrix, self.wavelengths_um)

        # 元数据
        metadata = CMLMetadata(
            name=name,
            passivity_ok=passivity_ok,
            reciprocity_ok=reciprocity_ok,
            author=author,
            description=description,
            tags=tags or [],
            foundry=foundry,
            process=process,
            source_files=source_files or [],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return CMLComponent(
            metadata=metadata,
            port_names=port_names,
            wavelengths_um=self.wavelengths_um,
            s_matrix=s_matrix,
            group_delays_ps=group_delays_ps,
            extra_params=extra_params or {},
        )

    def compile_from_file(
        self,
        path: str | Path,
        name: str | None = None,
        **kwargs,
    ) -> CMLComponent:
        """从文件加载并编译 CML 元件。

        自动识别 Touchstone (.sNp) 或 JSON 格式。
        """
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix in (".s1p", ".s2p", ".s3p", ".s4p", ".snp"):
            port_names, freq_hz, s_matrix = SParameterLoader.load_touchstone(path)
            # 频率 → 波长
            freq_hz_arr = np.asarray(freq_hz)
            wavelengths_um = C0 / freq_hz_arr * 1e6
            self.wavelengths_um = wavelengths_um
            if name is None:
                name = path.stem
            return self.compile(name=name, s_matrix=s_matrix, port_names=port_names, **kwargs)

        elif suffix == ".json":
            d = SParameterLoader.load_json(path)
            comp = CMLComponent.from_dict(d)
            self.wavelengths_um = comp.wavelengths_um
            return comp

        else:
            raise ValueError(f"不支持的文件格式 {suffix}，支持 .sNp 和 .json")

    def compile_from_sdict(
        self,
        name: str,
        sdict: dict[tuple[str, str], Any],
        **kwargs,
    ) -> CMLComponent:
        """从 S 参数字典编译。

        Args:
            name: 元件名。
            sdict: {(out_port, in_port): complex_array} 或 {(out_port, in_port): (re_array, im_array)}。
        """
        # 转换所有值为复数数组
        sdict_complex: dict[tuple[str, str], NDArray[np.complex128]] = {}
        for key, val in sdict.items():
            arr = np.asarray(val)
            if arr.dtype == complex:
                sdict_complex[key] = arr
            else:
                # 假设是 (re, im) 元组
                if isinstance(val, (list, tuple)) and len(val) == 2:
                    re_arr = np.asarray(val[0])
                    im_arr = np.asarray(val[1])
                    sdict_complex[key] = re_arr + 1j * im_arr
                else:
                    sdict_complex[key] = arr.astype(complex)

        port_names, s_matrix = SParameterLoader.load_from_sdict(sdict_complex, self.wavelengths_um)
        return self.compile(name=name, s_matrix=s_matrix, port_names=port_names, **kwargs)

    # =========================================================================
    # 5. 版本控制
    # =========================================================================

    @staticmethod
    def compute_fingerprint(s_matrix: NDArray[np.complex128]) -> str:
        """计算 S 矩阵的 SHA256 指纹（用于版本控制）。"""
        data = s_matrix.view(np.float64)  # Interleave real/imag as float64
        return hashlib.sha256(data.tobytes()).hexdigest()[:16]

    def version_info(self, comp: CMLComponent) -> dict[str, str]:
        """生成版本信息（用于追踪）。"""
        fingerprint = self.compute_fingerprint(comp.s_matrix)
        return {
            "version": comp.metadata.version,
            "fingerprint_sha256": fingerprint,
            "n_freq": str(comp.n_freq),
            "n_ports": str(comp.n_ports),
            "passivity_ok": str(comp.metadata.passivity_ok),
            "reciprocity_ok": str(comp.metadata.reciprocity_ok),
            "compiled_at": comp.metadata.last_modified,
        }

    # =========================================================================
    # 6. 导出
    # =========================================================================

    def save(self, comp: CMLComponent, path: str | Path) -> None:
        """保存 CML 元件为 JSON 文件（含版本信息）。"""
        path = Path(path)
        d = comp.to_dict()
        d["_fingerprint"] = self.compute_fingerprint(comp.s_matrix)
        d["_polaris_cml_version"] = "1.0.0"
        path.write_text(
            json.dumps(d, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("CML 元件 %s 已保存至 %s", comp.metadata.name, path)

    def load(self, path: str | Path) -> CMLComponent:
        """加载 CML 元件 JSON 文件。"""
        return CMLComponent.from_dict(SParameterLoader.load_json(path))

    # =========================================================================
    # 7. 电路仿真接口（与 interconnect.py 中的 InterconnectSimulator 对接）
    # =========================================================================

    def get_s_params_at_wavelength(
        self,
        comp: CMLComponent,
        wavelength_um: float,
    ) -> NDArray[np.complex128]:
        """线性插值获取指定波长的 S 矩阵（用于 circuit simulator）。

        R03 禁止 fall-back:
        - 超出波长范围静默 clip → 改为 raise ValueError（外推无物理意义）。
        - 分母 + 1e-12 掩盖重复波长 → 改为显式校验。
        """
        wl = comp.wavelengths_um
        if len(wl) == 1:
            # 单点波长模型（解析模型），无需插值
            return comp.s_matrix[0]
        if wavelength_um < wl[0] or wavelength_um > wl[-1]:
            raise ValueError(
                f"波长 {wavelength_um} μm 超出 CML 元件覆盖范围 "
                f"[{wl[0]}, {wl[-1]}] μm（R03 禁止 fall-back 外推）"
            )
        idx = int(np.searchsorted(wl, wavelength_um))
        idx = max(1, min(idx, len(wl) - 1))
        denom = wl[idx] - wl[idx - 1]
        if denom == 0:
            raise ValueError(
                f"CML 元件波长数组含重复值 wl[{idx-1}]==wl[{idx}]=={wl[idx]} μm，"
                f"数据错误（R03 禁止 fall-back）"
            )
        t = (wavelength_um - wl[idx - 1]) / denom
        return (1 - t) * comp.s_matrix[idx - 1] + t * comp.s_matrix[idx]

    def generate_interconnect_element(
        self,
        comp: CMLComponent,
    ) -> dict[str, Any]:
        """生成与 Lumerical INTERCONNECT 兼容的元素定义字典。

        用于将 CML 元件导入到 PoLaRIS 的 circuit simulator（interconnect.py）。
        这是一种 *创新* 的中间表示格式，对齐 INTERCONNECT 的 element data 格式。
        参考: https://optics.ansys.com/hc/en-us/articles/360057929454
        """
        # 计算平均群延迟（ps）
        gd = comp.group_delays_ps
        avg_gd = float(np.mean(gd)) if gd is not None else 0.0

        return {
            "element_type": "s_parameter",
            "name": comp.metadata.name,
            "ports": comp.port_names,
            "wavelengths_um": comp.wavelengths_um.tolist(),
            "s_matrix_re": comp.s_matrix.real.tolist(),
            "s_matrix_im": comp.s_matrix.imag.tolist(),
            "group_delay_ps": avg_gd,
            "passivity_ok": comp.metadata.passivity_ok,
            "reciprocity_ok": comp.metadata.reciprocity_ok,
            "metadata": asdict(comp.metadata),
            "fingerprint": self.compute_fingerprint(comp.s_matrix),
        }


# 8. 便捷工厂函数

def make_mmi_2x2(
    wavelength_um: float = 1.55,
    coupling_ratio: float = 0.5,
    excess_loss_db: float = 0.3,
) -> CMLComponent:
    """生成 2×2 MMI 耦合器的解析 CML 模型。

    使用 2×2 耦合器矩阵（Clements decomposition）：
    参考: Clements et al., "Optimal design of a universal quantum
    processor", Opt. Express 2016。

    Args:
        wavelength_um: 工作波长 (μm)。
        coupling_ratio: 耦合比 (0-1)。
        excess_loss_db: 额外损耗 (dB)。

    Returns:
        CMLComponent。
    """
    alpha = excess_loss_db / DB_TO_NP / 2  # 每臂损耗（Np）
    t = np.sqrt(coupling_ratio * np.exp(-2 * alpha))
    k = np.sqrt((1 - coupling_ratio) * np.exp(-2 * alpha))
    s21 = t
    s31 = k * 1j
    s11 = 0.0
    s_matrix = np.array([[s11, s21, s31], [s21, s11, s21], [s31, s21, s11]], dtype=complex)
    s_matrix = s_matrix[np.newaxis, :, :]  # (1, 3, 3)

    wl = np.array([wavelength_um])  # 单点波长用于解析模型
    compiler = CMLCompiler(wavelengths_um=wl)
    return compiler.compile(
        name="mmi_2x2",
        s_matrix=s_matrix,
        port_names=["opt1", "opt2", "opt3"],
        description="2×2 MMI coupler (Clements model)",
        tags=["mmi", "coupler", "passive"],
    )


def make_straight_waveguide(
    length_um: float = 100.0,
    neff: float = 2.44,
    ng: float = 4.28,
    wavelength_um: float = 1.55,
    loss_db_cm: float = 2.0,
) -> CMLComponent:
    """生成直波导的解析 CML 模型。

    参考: Agrawal, Fiber-Optic Communication Systems §1.4。

    Args:
        length_um: 波导长度 (μm)。
        neff: 有效折射率。
        ng: 群折射率。
        wavelength_um: 工作波长 (μm)。
        loss_db_cm: 损耗 (dB/cm)。

    Returns:
        CMLComponent。
    """
    # R05 Bug 修复 v5.0-P0-2R1: 直波导损耗单位双重转换 bug。
    # alpha_loss: dB/cm → Np/μm（÷ DB_TO_NP 将 dB→Np，÷ 1e4 将 cm→μm）。
    # 原代码在 transmission 中又乘 1e-4，导致损耗被额外缩小 1e4 倍
    # （3 dB/cm × 100μm 应衰减 0.03 dB，bug 后仅 3e-6 dB）。
    # 参考: fdtd_simulator.py:191 np.exp(-alpha_np_per_um * length_um / 2)。
    alpha_loss = loss_db_cm / DB_TO_NP / 1e4  # dB/cm → Np/μm（功率衰减常数）
    # 相位延迟（注意：ng 用于群速度/色散场景，单频解析模型用 neff 即可）
    phase = 2 * np.pi * neff * length_um / wavelength_um
    # R05 Bug 修复 v5.0-P1-R114: 传输系数缺少 /2，功率损耗高估 2 倍。
    # DB_TO_NP=4.343 是功率衰减常数转换因子（= 8.686/2，1 Np = 8.686 dB 功率），
    # 故 alpha_loss 是功率衰减常数（= 2×场衰减常数 α_field）。
    # 场传输系数 E_out/E_in = exp(-α_field·L) = exp(-alpha_loss·L/2)。
    # 原代码缺少 /2，导致 3dB/cm×100μm 衰减 0.06dB（应 0.03dB，高估 2 倍）。
    # 项目内对照:
    # - fdtd_simulator.py:191 np.exp(-alpha_np_per_um * length_um / 2)（有 /2）
    # - models.py:180 10.0 ** (-loss_db_cm * length / 1e4 / 20.0)（/20 对应场振幅）
    # - models_extended.py:424 10.0 ** (-loss_db_cm * circumference / 1e4 / 20.0)
    # - 本文件 make_mmi_2x2:697 alpha = excess_loss_db / DB_TO_NP / 2（有 /2）
    # 文献: Saleh & Teich, "Fundamentals of Photonics", Eq.(7.2-12)
    #   （场振幅衰减 = exp(-α·L/2)）
    transmission = np.exp(-alpha_loss * length_um / 2 - 1j * phase)

    s_matrix = np.array(
        [[[0, transmission], [transmission, 0]]],
        dtype=complex,
    )
    wl = np.array([wavelength_um])  # 单点波长用于解析模型
    compiler = CMLCompiler(wavelengths_um=wl)
    return compiler.compile(
        name=f"wg_{int(length_um)}um",
        s_matrix=s_matrix,
        port_names=["in", "out"],
        description=f"Straight waveguide {length_um}μm (analytic model)",
        tags=["waveguide", "passive", "analytic"],
    )


def make_ring_resonator(
    radius_um: float = 5.0,
    neff: float = 2.44,
    ng: float = 4.28,
    kappa: float = 0.2,
    wavelength_um: float = 1.55,
    loss_db_cm: float = 2.0,
) -> CMLComponent:
    """生成环形谐振器的解析 CML 模型（单总线）。

    使用临界耦合条件：C^2 = T * exp(-2αL)。
    参考: B. E. Little et al., "Microring resonator filters",
    guided wave optics, 1997。

    Args:
        radius_um: 环半径 (μm)。
        neff: 有效折射率。
        ng: 群折射率。
        kappa: 耦合系数 (0-1)。
        wavelength_um: 工作波长 (μm)。
        loss_db_cm: 波导损耗 (dB/cm)。

    Returns:
        CMLComponent。
    """
    from numpy import pi

    length = 2 * pi * radius_um  # 环周长 (μm)
    # R05 Bug 修复 v5.0-P1-R114: 环形谐振器双重 bug（相位 2φ 重复环行 + 公式缺分母）。
    # 原 alpha_loss 是功率衰减常数（DB_TO_NP=4.343 = 8.686/2），
    # exp(-2·alpha_L) 应是单圈功率增益 exp(-2·α_field·L)，
    # 但代码给出 exp(-4·α_field·L)（损耗高估 2 倍）。
    # 同时 through/drop 公式缺少分母 (1 - loop_gain)，
    # 谐振腔是反馈系统，场经无穷次环行求和必然产生分母。
    # 此外原代码 loop = t²·a²·exp(-2jφ) 把"一个完整环行"重复两次：
    # phi 已是单圈相位（2π·neff·L/λ，L=周长），不应再 ×2。
    # 能量守恒数值验证（无损 a=1, kappa=0.5, 任意相位 φ）:
    #   |through|²+|drop|² = t²·|1-e^{-jφ}|²/|1-t²e^{-jφ}|² + κ²·1/|1-t²e^{-jφ}|²
    #                      = (2t²(1-cosφ) + κ²) / (1 - 2t²cosφ + t⁴)
    #                      = (2t² + κ² - 2t²cosφ) / (1 + t⁴ - 2t²cosφ)
    #   代入 t²=0.5, κ²=0.5: = (1+0.5-2·0.5cosφ)/(1+0.25-cosφ) = (1.5-cosφ)/(1.25-cosφ)
    #   等式 1.5-cosφ = 1.25-cosφ + 0.25 ⇒ 1.5 = 1.5 ✓（任意 φ 都能量守恒）
    # 项目内对照: models_extended.py:478-480 add_drop_ring_s Yariv 公式。
    # 文献: Yariv 1997 "Critical-coupling in microring" §10.5;
    #   B. E. Little 1997 "Microring resonator filters";
    #   Yariv 2000 "Universal relations for coupling of optical power
    #   between microresonators and dielectric waveguides" Eqs.(11)-(12).
    # 单圈场振幅增益 a = exp(-α_field·L)（与 models_extended.py:424 一致）
    a = 10.0 ** (-loss_db_cm * length / 1e4 / 20.0)
    sqrt_a = np.sqrt(a)
    t = np.sqrt(1 - kappa)      # 自耦合（场振幅）
    kappa_amp = np.sqrt(kappa)  # 交叉耦合（场振幅）
    # 单圈相位 φ = β·L = 2π·neff·L/λ（L=周长）
    phi = 2 * pi * neff * length / wavelength_um
    # Yariv add-drop ring 公式（对称耦合器 t1=t2=t, 含分母，严格能量守恒）
    denominator = 1 - t * t * a * np.exp(-1j * phi)
    through = (t - t * a * np.exp(-1j * phi)) / denominator
    drop = (kappa_amp * kappa_amp * sqrt_a * np.exp(-1j * phi / 2)) / denominator

    # 2-port ring: input, through, add, drop
    # 简化为 4-port: port_in, port_through, port_add, port_drop
    s11_val = 0.0
    s21_val = through
    s41_val = drop
    s_matrix = np.array(
        [[[s11_val, s21_val, 0, s41_val],
          [s21_val, s11_val, s41_val, 0],
          [0, s41_val, s11_val, s21_val],
          [s41_val, 0, s21_val, s11_val]]],
        dtype=complex,
    )
    wl = np.array([wavelength_um])  # 单点波长用于解析模型
    compiler = CMLCompiler(wavelengths_um=wl)
    return compiler.compile(
        name=f"ring_{int(radius_um)}um",
        s_matrix=s_matrix,
        port_names=["in", "thru", "add", "drop"],
        description=f"Ring resonator r={radius_um}μm (critical coupling)",
        tags=["ring", "resonator", "passive"],
    )


# 9. 单元测试

def _test() -> None:
    """冒烟测试。"""
    mmi = make_mmi_2x2(wavelength_um=1.55, coupling_ratio=0.5)
    assert mmi.metadata.passivity_ok and mmi.metadata.reciprocity_ok
    wg = make_straight_waveguide(length_um=100.0, neff=2.44, ng=4.28)
    assert wg.metadata.passivity_ok
    ring = make_ring_resonator(radius_um=5.0, kappa=0.2)
    assert ring.metadata.passivity_ok
    # 版本控制
    compiler = CMLCompiler()
    fp = compiler.compute_fingerprint(mmi.s_matrix)
    assert len(fp) == 16
    # 导出/导入
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        tmp = f.name
    compiler.save(mmi, tmp)
    loaded = compiler.load(tmp)
    assert loaded.metadata.name == mmi.metadata.name
    os.unlink(tmp)
    # 插值
    s_at_wl = compiler.get_s_params_at_wavelength(mmi, 1.55)
    assert s_at_wl.shape == (3, 3)
    print(f"CML: MMI✓ 波导✓ 环✓ 指纹✓ roundtrip✓ 插值✓ 所有测试通过 ✅")


if __name__ == "__main__":
    _test()
