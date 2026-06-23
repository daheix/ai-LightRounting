"""PoLaRIS 端到端 Demo Showcase 测试套件。

覆盖 examples/e2e_showcase 9 阶段全流程，验证各阶段 run() 返回值结构与关键指标，
以及汇总报告生成与全流程集成。

学术诚信（规则 18）:
- 所有断言基于真实阶段输出，无 fall-back 假数据
- 公式与参数来源参见各 stage 模块文档字符串
- 测试仅校验阶段模块的实际行为，不构造虚假期望值

来源:
- Showcase 模块: examples/e2e_showcase/stages/
- 报告生成器: examples/e2e_showcase/report_generator.py
- 主入口: examples/e2e_showcase/run_showcase.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 将 showcase 目录加入 sys.path，使 stages 包与同级模块可被导入
_SHOWCASE_DIR = Path(__file__).resolve().parent.parent / "examples" / "e2e_showcase"
if str(_SHOWCASE_DIR) not in sys.path:
    sys.path.insert(0, str(_SHOWCASE_DIR))

from report_generator import generate_report  # noqa: E402
from stages import (  # noqa: E402
    stage1_pdk_catalog,
    stage2_circuit_spec,
    stage3_ai_placement,
    stage4_routing,
    stage5_simulation,
    stage6_drc_lvs,
    stage7_gds_export,
    stage8_opto_electrical,
    stage9_quantum_photonics,
)

# =============================================================================
# 阶段 1: PDK 器件目录展示
# =============================================================================


class TestStage1PDKCatalog:
    """阶段 1: PDK 器件目录展示测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage1_pdk_catalog.run(tmp_path)
        assert isinstance(result, dict)

    def test_platforms_count(self, tmp_path: Path) -> None:
        """验证 4 个平台（SOI/SiN/InP/LNOI）。"""
        result = stage1_pdk_catalog.run(tmp_path)
        platforms = result["platforms"]
        assert len(platforms) == 4
        names = {p["platform"] for p in platforms}
        assert names == {"SOI", "SiN", "InP", "LNOI"}

    def test_total_device_count(self, tmp_path: Path) -> None:
        """验证总器件数 ≥ 36（SOI 15 + SiN 7 + InP 7 + LNOI 7 = 36）。"""
        result = stage1_pdk_catalog.run(tmp_path)
        assert result["total_device_count"] >= 36

    def test_representative_devices(self, tmp_path: Path) -> None:
        """验证每平台有代表器件（≥ 3 个）。"""
        result = stage1_pdk_catalog.run(tmp_path)
        for platform in result["platforms"]:
            assert len(platform["representative_devices"]) >= 3
            for dev in platform["representative_devices"]:
                assert "name" in dev
                assert "params" in dev
                assert "source" in dev

    def test_foundry_sources(self, tmp_path: Path) -> None:
        """验证来源 foundry 标注（每平台含 foundry 与 foundry_url）。"""
        result = stage1_pdk_catalog.run(tmp_path)
        for platform in result["platforms"]:
            assert platform["foundry"]
            assert platform["foundry_url"].startswith("https://")


# =============================================================================
# 阶段 2: 电路规格定义
# =============================================================================


class TestStage2CircuitSpec:
    """阶段 2: 电路规格定义测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage2_circuit_spec.run(tmp_path)
        assert isinstance(result, dict)

    def test_circuits_count(self, tmp_path: Path) -> None:
        """验证 3 个电路（MZI/Clements/玻色采样）。"""
        result = stage2_circuit_spec.run(tmp_path)
        assert len(result["circuits"]) == 3

    def test_mzi_devices(self, tmp_path: Path) -> None:
        """验证 MZI 有 5 器件。"""
        result = stage2_circuit_spec.run(tmp_path)
        mzi = result["circuits"][0]
        assert mzi["n_devices"] == 5

    def test_clements_devices(self, tmp_path: Path) -> None:
        """验证 Clements 有 10 器件（6 分束器 + 4 相移器）。"""
        result = stage2_circuit_spec.run(tmp_path)
        clements = result["circuits"][1]
        assert clements["n_devices"] == 10

    def test_unitary_matrix_shape(self, tmp_path: Path) -> None:
        """验证酉矩阵形状为 [4, 4]。"""
        result = stage2_circuit_spec.run(tmp_path)
        assert result["unitary_matrix_shape"] == [4, 4]


# =============================================================================
# 阶段 3: AI 布局
# =============================================================================


class TestStage3AIPlacement:
    """阶段 3: AI 布局测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage3_ai_placement.run(tmp_path)
        assert isinstance(result, dict)

    def test_circuits_count(self, tmp_path: Path) -> None:
        """验证 3 个电路布局。"""
        result = stage3_ai_placement.run(tmp_path)
        assert len(result["circuits"]) == 3

    def test_hpwl_positive(self, tmp_path: Path) -> None:
        """验证 HPWL > 0（布局后器件间连线长度非零）。"""
        result = stage3_ai_placement.run(tmp_path)
        for circuit in result["circuits"]:
            assert circuit["hpwl"] > 0

    def test_placement_mode(self, tmp_path: Path) -> None:
        """验证 placement_mode 为 "rl" 或 "analytical"。"""
        result = stage3_ai_placement.run(tmp_path)
        assert result["placement_mode"] in {"rl", "analytical"}


# =============================================================================
# 阶段 4: 智能布线
# =============================================================================


class TestStage4Routing:
    """阶段 4: 智能布线测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage4_routing.run(tmp_path)
        assert isinstance(result, dict)

    def test_circuits_count(self, tmp_path: Path) -> None:
        """验证 3 个电路布线。"""
        result = stage4_routing.run(tmp_path)
        assert len(result["circuits"]) == 3

    def test_router_type(self, tmp_path: Path) -> None:
        """验证 router_type = "curvy"。"""
        result = stage4_routing.run(tmp_path)
        assert result["router_type"] == "curvy"

    def test_loss_positive(self, tmp_path: Path) -> None:
        """验证损耗 ≥ 0（波导传播损耗非负）。"""
        result = stage4_routing.run(tmp_path)
        for circuit in result["circuits"]:
            assert circuit["total_loss_db"] >= 0


# =============================================================================
# 阶段 5: 仿真验证
# =============================================================================


class TestStage5Simulation:
    """阶段 5: 仿真验证测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage5_simulation.run(tmp_path)
        assert isinstance(result, dict)

    def test_mzi_s_param(self, tmp_path: Path) -> None:
        """验证 MZI S 参数含 resonant_wavelength_nm 和 extinction_ratio_db。"""
        result = stage5_simulation.run(tmp_path)
        mzi = result["mzi_s_param"]
        assert "resonant_wavelength_nm" in mzi
        assert "extinction_ratio_db" in mzi
        # 谐振波长应在扫描范围 1500-1600nm 内
        assert 1500 <= mzi["resonant_wavelength_nm"] <= 1600

    def test_clements_unitary(self, tmp_path: Path) -> None:
        """验证酉性误差 < 1e-6。"""
        result = stage5_simulation.run(tmp_path)
        clements = result["clements_unitary"]
        assert clements["unitarity_error"] < 1e-6
        assert clements["is_unitary"] is True

    def test_pam4(self, tmp_path: Path) -> None:
        """验证 PAM4 BER > 0 且 SNR > 0。"""
        result = stage5_simulation.run(tmp_path)
        pam4 = result["pam4"]
        assert pam4["ber"] > 0
        assert pam4["snr_db"] > 0


# =============================================================================
# 阶段 6: DRC/LVS 验证
# =============================================================================


class TestStage6DRCLVS:
    """阶段 6: DRC/LVS 验证测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage6_drc_lvs.run(tmp_path)
        assert isinstance(result, dict)

    def test_drc_pass_rate(self, tmp_path: Path) -> None:
        """验证 DRC 通过率 ≥ 0。"""
        result = stage6_drc_lvs.run(tmp_path)
        assert result["drc"]["pass_rate"] >= 0

    def test_lvs_consistent(self, tmp_path: Path) -> None:
        """验证 LVS 结果为 bool。"""
        result = stage6_drc_lvs.run(tmp_path)
        assert isinstance(result["lvs"]["is_consistent"], bool)


# =============================================================================
# 阶段 7: GDS 导出
# =============================================================================


class TestStage7GDSExport:
    """阶段 7: GDS 导出测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage7_gds_export.run(tmp_path)
        assert isinstance(result, dict)

    def test_circuits_count(self, tmp_path: Path) -> None:
        """验证 3 个电路 GDS。"""
        result = stage7_gds_export.run(tmp_path)
        assert len(result["circuits"]) == 3

    def test_gds_files_exist(self, tmp_path: Path) -> None:
        """验证 GDS 文件存在且可加载。"""
        result = stage7_gds_export.run(tmp_path)
        for circuit in result["circuits"]:
            gds_path = Path(circuit["gds_path"])
            assert gds_path.exists()
            assert gds_path.stat().st_size > 0
            assert circuit["loadable"] is True


# =============================================================================
# 阶段 8: 光电协同
# =============================================================================


class TestStage8OptoElectrical:
    """阶段 8: 光电协同测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage8_opto_electrical.run(tmp_path)
        assert isinstance(result, dict)

    def test_verilog_a_models(self, tmp_path: Path) -> None:
        """验证 ≥ 5 个 Verilog-A 模型。"""
        result = stage8_opto_electrical.run(tmp_path)
        models = result["verilog_a_models"]
        assert len(models) >= 5
        for m in models:
            assert Path(m["file_path"]).exists()

    def test_spice_netlist(self, tmp_path: Path) -> None:
        """验证 SPICE 网表存在。"""
        result = stage8_opto_electrical.run(tmp_path)
        netlist = result["spice_netlist"]
        assert Path(netlist["file_path"]).exists()
        assert netlist["lines"] > 0

    def test_pam4(self, tmp_path: Path) -> None:
        """验证 PAM4 BER > 0 且 SNR > 0。"""
        result = stage8_opto_electrical.run(tmp_path)
        pam4 = result["pam4"]
        assert pam4["ber"] > 0
        assert pam4["snr_db"] > 0


# =============================================================================
# 阶段 9: 量子光子验证
# =============================================================================


class TestStage9QuantumPhotonics:
    """阶段 9: 量子光子验证测试。"""

    def test_run_returns_dict(self, tmp_path: Path) -> None:
        """验证 run() 返回 dict。"""
        result = stage9_quantum_photonics.run(tmp_path)
        assert isinstance(result, dict)

    def test_boson_sampling_prob_sum(self, tmp_path: Path) -> None:
        """验证概率守恒（所有输出概率之和 ≈ 1）。"""
        result = stage9_quantum_photonics.run(tmp_path)
        bs = result["boson_sampling"]
        assert abs(bs["prob_sum"] - 1.0) < 1e-6
        assert bs["prob_sum_ok"] is True

    def test_hom_verified(self, tmp_path: Path) -> None:
        """验证 HOM 干涉（|1,1⟩ 输出概率 ≈ 0）。"""
        result = stage9_quantum_photonics.run(tmp_path)
        hom = result["hom"]
        assert hom["hom_verified"] is True
        assert abs(hom["coincidence_prob"]) < 1e-6

    def test_klm_cnot(self, tmp_path: Path) -> None:
        """验证 KLM CNOT 成功率 ≈ 0.25（Knill et al., Nature 2001）。"""
        result = stage9_quantum_photonics.run(tmp_path)
        klm = result["klm"]
        assert klm["cnot_verified"] is True
        assert abs(klm["cnot_success_prob"] - 0.25) < 1e-6

    def test_klm_hadamard(self, tmp_path: Path) -> None:
        """验证 Hadamard 门酉性（H @ H† = I）。"""
        result = stage9_quantum_photonics.run(tmp_path)
        klm = result["klm"]
        assert klm["hadamard_verified"] is True
        assert klm["hadamard_unitary_error"] < 1e-6


# =============================================================================
# 汇总报告生成器
# =============================================================================


class TestReportGenerator:
    """汇总报告生成器测试。"""

    def test_generate_report(self, tmp_path: Path) -> None:
        """验证报告生成（report.md 文件存在且非空）。"""
        # 先执行阶段 1 生成 JSONL 日志（通过 StageLogger）
        from logging_config import StageLogger, setup_logging

        setup_logging(tmp_path)
        with StageLogger(1, "PDK 器件目录展示", tmp_path) as sl:
            result = stage1_pdk_catalog.run(tmp_path)
            for key, value in result.items():
                sl.log_output(key, value)

        report_path = generate_report(tmp_path)
        assert report_path.exists()
        assert report_path.stat().st_size > 0

    def test_report_contains_stages(self, tmp_path: Path) -> None:
        """验证报告含阶段信息（阶段执行状态表与学术诚信声明）。"""
        from logging_config import StageLogger, setup_logging

        setup_logging(tmp_path)
        with StageLogger(1, "PDK 器件目录展示", tmp_path) as sl:
            result = stage1_pdk_catalog.run(tmp_path)
            for key, value in result.items():
                sl.log_output(key, value)

        report_path = generate_report(tmp_path)
        content = report_path.read_text(encoding="utf-8")
        # 报告应包含阶段状态表头与学术诚信声明
        assert "阶段执行状态" in content
        assert "PDK 器件目录展示" in content
        assert "学术诚信声明" in content


# =============================================================================
# 端到端集成测试
# =============================================================================


@pytest.mark.slow
class TestE2EIntegration:
    """端到端集成测试：运行全流程 9 阶段。"""

    def test_full_showcase(self, tmp_path: Path) -> None:
        """运行全流程 9 阶段，验证全部成功。

        依次执行 stage1-stage9，验证每阶段 run() 返回非空 dict，
        且关键产物（酉矩阵 JSON、GDS、Verilog-A、SPICE 网表）均生成。
        """
        # 阶段 1: PDK 器件目录
        r1 = stage1_pdk_catalog.run(tmp_path)
        assert isinstance(r1, dict) and r1["total_device_count"] >= 36

        # 阶段 2: 电路规格定义
        r2 = stage2_circuit_spec.run(tmp_path)
        assert isinstance(r2, dict) and len(r2["circuits"]) == 3
        assert (tmp_path / "reports" / "boson_sampling_unitary.json").exists()

        # 阶段 3: AI 布局
        r3 = stage3_ai_placement.run(tmp_path)
        assert isinstance(r3, dict) and len(r3["circuits"]) == 3
        assert r3["placement_mode"] in {"rl", "analytical"}

        # 阶段 4: 智能布线
        r4 = stage4_routing.run(tmp_path)
        assert isinstance(r4, dict) and r4["router_type"] == "curvy"

        # 阶段 5: 仿真验证
        r5 = stage5_simulation.run(tmp_path)
        assert isinstance(r5, dict)
        assert r5["clements_unitary"]["is_unitary"] is True

        # 阶段 6: DRC/LVS 验证
        r6 = stage6_drc_lvs.run(tmp_path)
        assert isinstance(r6, dict)
        assert isinstance(r6["lvs"]["is_consistent"], bool)

        # 阶段 7: GDS 导出
        r7 = stage7_gds_export.run(tmp_path)
        assert isinstance(r7, dict) and len(r7["circuits"]) == 3
        for c in r7["circuits"]:
            assert Path(c["gds_path"]).exists()

        # 阶段 8: 光电协同
        r8 = stage8_opto_electrical.run(tmp_path)
        assert isinstance(r8, dict)
        assert len(r8["verilog_a_models"]) >= 5
        assert Path(r8["spice_netlist"]["file_path"]).exists()

        # 阶段 9: 量子光子验证
        r9 = stage9_quantum_photonics.run(tmp_path)
        assert isinstance(r9, dict)
        assert r9["boson_sampling"]["prob_sum_ok"] is True
        assert r9["hom"]["hom_verified"] is True
        assert r9["klm"]["cnot_verified"] is True
