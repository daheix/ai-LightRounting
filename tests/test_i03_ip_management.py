"""I03 IP 管理验收测试（Workspace/IP 注册/版本管理）。

覆盖验收标准：
- M1: Workspace 目录结构
- M2: IP 注册与检索
- M3: 版本管理

学术来源:
- IPKISS 项目结构: https://docs.lucedaphotonics.com/
- Cadence ADE-XL 运行目录: https://docs.cadence.com/
- Synopsys ICC2 工作目录: https://www.synopsys.com/
- Ansys Lumerical 项目目录: https://www.ansys.com/products/photonics
- gdsfactory PDK 注册: https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

import pytest

from polaris.flow.ipkiss_flow import (
    CircuitModelView,
    IPKISSPCell,
    IPKISSPDKBridge,
    LayoutView,
    NetlistView,
)
from polaris.flow.workspace import Workspace
from polaris.pdk.catalog import DeviceCatalog
from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port

# =============================================================================
# M1: Workspace 目录结构测试
# =============================================================================


class TestWorkspaceDirectoryStructure:
    """Workspace 目录结构正确性测试。"""

    def test_workspace_base_path(self, tmp_path):
        """Workspace base_path 正确。"""
        ws = Workspace(str(tmp_path), "ip_test_1")
        assert ws.base_path == tmp_path / "ip_test_1"

    def test_workspace_creates_all_subdirs(self, tmp_path):
        """Workspace 创建所有必需子目录。"""
        Workspace(str(tmp_path), "ip_test_2")
        base = tmp_path / "ip_test_2"
        required_dirs = [
            "inputs",
            "logs",
            "stages",
            "reports",
            "gds",
        ]
        for d in required_dirs:
            assert (base / d).is_dir(), f"缺少目录: {d}"

    def test_workspace_creates_all_stage_dirs(self, tmp_path):
        """Workspace 创建所有 10 个阶段子目录。"""
        Workspace(str(tmp_path), "ip_test_3")
        stages_dir = tmp_path / "ip_test_3" / "stages"
        expected_slugs = [
            "stage1_pdk", "stage2_circuit", "stage3_placement", "stage4_routing",
            "stage5_simulation", "stage6_drc_lvs", "stage7_gds",
            "stage8_opto_electrical", "stage9_quantum", "stage10_inverse",
        ]
        for slug in expected_slugs:
            assert (stages_dir / slug).is_dir(), f"缺少阶段目录: {slug}"

    def test_workspace_stage_dir_method(self, tmp_path):
        """stage_dir 方法返回正确路径。"""
        ws = Workspace(str(tmp_path), "ip_test_4")
        path = ws.stage_dir("stage1_pdk")
        assert path == tmp_path / "ip_test_4" / "stages" / "stage1_pdk"

    def test_workspace_gds_path_method(self, tmp_path):
        """gds_path 方法返回正确路径。"""
        ws = Workspace(str(tmp_path), "ip_test_5")
        path = ws.gds_path("my_layout.gds")
        assert path == tmp_path / "ip_test_5" / "gds" / "my_layout.gds"

    def test_workspace_multiple_jobs_isolated(self, tmp_path):
        """多个 Workspace 相互隔离。"""
        ws1 = Workspace(str(tmp_path), "job_a")
        ws2 = Workspace(str(tmp_path), "job_b")
        ws1.write_stage_output("stage1_pdk", {"job": "a"})
        ws2.write_stage_output("stage1_pdk", {"job": "b"})
        assert ws1.read_stage_output("stage1_pdk")["job"] == "a"
        assert ws2.read_stage_output("stage1_pdk")["job"] == "b"


# =============================================================================
# M2: IP 注册与检索测试
# =============================================================================


class TestIPRegistration:
    """IP 注册与检索测试。"""

    def test_ipkiss_pcell_creation(self):
        """IPKISSPCell 基本创建。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 100.0})
        assert cell.name == "wg1"
        assert cell.cell_type == "waveguide"
        assert cell.params["length"] == 100.0

    def test_ipkiss_pcell_auto_ports(self):
        """PCell 自动补全端口列表。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide")
        assert "in" in cell.ports
        assert "out" in cell.ports

    def test_ipkiss_pcell_custom_ports(self):
        """PCell 自定义端口优先。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide", ports=["p1", "p2"])
        assert cell.ports == ["p1", "p2"]

    def test_ipkiss_pdk_bridge_register(self):
        """PDK Bridge 注册 PCell。"""
        bridge = IPKISSPDKBridge()
        cell = IPKISSPCell(name="wg_test", cell_type="waveguide")
        bridge.register(cell)
        assert "wg_test" in bridge.cell_registry

    def test_ipkiss_pdk_bridge_get_cell(self):
        """PDK Bridge 按名称获取 PCell。"""
        bridge = IPKISSPDKBridge()
        cell = IPKISSPCell(name="wg_test", cell_type="waveguide", params={"length": 50.0})
        bridge.register(cell)
        retrieved = bridge.get_cell("wg_test")
        assert retrieved.name == "wg_test"
        assert retrieved.params["length"] == 50.0

    def test_ipkiss_pdk_bridge_get_nonexistent_raises(self):
        """获取未注册 PCell 抛出 KeyError。"""
        bridge = IPKISSPDKBridge()
        with pytest.raises(KeyError, match="未注册"):
            bridge.get_cell("nonexistent")

    def test_ipkiss_pdk_bridge_register_standard_cells(self):
        """注册标准器件库。"""
        bridge = IPKISSPDKBridge()
        names = bridge.register_standard_cells()
        assert len(names) >= 5
        assert "wg1" in names
        assert "mmi1" in names

    def test_ipkiss_pdk_bridge_list_cells(self):
        """列出所有已注册 PCell。"""
        bridge = IPKISSPDKBridge()
        bridge.register_standard_cells()
        listed = bridge.list_cells()
        assert len(listed) >= 5
        assert "wg1" in listed

    def test_netlist_view_generate(self):
        """NetlistView 生成网表。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide")
        view = NetlistView(cell)
        netlist = view.generate()
        assert "instances" in netlist
        assert "connections" in netlist
        assert "ports" in netlist
        assert "wg1" in netlist["instances"]

    def test_layout_view_generate(self):
        """LayoutView 生成版图。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 100.0, "width": 0.5})
        view = LayoutView(cell)
        layout = view.generate()
        assert "elements" in layout
        assert "bbox" in layout
        assert len(layout["elements"]) > 0


# =============================================================================
# M3: 版本管理与 CircuitModelView 测试
# =============================================================================


class TestVersionManagement:
    """版本管理与电路模型测试。"""

    def test_circuit_model_view_returns_model(self):
        """CircuitModelView 生成 S 参数模型。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 100.0})
        view = CircuitModelView(cell)
        model = view.generate()
        assert model is not None
        assert callable(model)

    def test_circuit_model_view_callable(self):
        """生成的模型可调用并返回 S 参数。"""
        cell = IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 100.0})
        view = CircuitModelView(cell)
        model = view.generate()
        result = model(wl=1.55)
        assert isinstance(result, dict)

    def test_circuit_model_view_unknown_type_returns_none(self):
        """未知器件类型返回 None。"""
        cell = IPKISSPCell(name="unknown1", cell_type="unknown_device")
        view = CircuitModelView(cell)
        model = view.generate()
        assert model is None

    def test_pcell_multiview_consistency(self):
        """同一 PCell 的多个视图一致。"""
        cell = IPKISSPCell(
            name="mmi_test",
            cell_type="mmi_1x2",
            params={"insertion_loss_db": 0.3},
        )
        netlist = cell.netlist_view.generate()
        layout = cell.layout_view.generate()
        model = cell.circuit_model_view.generate()
        assert netlist["instances"]["mmi_test"] == "mmi_1x2"
        assert len(layout["elements"]) > 0
        assert model is not None

    def test_device_catalog_registration(self):
        """DeviceCatalog 注册与检索。"""
        catalog = DeviceCatalog()
        port = Port(name="o1", x=0.0, y=0.0, direction=Direction.EAST, waveguide_type="optical", width=0.5)
        bbox = BoundingBox(xmin=0.0, ymin=0.0, xmax=10.0, ymax=10.0)
        device = Device(
            device_id="test_dev",
            name="test_device",
            platform="SOI",
            category="passive",
            ports=[port],
            bbox=bbox,
        )
        catalog.register(device)
        retrieved = catalog.get("test_dev")
        assert retrieved.device_id == "test_dev"

    def test_device_catalog_list_by_platform(self):
        """按平台检索器件。"""
        catalog = DeviceCatalog()
        catalog.register_all_builtin()
        soi_devices = catalog.list_by_platform("SOI")
        assert len(soi_devices) > 0
        for d in soi_devices:
            assert d.platform == "SOI"

    def test_workspace_persists_ip_data(self, tmp_path):
        """Workspace 持久化 IP 数据。"""
        ws = Workspace(str(tmp_path), "ip_persist_1")
        ip_data = {
            "ip_name": "my_mzi",
            "version": "1.0.0",
            "devices": ["wg1", "mmi1"],
            "connections": 2,
        }
        ws.write_stage_output("stage2_circuit", ip_data)
        read_back = ws.read_stage_output("stage2_circuit")
        assert read_back["ip_name"] == "my_mzi"
        assert read_back["version"] == "1.0.0"

    def test_workspace_job_metadata_versioning(self, tmp_path):
        """作业元数据支持版本信息。"""
        ws = Workspace(str(tmp_path), "ip_version_1")
        meta = {
            "job_id": "ip_version_1",
            "status": "completed",
            "version": "2.1.0",
            "pdk_version": "SOI_220nm_v1.0",
        }
        ws.write_job_metadata(meta)
        read_back = ws.read_job_metadata()
        assert read_back is not None
        assert read_back["version"] == "2.1.0"
        assert read_back["pdk_version"] == "SOI_220nm_v1.0"
