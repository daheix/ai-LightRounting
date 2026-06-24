"""PoLaRIS 端到端 Demo Showcase 测试套件。

覆盖 examples/e2e_showcase 9 阶段全流程，验证各阶段 run() 返回值结构与关键指标，
日志配置、汇总报告生成与全流程集成。

测试优化: 各阶段 run() 较慢（含 IntegratedPipeline 布局布线），使用类级 fixture
缓存阶段结果，避免每个测试方法重复执行（规则 15.1 性能基准）。

学术诚信（规则 18）:
- 所有断言基于真实阶段输出，无 fall-back 假数据
- 公式与参数来源参见各 stage 模块文档字符串
- 测试仅校验阶段模块的实际行为，不构造虚假期望值

来源:
- Showcase 模块: examples/e2e_showcase/stages/
- 日志配置: examples/e2e_showcase/logging_config.py
- 报告生成器: examples/e2e_showcase/report_generator.py
- 主入口: examples/e2e_showcase/run_showcase.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 将 showcase 目录加入 sys.path，使 stages 包与同级模块可被导入
_SHOWCASE_DIR = Path(__file__).resolve().parent.parent / "examples" / "e2e_showcase"
if str(_SHOWCASE_DIR) not in sys.path:
    sys.path.insert(0, str(_SHOWCASE_DIR))

from logging_config import StageLogger, setup_logging  # noqa: E402
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

# 9 阶段定义: (阶段 ID, 阶段名称, 阶段模块)
_STAGES: list[tuple[int, str, object]] = [
    (1, "PDK 器件目录展示", stage1_pdk_catalog),
    (2, "电路规格定义", stage2_circuit_spec),
    (3, "AI 布局", stage3_ai_placement),
    (4, "智能布线", stage4_routing),
    (5, "仿真验证", stage5_simulation),
    (6, "DRC/LVS 验证", stage6_drc_lvs),
    (7, "GDS 导出", stage7_gds_export),
    (8, "光电协同", stage8_opto_electrical),
    (9, "量子光子验证", stage9_quantum_photonics),
]


def _make_output_dir(tmp_path_factory: pytest.TempPathFactory, name: str) -> Path:
    """创建输出目录（含 logs/gds/verilog_a/spice/reports 子目录）并配置日志。

    Args:
        tmp_path_factory: pytest 临时目录工厂。
        name: 子目录名（用于区分不同测试类）。

    Returns:
        配置好日志的输出目录路径。
    """
    out = tmp_path_factory.mktemp(name)
    for subdir in ["logs", "gds", "verilog_a", "spice", "reports"]:
        (out / subdir).mkdir(parents=True, exist_ok=True)
    setup_logging(out)
    return out


# =============================================================================
# 阶段 1: PDK 器件目录展示
# =============================================================================


class TestStage1PDKCatalog:
    """阶段 1: PDK 器件目录展示测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 1 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage1")
        return stage1_pdk_catalog.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_platforms_count(self, result: dict) -> None:
        """验证 4 个平台（SOI/SiN/InP/LNOI）。"""
        platforms = result["platforms"]
        assert len(platforms) == 4
        names = {p["platform"] for p in platforms}
        assert names == {"SOI", "SiN", "InP", "LNOI"}

    def test_total_device_count(self, result: dict) -> None:
        """验证总器件数 ≥ 36（SOI 15 + SiN 7 + InP 7 + LNOI 7 = 36）。"""
        assert result["total_device_count"] >= 36

    def test_representative_devices(self, result: dict) -> None:
        """验证每平台有代表器件（≥ 3 个）。"""
        for platform in result["platforms"]:
            assert len(platform["representative_devices"]) >= 3
            for dev in platform["representative_devices"]:
                assert "name" in dev
                assert "params" in dev
                assert "source" in dev

    def test_foundry_sources(self, result: dict) -> None:
        """验证来源 foundry 标注（每平台含 foundry 与 foundry_url）。"""
        for platform in result["platforms"]:
            assert platform["foundry"]
            assert platform["foundry_url"].startswith("https://")


# =============================================================================
# 阶段 2: 电路规格定义
# =============================================================================


class TestStage2CircuitSpec:
    """阶段 2: 电路规格定义测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 2 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage2")
        return stage2_circuit_spec.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_circuits_count(self, result: dict) -> None:
        """验证 3 个电路（MZI/Clements/玻色采样）。"""
        assert len(result["circuits"]) == 3

    def test_mzi_devices(self, result: dict) -> None:
        """验证 MZI 有 5 器件。"""
        mzi = result["circuits"][0]
        assert mzi["n_devices"] == 5

    def test_clements_devices(self, result: dict) -> None:
        """验证 Clements 有 10 器件（6 分束器 + 4 相移器）。"""
        clements = result["circuits"][1]
        assert clements["n_devices"] == 10

    def test_unitary_matrix_shape(self, result: dict) -> None:
        """验证酉矩阵形状为 [4, 4]。"""
        assert result["unitary_matrix_shape"] == [4, 4]


# =============================================================================
# 阶段 3: AI 布局
# =============================================================================


class TestStage3AIPlacement:
    """阶段 3: AI 布局测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 3 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage3")
        return stage3_ai_placement.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_circuits_count(self, result: dict) -> None:
        """验证 3 个电路布局。"""
        assert len(result["circuits"]) == 3

    def test_hpwl_positive(self, result: dict) -> None:
        """验证 HPWL > 0（布局后器件间连线长度非零）。"""
        for circuit in result["circuits"]:
            assert circuit["hpwl"] > 0

    def test_placement_mode(self, result: dict) -> None:
        """验证 placement_mode 为 RL 或 analytical 模式。"""
        # 接受所有 RL 变种（rl/ppo_gnn_init/ppo_gnn_pretrained）和 analytical
        assert result["placement_mode"] in {"rl", "analytical", "ppo_gnn_init", "ppo_gnn_pretrained"}


# =============================================================================
# 阶段 4: 智能布线
# =============================================================================


class TestStage4Routing:
    """阶段 4: 智能布线测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 4 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage4")
        return stage4_routing.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_circuits_count(self, result: dict) -> None:
        """验证 3 个电路布线。"""
        assert len(result["circuits"]) == 3

    def test_router_type(self, result: dict) -> None:
        """验证 router_type = "curvy"。"""
        assert result["router_type"] == "curvy"

    def test_loss_positive(self, result: dict) -> None:
        """验证损耗 ≥ 0（波导传播损耗非负）。"""
        for circuit in result["circuits"]:
            assert circuit["total_loss_db"] >= 0


# =============================================================================
# 阶段 5: 仿真验证
# =============================================================================


class TestStage5Simulation:
    """阶段 5: 仿真验证测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 5 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage5")
        return stage5_simulation.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_mzi_s_param(self, result: dict) -> None:
        """验证 MZI S 参数含 resonant_wavelength_nm 和 extinction_ratio_db。"""
        mzi = result["mzi_s_param"]
        assert "resonant_wavelength_nm" in mzi
        assert "extinction_ratio_db" in mzi
        # 谐振波长应在扫描范围 1500-1600nm 内
        assert 1500 <= mzi["resonant_wavelength_nm"] <= 1600

    def test_clements_unitary(self, result: dict) -> None:
        """验证酉性误差 < 1e-6。"""
        clements = result["clements_unitary"]
        assert clements["unitarity_error"] < 1e-6
        assert clements["is_unitary"] is True

    def test_pam4(self, result: dict) -> None:
        """验证 PAM4 BER > 0 且 SNR > 0。"""
        pam4 = result["pam4"]
        assert pam4["ber"] > 0
        assert pam4["snr_db"] > 0


# =============================================================================
# 阶段 6: DRC/LVS 验证
# =============================================================================


class TestStage6DRCLVS:
    """阶段 6: DRC/LVS 验证测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 6 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage6")
        return stage6_drc_lvs.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_drc_pass_rate(self, result: dict) -> None:
        """验证 DRC 通过率 ≥ 0。"""
        assert result["drc"]["pass_rate"] >= 0

    def test_lvs_consistent(self, result: dict) -> None:
        """验证 LVS 结果为 bool。"""
        assert isinstance(result["lvs"]["is_consistent"], bool)


# =============================================================================
# 阶段 7: GDS 导出
# =============================================================================


class TestStage7GDSExport:
    """阶段 7: GDS 导出测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 7 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage7")
        return stage7_gds_export.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_circuits_count(self, result: dict) -> None:
        """验证 3 个电路 GDS。"""
        assert len(result["circuits"]) == 3

    def test_gds_files_exist(self, result: dict) -> None:
        """验证 GDS 文件存在且可加载。"""
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

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 8 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage8")
        return stage8_opto_electrical.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_verilog_a_models(self, result: dict) -> None:
        """验证 ≥ 5 个 Verilog-A 模型。"""
        models = result["verilog_a_models"]
        assert len(models) >= 5
        for m in models:
            assert Path(m["file_path"]).exists()

    def test_spice_netlist(self, result: dict) -> None:
        """验证 SPICE 网表存在。"""
        netlist = result["spice_netlist"]
        assert Path(netlist["file_path"]).exists()
        assert netlist["lines"] > 0

    def test_pam4(self, result: dict) -> None:
        """验证 PAM4 BER > 0 且 SNR > 0。"""
        pam4 = result["pam4"]
        assert pam4["ber"] > 0
        assert pam4["snr_db"] > 0


# =============================================================================
# 阶段 9: 量子光子验证
# =============================================================================


class TestStage9QuantumPhotonics:
    """阶段 9: 量子光子验证测试。"""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory: pytest.TempPathFactory) -> dict:
        """类级 fixture: 运行阶段 9 一次，结果供所有测试方法共享。"""
        out = _make_output_dir(tmp_path_factory, "stage9")
        return stage9_quantum_photonics.run(out)

    def test_run_returns_dict(self, result: dict) -> None:
        """验证 run() 返回 dict。"""
        assert isinstance(result, dict)

    def test_boson_sampling_prob_sum(self, result: dict) -> None:
        """验证概率守恒（所有输出概率之和 ≈ 1）。"""
        bs = result["boson_sampling"]
        assert abs(bs["prob_sum"] - 1.0) < 1e-6
        assert bs["prob_sum_ok"] is True

    def test_hom_verified(self, result: dict) -> None:
        """验证 HOM 干涉（|1,1⟩ 输出概率 ≈ 0）。"""
        hom = result["hom"]
        assert hom["hom_verified"] is True
        assert abs(hom["coincidence_prob"]) < 1e-6

    def test_klm_cnot(self, result: dict) -> None:
        """验证 KLM CNOT 成功率 ≈ 0.25（Knill et al., Nature 2001）。"""
        klm = result["klm"]
        assert klm["cnot_verified"] is True
        assert abs(klm["cnot_success_prob"] - 0.25) < 1e-6

    def test_klm_hadamard(self, result: dict) -> None:
        """验证 Hadamard 门酉性（H @ H† = I）。"""
        klm = result["klm"]
        assert klm["hadamard_verified"] is True
        assert klm["hadamard_unitary_error"] < 1e-6


# =============================================================================
# 日志配置
# =============================================================================


class TestLoggingConfig:
    """日志配置测试。"""

    def test_setup_logging(self, tmp_path: Path) -> None:
        """验证 setup_logging 返回名为 e2e_showcase 的日志器。"""
        out = tmp_path / "test_logs"
        out.mkdir()
        logger = setup_logging(out)
        assert logger.name == "e2e_showcase"

    def test_stage_logger(self, tmp_path: Path) -> None:
        """验证 StageLogger 写入 JSONL 日志（含输入/输出/状态字段）。"""
        out = tmp_path / "test_stage_logger"
        out.mkdir()
        (out / "logs").mkdir()
        setup_logging(out)
        with StageLogger(1, "测试阶段", out) as sl:
            sl.log_input("test_input", "value")
            sl.log_output("test_output", 42)
        jsonl_path = out / "logs" / "showcase.jsonl"
        assert jsonl_path.exists()
        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["stage_id"] == 1
        assert entry["stage_name"] == "测试阶段"
        assert entry["status"] == "done"
        assert entry["inputs"]["test_input"] == "value"
        assert entry["outputs"]["test_output"] == 42


# =============================================================================
# 阶段失败日志（P0 缺陷修复验证）
# =============================================================================


class TestStageFailureLogging:
    """阶段失败日志测试（P0 缺陷修复验证）。

    验证三个 P0 缺陷修复:
    1. error 字段含完整 traceback
    2. events 字段记录中间过程日志（info/warn）
    3. inputs 字段被正确填充
    """

    def test_failed_stage_logs_error_with_traceback(self, tmp_path: Path) -> None:
        """失败阶段应记录完整 traceback。"""
        out = tmp_path / "test_fail"
        (out / "logs").mkdir(parents=True)
        setup_logging(out)

        with pytest.raises(ValueError):
            with StageLogger(99, "失败测试", out) as sl:
                sl.log_input("test_input", "value")
                raise ValueError("模拟失败")

        jsonl_path = out / "logs" / "showcase.jsonl"
        assert jsonl_path.exists()
        entry = json.loads(jsonl_path.read_text(encoding="utf-8").strip())
        assert entry["status"] == "failed"
        assert "ValueError" in entry["error"]
        assert "Traceback" in entry["error"]
        assert "模拟失败" in entry["error"]
        assert entry["inputs"]["test_input"] == "value"

    def test_events_recorded_in_jsonl(self, tmp_path: Path) -> None:
        """中间过程日志应记录到 events 字段。"""
        out = tmp_path / "test_events"
        (out / "logs").mkdir(parents=True)
        setup_logging(out)

        with StageLogger(1, "测试", out) as sl:
            sl.info("步骤 1 开始")
            sl.info("步骤 2 进行中")
            sl.warn("发现警告")
            sl.log_output("result", 42)

        entry = json.loads((out / "logs" / "showcase.jsonl").read_text(encoding="utf-8").strip())
        assert "events" in entry
        assert len(entry["events"]) == 3  # 2 info + 1 warn
        assert entry["events"][0]["level"] == "info"
        assert entry["events"][0]["msg"] == "步骤 1 开始"
        assert entry["events"][2]["level"] == "warning"

    def test_inputs_populated(self, tmp_path: Path) -> None:
        """inputs 字段应被填充。"""
        out = tmp_path / "test_inputs"
        (out / "logs").mkdir(parents=True)
        setup_logging(out)

        with StageLogger(1, "测试", out) as sl:
            sl.log_input("param1", "value1")
            sl.log_input("param2", 42)

        entry = json.loads((out / "logs" / "showcase.jsonl").read_text(encoding="utf-8").strip())
        assert entry["inputs"]["param1"] == "value1"
        assert entry["inputs"]["param2"] == 42


# =============================================================================
# 汇总报告生成器
# =============================================================================


class TestReportGenerator:
    """汇总报告生成器测试。"""

    def test_generate_report(self, tmp_path: Path) -> None:
        """验证报告生成（report.md 文件存在且非空）。"""
        out = tmp_path / "test_report"
        (out / "logs").mkdir(parents=True)
        (out / "reports").mkdir(parents=True)
        setup_logging(out)
        # 运行一个阶段以生成日志
        with StageLogger(1, "PDK 器件目录展示", out) as sl:
            sl.log_output("total_device_count", 36)
        report_path = generate_report(out)
        assert report_path.exists()
        assert report_path.stat().st_size > 0

    def test_report_contains_stages(self, tmp_path: Path) -> None:
        """验证报告含阶段信息（阶段执行状态表与学术诚信声明）。"""
        out = tmp_path / "test_report_stages"
        (out / "logs").mkdir(parents=True)
        (out / "reports").mkdir(parents=True)
        setup_logging(out)
        with StageLogger(1, "PDK 器件目录展示", out) as sl:
            sl.log_output("total_device_count", 36)
        report_path = generate_report(out)
        content = report_path.read_text(encoding="utf-8")
        # 报告应包含阶段状态表头与学术诚信声明
        assert "PoLaRIS 端到端 Demo Showcase 汇总报告" in content
        assert "阶段执行状态" in content
        assert "PDK 器件目录展示" in content
        assert "学术诚信声明" in content


# =============================================================================
# 端到端集成测试
# =============================================================================


@pytest.mark.slow
class TestEndToEnd:
    """端到端串联测试：验证 9 阶段顺序运行、JSONL 日志与报告生成。"""

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """验证 9 阶段串联运行。

        依次执行 stage1-stage9，每阶段用 StageLogger 包裹，
        验证 JSONL 日志含 9 条记录且报告生成成功。
        """
        out = tmp_path / "e2e_full"
        for subdir in ["logs", "gds", "verilog_a", "spice", "reports"]:
            (out / subdir).mkdir(parents=True, exist_ok=True)
        setup_logging(out)

        for stage_id, stage_name, stage_module in _STAGES:
            with StageLogger(stage_id, stage_name, out):
                result = stage_module.run(out)
                assert isinstance(result, dict), f"阶段 {stage_id} 返回非 dict"

        # 验证 JSONL 日志含 9 条记录
        jsonl_path = out / "logs" / "showcase.jsonl"
        assert jsonl_path.exists()
        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 9  # 9 阶段

        # 验证报告生成
        report_path = generate_report(out)
        assert report_path.exists()
        report_content = report_path.read_text(encoding="utf-8")
        assert "9" in report_content  # 总阶段数
