"""训练数据集生成器和加载器测试。"""

import json
import tempfile
from pathlib import Path

import yaml

from polaris.data.data_loader import (
    load_directory,
    load_gdsfactory_yaml,
    load_pic_ir,
    load_picbench,
)
from polaris.data.dataset_generator import (
    STANDARD_DEVICES,
    _mzi_circuit,
    _mzi_lattice_circuit,
    _random_circuit,
    _ring_filter_circuit,
    _splitter_tree_circuit,
    _switch_circuit,
    generate_dataset,
    generate_layout,
)


class TestDeviceSpec:
    """DeviceSpec 测试。"""

    def test_standard_devices_exist(self):
        assert len(STANDARD_DEVICES) >= 10

    def test_mzi_device(self):
        mzi = STANDARD_DEVICES["mzi"]
        assert mzi.device_type == "mzi"
        assert mzi.width_um > 0
        assert len(mzi.ports) >= 2


class TestCircuitTemplates:
    """电路模板测试。"""

    def test_mzi_circuit(self):
        c = _mzi_circuit()
        assert c.name == "mzi"
        assert len(c.devices) == 6
        assert len(c.connections) == 6

    def test_ring_filter_circuit(self):
        c = _ring_filter_circuit()
        assert len(c.devices) == 3
        assert len(c.connections) == 2

    def test_mzi_lattice_circuit(self):
        c = _mzi_lattice_circuit("test", 3)
        assert len(c.devices) > 5
        assert len(c.connections) > 5

    def test_splitter_tree_circuit(self):
        c = _splitter_tree_circuit("test", 2)
        assert len(c.devices) > 5

    def test_switch_circuit(self):
        c = _switch_circuit("test", 4)
        assert len(c.devices) == 6  # gc_in + 4 mzi + gc_out

    def test_random_circuit(self):
        c = _random_circuit("test", 10, seed=42)
        assert len(c.devices) == 10
        assert len(c.connections) >= 9


class TestGenerateLayout:
    """布局生成测试。"""

    def test_generate_layout(self):
        c = _mzi_circuit()
        layout = generate_layout(c, seed=0)
        assert len(layout) == len(c.devices)
        for dev in c.devices:
            assert dev.name in layout
            assert "x" in layout[dev.name]
            assert "y" in layout[dev.name]

    def test_layout_within_canvas(self):
        c = _mzi_circuit()
        layout = generate_layout(c, seed=1)
        for dev in c.devices:
            pos = layout[dev.name]
            assert pos["x"] >= 0
            assert pos["y"] >= 0


class TestGenerateDataset:
    """数据集生成测试。"""

    def test_generate_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats = generate_dataset(tmp, n_variations=2, canvas_sizes=[(500.0, 500.0)])
            assert stats["total_circuits"] > 0
            assert stats["total_variations"] > 0
            # 检查文件存在
            files = list(Path(tmp).glob("*.json"))
            assert len(files) > 0
            # 检查 JSON 可解析
            for f in files:
                data = json.loads(f.read_text(encoding="utf-8"))
                assert isinstance(data, dict)


class TestDataLoader:
    """数据加载器测试。"""

    def test_load_pic_ir(self):
        with tempfile.TemporaryDirectory() as tmp:
            pic_ir_data = {
                "name": "test_pic",
                "instances": [
                    {
                        "name": "mzi1",
                        "cell_type": "mzi",
                        "width": 200.0,
                        "height": 50.0,
                        "ports": [
                            {
                                "name": "o1",
                                "x": 0.0,
                                "y": 25.0,
                                "direction": "E",
                            },
                            {
                                "name": "o2",
                                "x": 200.0,
                                "y": 25.0,
                                "direction": "W",
                            },
                        ],
                    },
                    {
                        "name": "gc1",
                        "cell_type": "grating_coupler",
                        "width": 20.0,
                        "height": 20.0,
                        "ports": [
                            {
                                "name": "o1",
                                "x": 10.0,
                                "y": 0.0,
                                "direction": "N",
                            },
                        ],
                    },
                ],
                "nets": [
                    {"src": "gc1,o1", "dst": "mzi1,o1"},
                ],
                "canvas": {"width": 1000.0, "height": 1000.0},
            }
            fp = Path(tmp) / "test.pic.yml"
            fp.write_text(
                yaml.dump(pic_ir_data),
                encoding="utf-8",
            )
            c = load_pic_ir(fp)
            assert c.name == "test_pic"
            assert len(c.devices) == 2
            assert len(c.connections) == 1

    def test_load_gdsfactory_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            gf_data = {
                "name": "test_gf",
                "instances": {
                    "mzi1": {"component": "mzi", "settings": {"length": 200.0}},
                    "gc1": {"component": "grating_coupler", "settings": {}},
                },
                "connections": [
                    {"source": "gc1,o1", "destination": "mzi1,o1"},
                ],
            }
            import yaml

            fp = Path(tmp) / "test.pic.yml"
            fp.write_text(yaml.dump(gf_data), encoding="utf-8")
            c = load_gdsfactory_yaml(fp)
            assert c.name == "test_gf"
            assert len(c.devices) == 2
            assert len(c.connections) == 1

    def test_load_picbench(self):
        with tempfile.TemporaryDirectory() as tmp:
            pb_data = {
                "name": "test_pb",
                "components": [
                    {"name": "mzi1", "type": "mzi", "width": 200.0, "height": 50.0},
                ],
                "connections": [
                    {"source": "gc1,o1", "destination": "mzi1,o1"},
                ],
            }
            fp = Path(tmp) / "test.json"
            fp.write_text(json.dumps(pb_data), encoding="utf-8")
            c = load_picbench(fp)
            assert c.name == "test_pb"
            assert len(c.devices) == 1

    def test_load_directory_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            circuits = load_directory(tmp)
            assert circuits == []

    def test_load_directory_nonexistent(self):
        circuits = load_directory("/nonexistent/path")
        assert circuits == []
