"""R5 第5轮 P0+P1 fall-back 消除回归测试。

覆盖 R5 修复的 3 项 P0 + 11 项 P1 + 2 项 P2，共 16 项。

R5 修复清单:
- R5-P0-1: quantum_klm.py KLM CNOT 成功率 0.25 → 1/9（Ralph 2002 简化 4-BS）
- R5-P0-2: fdtd_jax_backend.py MU0 1.25663706212e-7 → 1.25663706212e-6（小 10 倍）
- R5-P0-3: fdtd_gpu_engine.py use_gpu=True → False + raise（R04 GPU 战略）
- R5-P1-1: opto_electrical.py 2.0 → 3.0 dB/cm（SOI 统一）
- R5-P1-2: edge_gnn.py 2.0 → 3.0 dB/cm（SOI 统一）
- R5-P1-3: tcad_thermal_package.py 未知材料 fall-back → raise ValueError
- R5-P1-4: tcad_thermal_package.py 物理常数升级 CODATA 2018 精确值
- R5-P1-5: dag_scheduler.py _fallback_klu 重命名 + 显式环检测
- R5-P1-6: quantum_circuit_distributed.py simulate_training_step deprecated 删除
- R5-P1-7: rcwa solver_1d/solver_2d 负衍射效率截断 → raise RuntimeError
- R5-P1-8: subnetwork_decomp.py 死代码 + 静默丢失 → raise + 合并
- R5-P1-9: apollo_benchmark.py crossing_loss 0.2 → 0.3（SiEPIC PDK 统一）
- R5-P1-10: tcad_thermal_package.py 温度标准说明（JEDEC 25°C vs TCAD 300K）
- R5-P1-11: test_r35 quantum_advantage_threshold 测试修复
- R5-P2-1: BB84 channel_loss_db=3.0 文献溯源（ITU-T G.652 / ETSI GS QKD 002）
- R5-P2-2: HOM coherence_length_um=5.0 文献溯源（Kwiat 1995 / Bouwmeester 1997）

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修 / R07 操作记录
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pytest


# =============================================================================
# R5-P0-1: KLM CNOT 成功率 0.25 → 1/9（Ralph 2002 简化 4-BS）
# =============================================================================

class TestR5P01KlmCnotSuccessProb:
    """R5-P0-1: KLM CNOT 成功率必须为 1/9（Ralph 2002），非 0.25（Knill NS-gate）。"""

    def test_klm_cnot_success_prob_is_one_ninth(self) -> None:
        """klm_cnot_success_probability() 返回 1/9 ≈ 0.1111。"""
        from polaris.sim.quantum_klm import klm_cnot_success_probability
        p = klm_cnot_success_probability()
        assert abs(p - 1.0 / 9.0) < 1e-10, f"应为 1/9 ≈ 0.1111，实际 {p}"

    def test_klm_cnot_simulate_theoretical_is_one_ninth(self) -> None:
        """klm_cnot_simulate() 返回的 theoretical_success_prob 为 1/9。"""
        from polaris.sim.quantum_klm import klm_cnot_simulate
        result = klm_cnot_simulate(n_shots=500, seed=42)
        assert abs(result["theoretical_success_prob"] - 1.0 / 9.0) < 1e-10

    def test_no_hardcoded_0_25_in_klm_success(self) -> None:
        """klm_cnot_success_probability 的 return 语句不含 0.25。"""
        klm_file = Path(__file__).parent.parent / "src/polaris/sim/quantum_klm.py"
        src = klm_file.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "klm_cnot_success_probability":
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Return) and stmt.value is not None:
                        if isinstance(stmt.value, ast.Constant) and stmt.value.value == 0.25:
                            pytest.fail("R5-P0-1: 禁止 return 0.25")
                break


# =============================================================================
# R5-P0-2: MU0 物理常数修正（小 10 倍 → 正确值）
# =============================================================================

class TestR5P02Mu0Constant:
    """R5-P0-2: MU0 必须为 1.25663706212e-6 H/m（4π×10⁻⁷），非 1.25663706212e-7。"""

    def test_mu0_value_correct(self) -> None:
        """MU0 = 4π×10⁻⁷ ≈ 1.25663706212e-6 H/m。"""
        from polaris.sim.fdtd_jax_backend import MU0
        expected = 4 * math.pi * 1e-7
        assert abs(MU0 - expected) < 1e-15, f"MU0 应为 {expected}，实际 {MU0}"

    def test_mu0_not_small_10x(self) -> None:
        """MU0 不能是 1.25663706212e-7（小 10 倍的错误值）。"""
        from polaris.sim.fdtd_jax_backend import MU0
        assert MU0 > 1e-6, f"MU0 应 > 1e-6，实际 {MU0}（可能小 10 倍）"

    def test_eta0_correct(self) -> None:
        """真空阻抗 η₀ = sqrt(MU0/EPS0) ≈ 377 Ω。"""
        from polaris.sim.fdtd_jax_backend import MU0, EPS0
        eta0 = math.sqrt(MU0 / EPS0)
        assert abs(eta0 - 376.73) < 1.0, f"η₀ 应 ≈ 377 Ω，实际 {eta0}"


# =============================================================================
# R5-P0-3: fdtd_gpu_engine use_gpu 强制 False（R04 GPU 战略）
# =============================================================================

class TestR5P03GpuStrategyCompliance:
    """R5-P0-3: GPUFDTDConfig.use_gpu 必须为 False，True 时 raise。"""

    def test_default_use_gpu_false(self) -> None:
        """GPUFDTDConfig 默认 use_gpu=False。"""
        from polaris.sim.fdtd_gpu_engine import GPUFDTDConfig
        config = GPUFDTDConfig()
        assert config.use_gpu is False, "R04: use_gpu 必须为 False"

    def test_use_gpu_true_raises(self) -> None:
        """use_gpu=True 时 GPUFDTDEngine.__init__ 必须 raise RuntimeError。"""
        from polaris.sim.fdtd_gpu_engine import GPUFDTDConfig, GPUFDTDEngine
        bad_config = GPUFDTDConfig(use_gpu=True)
        with pytest.raises(RuntimeError, match="R04"):
            GPUFDTDEngine(bad_config)

    def test_module_docstring_marks_no_gpu(self) -> None:
        """模块 docstring 必须标注 🚫不参与 GPU。"""
        gpu_file = Path(__file__).parent.parent / "src/polaris/sim/fdtd_gpu_engine.py"
        src = gpu_file.read_text(encoding="utf-8")
        # 检查前 30 行 docstring
        docstring_end = src.find('"""', 3)
        docstring = src[:docstring_end] if docstring_end > 0 else src[:1000]
        assert "🚫不参与 GPU" in docstring or "R04" in docstring, "docstring 必须标注 R04"


# =============================================================================
# R5-P1-1: opto_electrical.py 2.0 → 3.0 dB/cm
# =============================================================================

class TestR5P11OptoElectricalLossUnification:
    """R5-P1-1: opto_electrical.py 传播损耗必须为 3.0 dB/cm（SOI 统一）。"""

    def test_no_hardcoded_2_0_loss(self) -> None:
        """源码中不应有 `2.0 * length / 1e4` 硬编码。"""
        oe_file = Path(__file__).parent.parent / "src/polaris/router/opto_electrical.py"
        src = oe_file.read_text(encoding="utf-8")
        assert "2.0 * length / 1e4" not in src, "R5-P1-1: 禁止 2.0 dB/cm 硬编码"
        assert "3.0 * length / 1e4" in src, "应为 3.0 dB/cm"


# =============================================================================
# R5-P1-2: edge_gnn.py 2.0 → 3.0 dB/cm
# =============================================================================

class TestR5P12EdgeGnnLossUnification:
    """R5-P1-2: edge_gnn.py loss_db_cm 默认必须为 3.0（SOI 统一）。"""

    def test_no_hardcoded_2_0_loss_default(self) -> None:
        """源码中 loss_db_cm 默认不应为 2.0。"""
        gnn_file = Path(__file__).parent.parent / "src/polaris/rl/edge_gnn.py"
        src = gnn_file.read_text(encoding="utf-8")
        assert '"loss_db_cm", 2.0' not in src, "R5-P1-2: 禁止 2.0 dB/cm 默认"
        assert '"loss_db_cm", 3.0' in src, "应为 3.0 dB/cm"


# =============================================================================
# R5-P1-3: tcad_thermal_package.py 未知材料 fall-back → raise
# =============================================================================

class TestR5P13TcadUnknownMaterialRaises:
    """R5-P1-3: 未知材料必须 raise ValueError，禁止 fall-back 到 InGaAs 1e4。"""

    def test_known_materials_work(self) -> None:
        """已知材料（ingaas/ge/si）正常计算响应度。"""
        from polaris.device.tcad_thermal_package import TCADAwareModel
        model = TCADAwareModel()
        for mat in ["ingaas", "ge", "si"]:
            result = model.photodetector_responsivity(material=mat)
            assert result["responsivity_A_W"] > 0

    def test_unknown_material_raises(self) -> None:
        """未知材料必须 raise ValueError。"""
        from polaris.device.tcad_thermal_package import TCADAwareModel
        model = TCADAwareModel()
        with pytest.raises(ValueError, match="未知材料"):
            model.photodetector_responsivity(material="gaas")

    def test_no_get_fallback_for_material(self) -> None:
        """源码中不应有 .get(material, 1e4) fall-back。"""
        tcad_file = Path(__file__).parent.parent / "src/polaris/device/tcad_thermal_package.py"
        src = tcad_file.read_text(encoding="utf-8")
        assert ".get(material, 1e4)" not in src, "R5-P1-3: 禁止 .get fall-back"


# =============================================================================
# R5-P1-4: tcad_thermal_package.py 物理常数 CODATA 2018 升级
# =============================================================================

class TestR5P14TcadPhysicalConstantsUpgrade:
    """R5-P1-4: tcad_thermal_package.py 物理常数必须为 CODATA 2018 精确值。"""

    def test_q_precision(self) -> None:
        """photodetector_responsivity 使用 CODATA 2018 q=1.602176634e-19。"""
        tcad_file = Path(__file__).parent.parent / "src/polaris/device/tcad_thermal_package.py"
        src = tcad_file.read_text(encoding="utf-8")
        # 检查 photodetector_responsivity 函数内是否有精确值
        assert "1.602176634e-19" in src, "R5-P1-4: q 应为 CODATA 2018 精确值"

    def test_no_low_precision_q_in_responsivity(self) -> None:
        """photodetector_responsivity 中不应有 q = 1.602e-19（低精度）。"""
        tcad_file = Path(__file__).parent.parent / "src/polaris/device/tcad_thermal_package.py"
        src = tcad_file.read_text(encoding="utf-8")
        # 提取 photodetector_responsivity 函数
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "photodetector_responsivity"):
                func_src = ast.get_source_segment(src, node)
                assert "1.602e-19" not in func_src, "R5-P1-4: 禁止低精度 q=1.602e-19"
                assert "6.626e-34" not in func_src, "R5-P1-4: 禁止低精度 h=6.626e-34"
                break


# =============================================================================
# R5-P1-5: dag_scheduler.py _fallback_klu 重命名 + 显式环检测
# =============================================================================

class TestR5P15DagSchedulerFallbackRename:
    """R5-P1-5: _fallback_klu 重命名为 _cascade_via_klu，显式环检测。"""

    def test_no_fallback_klu_function(self) -> None:
        """源码中不应有 _fallback_klu 函数定义。"""
        dag_file = Path(__file__).parent.parent / "src/polaris/sim/dag_scheduler.py"
        src = dag_file.read_text(encoding="utf-8")
        assert "def _fallback_klu(" not in src, "R5-P1-5: 禁止 _fallback_klu 命名"
        assert "def _cascade_via_klu(" in src, "应重命名为 _cascade_via_klu"

    def test_has_cycle_detection(self) -> None:
        """应有显式 _has_cycle 函数。"""
        dag_file = Path(__file__).parent.parent / "src/polaris/sim/dag_scheduler.py"
        src = dag_file.read_text(encoding="utf-8")
        assert "def _has_cycle(" in src, "R5-P1-5: 应有显式 _has_cycle 环检测"

    def test_no_except_runtimeerror_fallback(self) -> None:
        """cascade_parallel 中不应有 except RuntimeError → _fallback_klu 模式。"""
        dag_file = Path(__file__).parent.parent / "src/polaris/sim/dag_scheduler.py"
        src = dag_file.read_text(encoding="utf-8")
        assert "except RuntimeError:" not in src or "_fallback_klu" not in src, \
            "R5-P1-5: 禁止 except RuntimeError 静默 fall-back"

    def test_cyclic_circuit_succeeds(self) -> None:
        """环电路应通过 _cascade_via_klu 正常求解（非 fall-back）。"""
        from polaris.sim.dag_scheduler import cascade_parallel
        wl = np.array([1.55])
        instances = {
            "a": {
                ("in", "in"): np.array([0.1 + 0.0j]),
                ("out", "in"): np.array([0.9 + 0.0j]),
                ("in", "out"): np.array([0.9 + 0.0j]),
                ("out", "out"): np.array([0.1 + 0.0j]),
            },
            "b": {
                ("in", "in"): np.array([0.1 + 0.0j]),
                ("out", "in"): np.array([0.9 + 0.0j]),
                ("in", "out"): np.array([0.9 + 0.0j]),
                ("out", "out"): np.array([0.1 + 0.0j]),
            },
        }
        connections = [("a.out", "b.in"), ("b.out", "a.in")]
        ports = {"in1": "a.in", "out1": "b.out"}
        result = cascade_parallel(instances, connections, ports)
        assert isinstance(result, dict)


# =============================================================================
# R5-P1-6: quantum_circuit_distributed.py simulate_training_step 删除
# =============================================================================

class TestR5P16SimulateTrainingStepDeleted:
    """R5-P1-6: simulate_training_step deprecated 方法必须删除。"""

    def test_no_simulate_training_step_method(self) -> None:
        """DistributedPPOTrainer 不应有 simulate_training_step 方法。"""
        qcd_file = Path(__file__).parent.parent / "src/polaris/quantum/quantum_circuit_distributed.py"
        src = qcd_file.read_text(encoding="utf-8")
        assert "def simulate_training_step(" not in src, \
            "R5-P1-6: simulate_training_step 必须删除"

    def test_training_step_still_works(self) -> None:
        """training_step 方法仍可用。"""
        from polaris.quantum.quantum_circuit_distributed import (
            DistributedPPOConfig,
            DistributedPPOTrainer,
        )
        config = DistributedPPOConfig(
            n_workers=2, n_devices_per_circuit=100, synthetic_env_mode=True,
        )
        trainer = DistributedPPOTrainer(config)
        result = trainer.training_step(10)
        assert result["n_workers"] == 2


# =============================================================================
# R5-P1-7: rcwa 负衍射效率截断 → raise
# =============================================================================

class TestR5P17RcwaNegativeEfficiencyRaises:
    """R5-P1-7: RCWA 负衍射效率必须 raise RuntimeError，禁止静默截断为 0。"""

    def test_solver_1d_no_truncate(self) -> None:
        """solver_1d.py 不应有 `ratio[ratio < 0] = 0.0` 截断。"""
        s1d_file = Path(__file__).parent.parent / "src/polaris/sim/rcwa/solver_1d.py"
        src = s1d_file.read_text(encoding="utf-8")
        assert "ratio[ratio < 0] = 0.0" not in src, \
            "R5-P1-7: 禁止静默截断负效率"

    def test_solver_2d_no_truncate(self) -> None:
        """solver_2d.py 不应有 `ratio[ratio < 0] = 0.0` 截断。"""
        s2d_file = Path(__file__).parent.parent / "src/polaris/sim/rcwa/solver_2d.py"
        src = s2d_file.read_text(encoding="utf-8")
        assert "ratio[ratio < 0] = 0.0" not in src, \
            "R5-P1-7: 禁止静默截断负效率"

    def test_solver_1d_raises_on_negative(self) -> None:
        """_safe_real_ratio 在负效率时 raise RuntimeError。"""
        from polaris.sim.rcwa.solver_1d import _safe_real_ratio
        # 构造负比值：numerator 实部为负，denominator 实部为正
        num = np.array([-1.0 + 0j, 2.0 + 0j])
        den = 1.0 + 0j
        with pytest.raises(RuntimeError, match="负值"):
            _safe_real_ratio(num, den)

    def test_solver_2d_raises_on_negative(self) -> None:
        """solver_2d _safe_real_ratio 在负效率时 raise RuntimeError。"""
        from polaris.sim.rcwa.solver_2d import _safe_real_ratio
        num = np.array([-1.0 + 0j, 2.0 + 0j])
        den = 1.0 + 0j
        with pytest.raises(RuntimeError, match="负值"):
            _safe_real_ratio(num, den)


# =============================================================================
# R5-P1-8: subnetwork_decomp.py 死代码 + 静默丢失 → raise + 合并
# =============================================================================

class TestR5P18SubnetworkDecompDeadCodeFix:
    """R5-P1-8: _multiway_partition 死代码修复，多余社区合并而非丢弃。"""

    def test_no_dead_while_loop(self) -> None:
        """源码中不应有死代码 while 循环。"""
        sd_file = Path(__file__).parent.parent / "src/polaris/sim/subnetwork_decomp.py"
        src = sd_file.read_text(encoding="utf-8")
        assert "while len(subnetworks) < num_subnetworks and len(communities)" not in src, \
            "R5-P1-8: 禁止死代码 while 循环"

    def test_insufficient_communities_raises(self) -> None:
        """社区数 < num_subnetworks 时 raise RuntimeError。"""
        from polaris.sim.subnetwork_decomp import _multiway_partition
        import networkx as nx
        G = nx.Graph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
        with pytest.raises(RuntimeError, match="社区数"):
            _multiway_partition(nx, G, num_subnetworks=5)


# =============================================================================
# R5-P1-9: apollo_benchmark.py crossing_loss 0.2 → 0.3
# =============================================================================

class TestR5P19ApolloCrossingLossUnification:
    """R5-P1-9: apollo_benchmark.py crossing insertion_loss_db 必须为 0.3。"""

    def test_crossing_loss_is_0_3(self) -> None:
        """PTC_DEVICES["crossing"].insertion_loss_db == 0.3。"""
        from polaris.data.apollo_benchmark import PTC_DEVICES
        assert PTC_DEVICES["crossing"].insertion_loss_db == 0.3, \
            "R5-P1-9: crossing_loss 应为 0.3 dB（SiEPIC EBeam PDK 统一）"

    def test_no_0_2_in_crossing(self) -> None:
        """源码中 crossing 的 insertion_loss_db 不应为 0.2。"""
        ab_file = Path(__file__).parent.parent / "src/polaris/data/apollo_benchmark.py"
        src = ab_file.read_text(encoding="utf-8")
        assert "insertion_loss_db=0.2" not in src, "R5-P1-9: 禁止 0.2 dB"


# =============================================================================
# R5-P1-10: tcad 温度标准说明（JEDEC 25°C vs TCAD 300K）
# =============================================================================

class TestR5P110TcadTemperatureStandard:
    """R5-P1-10: thermal_budget docstring 必须说明 25°C vs 300K 行业惯例差异。"""

    def test_docstring_mentions_jedec(self) -> None:
        """thermal_budget docstring 必须提及 JEDEC 标准。"""
        tcad_file = Path(__file__).parent.parent / "src/polaris/device/tcad_thermal_package.py"
        src = tcad_file.read_text(encoding="utf-8")
        # 提取 thermal_budget 函数
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "thermal_budget"):
                func_src = ast.get_source_segment(src, node)
                assert "JEDEC" in func_src or "jedec" in func_src.lower(), \
                    "R5-P1-10: docstring 应说明 JEDEC 25°C 标准"
                assert "300K" in func_src or "300 K" in func_src, \
                    "R5-P1-10: docstring 应说明 TCAD 300K 标准"
                break


# =============================================================================
# R5-P2-1: BB84 channel_loss_db=3.0 文献溯源
# =============================================================================

class TestR5P21Bb84ChannelLossDoc:
    """R5-P2-1: BB84 docstring 必须包含 ITU-T G.652 / ETSI GS QKD 002 文献。"""

    def test_docstring_has_itu_t(self) -> None:
        """BB84 simulate docstring 必须引用 ITU-T G.652。"""
        qcd_file = Path(__file__).parent.parent / "src/polaris/quantum/quantum_circuit_distributed.py"
        src = qcd_file.read_text(encoding="utf-8")
        assert "ITU-T G.652" in src, "R5-P2-1: 应引用 ITU-T G.652"

    def test_docstring_has_etsi(self) -> None:
        """BB84 simulate docstring 必须引用 ETSI GS QKD 002。"""
        qcd_file = Path(__file__).parent.parent / "src/polaris/quantum/quantum_circuit_distributed.py"
        src = qcd_file.read_text(encoding="utf-8")
        assert "ETSI GS QKD 002" in src, "R5-P2-1: 应引用 ETSI GS QKD 002"


# =============================================================================
# R5-P2-2: HOM coherence_length_um=5.0 文献溯源
# =============================================================================

class TestR5P22HomCoherenceLengthDoc:
    """R5-P2-2: HOM docstring 必须包含 Kwiat 1995 / Bouwmeester 1997 文献。"""

    def test_docstring_has_kwiat(self) -> None:
        """hom_dip docstring 必须引用 Kwiat 1995。"""
        qcd_file = Path(__file__).parent.parent / "src/polaris/quantum/quantum_circuit_distributed.py"
        src = qcd_file.read_text(encoding="utf-8")
        assert "Kwiat" in src, "R5-P2-2: 应引用 Kwiat 1995"

    def test_docstring_has_bouwmeester(self) -> None:
        """hom_dip docstring 必须引用 Bouwmeester 1997。"""
        qcd_file = Path(__file__).parent.parent / "src/polaris/quantum/quantum_circuit_distributed.py"
        src = qcd_file.read_text(encoding="utf-8")
        assert "Bouwmeester" in src, "R5-P2-2: 应引用 Bouwmeester 1997"


# =============================================================================
# 跨模块一致性验证
# =============================================================================

class TestR5CrossModuleConsistency:
    """R5 跨模块参数一致性验证。"""

    def test_soi_loss_consistent_3_0(self) -> None:
        """SOI 传播损耗全项目统一为 3.0 dB/cm。"""
        # 检查关键文件不含 2.0 dB/cm 硬编码（排除注释）
        files_to_check = [
            "src/polaris/router/opto_electrical.py",
            "src/polaris/rl/edge_gnn.py",
        ]
        for rel_path in files_to_check:
            f = Path(__file__).parent.parent / rel_path
            src = f.read_text(encoding="utf-8")
            # 不应在代码行（非注释）中出现 2.0 dB/cm 硬编码
            for line in src.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # 检查 loss_db_cm 默认值或硬编码 2.0
                if '"loss_db_cm", 2.0' in line:
                    pytest.fail(f"{rel_path}: 禁止 loss_db_cm=2.0 默认")
                if "2.0 * length / 1e4" in line:
                    pytest.fail(f"{rel_path}: 禁止 2.0 dB/cm 硬编码")

    def test_crossing_loss_consistent_0_3(self) -> None:
        """crossing_loss 全项目统一为 0.3 dB。"""
        from polaris.data.apollo_benchmark import PTC_DEVICES
        from polaris.router.curvy_optodesigner import AdaptiveCrossingInserter
        # apollo_benchmark PTC
        assert PTC_DEVICES["crossing"].insertion_loss_db == 0.3
        # curvy_optodesigner 默认
        inserter = AdaptiveCrossingInserter()
        assert inserter.crossing_loss == 0.3
