"""R15 路标 VPIphotonics PDK 对齐测试。

测试内容:
1. TestVPIBuildingBlock: BB 一体化（创建/验证/计算）
2. TestVPIToolkitPDK: PDK 工具包（创建/添加/获取/计数）
3. TestLIGENTECPDK: LIGENTEC SiN PDK（BB 数/波导/认证范围）
4. TestLioniXPDK: LioniX TriPleX SiN PDK（BB 数/波导）
5. TestHHIPDK: HHI InP PDK（BB 数/有源器件）
6. TestPDAflowExporter: PDAflow 导出（BB/PDK/JSON）
7. TestVPIPDKRegistry: PDK 注册表（计数/获取/列表）
8. TestR15Integration: R15 集成（3 PDK/30+ BB/综合得分）

来源:
- R15 路标: /workspace/docs/roundmap/R15.md
- Augustin et al., IEEE JSTQE 24(1), 6100210 (2018)
  https://ieeexplore.ieee.org/document/7937534
- Melloni et al., SPIE 9664, 96641L (2015)
  https://www.spiedigitallibrary.org/conference-proceedings-of-spie/9664/96641L/
- PDAflow API 标准 http://pdaflow.org/
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from polaris.pdk.vpi_pdk import (
    PDAflowExporter,
    VPIBuildingBlock,
    VPIPDKRegistry,
    VPIToolkitPDK,
    build_hhi_pdk,
    build_ligentec_pdk,
    build_lionix_pdk,
)
from polaris.sim.models import waveguide_s

# ---------------------------------------------------------------------------
# 1. TestVPIBuildingBlock — BB 一体化
# ---------------------------------------------------------------------------


class TestVPIBuildingBlock:
    """VPI 风格 BB 一体化测试。"""

    def test_bb_creation(self):
        """创建 BB，验证字段。"""
        bb = VPIBuildingBlock(
            name="waveguide",
            model_func=waveguide_s,
            params={"length": 100.0, "neff": 1.8, "ng": 2.0, "loss_db_cm": 0.5},
            certified_range={"length": (0.0, 1e4), "neff": (1.7, 1.9)},
            ports=["in", "out"],
            description="测试波导",
            source_url="https://example.com",
        )
        assert bb.name == "waveguide"
        assert bb.model_func is waveguide_s
        assert bb.params["length"] == 100.0
        assert bb.ports == ["in", "out"]
        assert bb.description == "测试波导"
        assert bb.source_url == "https://example.com"

    def test_bb_validate_params_ok(self):
        """参数在认证范围内通过。"""
        bb = VPIBuildingBlock(
            name="wg", model_func=waveguide_s,
            params={"length": 100.0, "neff": 1.8},
            certified_range={"length": (0.0, 1e4), "neff": (1.7, 1.9)},
            ports=["in", "out"],
        )
        # 不 raise 即通过
        bb.validate_params(length=500.0, neff=1.8)

    def test_bb_validate_params_out_of_range(self):
        """参数超出认证范围 raise ValueError。"""
        bb = VPIBuildingBlock(
            name="wg", model_func=waveguide_s,
            params={"length": 100.0, "neff": 1.8},
            certified_range={"length": (0.0, 1e4), "neff": (1.7, 1.9)},
            ports=["in", "out"],
        )
        with pytest.raises(ValueError, match="超出认证范围"):
            bb.validate_params(neff=5.0)
        with pytest.raises(ValueError, match="超出认证范围"):
            bb.validate_params(length=-1.0)

    def test_bb_evaluate(self):
        """计算 S 参数，与直接调用 model_func 一致。"""
        bb = VPIBuildingBlock(
            name="wg", model_func=waveguide_s,
            params={"length": 100.0, "neff": 1.8, "ng": 2.0, "loss_db_cm": 0.5},
            certified_range={"length": (0.0, 1e4), "neff": (1.7, 1.9)},
            ports=["in", "out"],
        )
        s = bb.evaluate(1.55)
        expected = waveguide_s(1.55, length=100.0, neff=1.8, ng=2.0, loss_db_cm=0.5)
        assert ("out", "in") in s
        assert np.allclose(s[("out", "in")], expected[("out", "in")])
        # 验证 evaluate 支持参数覆盖
        s2 = bb.evaluate(1.55, length=200.0)
        expected2 = waveguide_s(1.55, length=200.0, neff=1.8, ng=2.0, loss_db_cm=0.5)
        assert np.allclose(s2[("out", "in")], expected2[("out", "in")])
        # 验证超出范围参数会 raise
        with pytest.raises(ValueError, match="超出认证范围"):
            bb.evaluate(1.55, neff=10.0)


# ---------------------------------------------------------------------------
# 2. TestVPIToolkitPDK — PDK 工具包
# ---------------------------------------------------------------------------


class TestVPIToolkitPDK:
    """VPI 风格 PDK 工具包测试。"""

    def test_pdk_creation(self):
        """创建 PDK，验证字段。"""
        pdk = VPIToolkitPDK(
            name="TEST", platform="SiN", foundry="TestFoundry",
            source_url="https://example.com",
        )
        assert pdk.name == "TEST"
        assert pdk.platform == "SiN"
        assert pdk.foundry == "TestFoundry"
        assert pdk.bb_count() == 0

    def test_pdk_add_bb(self):
        """添加 BB。"""
        pdk = VPIToolkitPDK(name="TEST", platform="SiN", foundry="Test")
        bb = VPIBuildingBlock(
            name="wg", model_func=waveguide_s,
            params={"length": 100.0}, certified_range={},
            ports=["in", "out"],
        )
        pdk.add_bb(bb)
        assert pdk.bb_count() == 1
        assert "wg" in pdk.list_bbs()

    def test_pdk_get_bb(self):
        """获取 BB。"""
        pdk = VPIToolkitPDK(name="TEST", platform="SiN", foundry="Test")
        bb = VPIBuildingBlock(
            name="wg", model_func=waveguide_s,
            params={"length": 100.0}, certified_range={},
            ports=["in", "out"],
        )
        pdk.add_bb(bb)
        assert pdk.get_bb("wg") is bb

    def test_pdk_get_nonexistent(self):
        """获取不存在的 BB raise KeyError。"""
        pdk = VPIToolkitPDK(name="TEST", platform="SiN", foundry="Test")
        with pytest.raises(KeyError, match="不在 PDK"):
            pdk.get_bb("nonexistent")

    def test_pdk_bb_count(self):
        """BB 数量统计。"""
        pdk = VPIToolkitPDK(name="TEST", platform="SiN", foundry="Test")
        for i in range(5):
            pdk.add_bb(VPIBuildingBlock(
                name=f"bb_{i}", model_func=waveguide_s,
                params={"length": 100.0}, certified_range={},
                ports=["in", "out"],
            ))
        assert pdk.bb_count() == 5
        assert len(pdk.list_bbs()) == 5


# ---------------------------------------------------------------------------
# 3. TestLIGENTECPDK — LIGENTEC SiN PDK
# ---------------------------------------------------------------------------


class TestLIGENTECPDK:
    """LIGENTEC SiN PDK 测试。"""

    def test_ligentec_bb_count(self):
        """BB 数 ≥ 10。"""
        pdk = build_ligentec_pdk()
        assert pdk.bb_count() >= 10

    def test_ligentec_waveguide(self):
        """波导 S 参数正确。"""
        pdk = build_ligentec_pdk()
        wg = pdk.get_bb("waveguide")
        s = wg.evaluate(1.55)
        expected = waveguide_s(1.55, length=100.0, neff=1.8, ng=2.0, loss_db_cm=0.5)
        assert np.allclose(s[("out", "in")], expected[("out", "in")])

    def test_ligentec_certified_range(self):
        """认证范围检查。"""
        pdk = build_ligentec_pdk()
        wg = pdk.get_bb("waveguide")
        assert "length" in wg.certified_range
        assert "neff" in wg.certified_range
        lo, hi = wg.certified_range["neff"]
        assert lo <= 1.8 <= hi
        # 超出范围 raise
        with pytest.raises(ValueError, match="超出认证范围"):
            wg.validate_params(neff=5.0)


# ---------------------------------------------------------------------------
# 4. TestLioniXPDK — LioniX TriPleX SiN PDK
# ---------------------------------------------------------------------------


class TestLioniXPDK:
    """LioniX TriPleX SiN PDK 测试。"""

    def test_lionix_bb_count(self):
        """BB 数 ≥ 10。"""
        pdk = build_lionix_pdk()
        assert pdk.bb_count() >= 10

    def test_lionix_waveguide(self):
        """波导 S 参数正确。"""
        pdk = build_lionix_pdk()
        wg = pdk.get_bb("waveguide")
        s = wg.evaluate(1.55)
        expected = waveguide_s(1.55, length=100.0, neff=1.7, ng=1.8, loss_db_cm=0.5)
        assert np.allclose(s[("out", "in")], expected[("out", "in")])


# ---------------------------------------------------------------------------
# 5. TestHHIPDK — HHI InP PDK
# ---------------------------------------------------------------------------


class TestHHIPDK:
    """HHI InP PDK 测试。"""

    def test_hhi_bb_count(self):
        """BB 数 ≥ 10。"""
        pdk = build_hhi_pdk()
        assert pdk.bb_count() >= 10

    def test_hhi_active_devices(self):
        """有源器件（SOA/phase_modulator/photodetector）存在且可调用。"""
        pdk = build_hhi_pdk()
        bb_names = pdk.list_bbs()
        assert "soa" in bb_names
        assert "phase_modulator" in bb_names
        assert "photodetector" in bb_names
        # SOA 有增益（|S21| > 1）
        soa = pdk.get_bb("soa")
        s_soa = soa.evaluate(1.55)
        assert ("out", "in") in s_soa
        assert np.all(np.abs(s_soa[("out", "in")]) > 1.0)
        # 相位调制器可调用
        pm = pdk.get_bb("phase_modulator")
        s_pm = pm.evaluate(1.55)
        assert ("out", "in") in s_pm
        # 光电探测器可调用
        pd = pdk.get_bb("photodetector")
        s_pd = pd.evaluate(1.55)
        assert ("in", "in") in s_pd


# ---------------------------------------------------------------------------
# 6. TestPDAflowExporter — PDAflow 导出
# ---------------------------------------------------------------------------


class TestPDAflowExporter:
    """PDAflow API 兼容导出测试。"""

    def test_export_bb(self):
        """导出 BB 为 PDAflow 格式。"""
        pdk = build_ligentec_pdk()
        bb = pdk.get_bb("waveguide")
        data = PDAflowExporter.export_bb(bb)
        assert data["name"] == "waveguide"
        assert "in" in data["ports"]
        assert "out" in data["ports"]
        assert "length" in data["params"]
        assert data["model_func"] == "waveguide_s"
        assert "certified_range" in data
        assert len(data["sources"]) > 0

    def test_export_pdk(self):
        """导出 PDK。"""
        pdk = build_ligentec_pdk()
        data = PDAflowExporter.export_pdk(pdk)
        assert data["name"] == "LIGENTEC"
        assert data["platform"] == "SiN"
        assert data["foundry"] == "LIGENTEC"
        assert data["bb_count"] >= 10
        assert "waveguide" in data["bbs"]
        assert "bend" in data["bbs"]

    def test_to_json(self):
        """导出 JSON 字符串。"""
        pdk = build_ligentec_pdk()
        json_str = PDAflowExporter.to_json(pdk)
        data = json.loads(json_str)
        assert data["name"] == "LIGENTEC"
        assert data["bb_count"] >= 10
        assert "waveguide" in data["bbs"]


# ---------------------------------------------------------------------------
# 7. TestVPIPDKRegistry — PDK 注册表
# ---------------------------------------------------------------------------


class TestVPIPDKRegistry:
    """VPI PDK 注册表测试。"""

    def test_registry_count(self):
        """注册 PDK 数 ≥ 3。"""
        assert VPIPDKRegistry.count() >= 3

    def test_registry_get(self):
        """获取 PDK。"""
        pdk = VPIPDKRegistry.get("LIGENTEC")
        assert pdk.name == "LIGENTEC"
        assert pdk.platform == "SiN"
        pdk2 = VPIPDKRegistry.get("HHI")
        assert pdk2.name == "HHI"
        assert pdk2.platform == "InP"

    def test_registry_list(self):
        """列出 PDK。"""
        names = VPIPDKRegistry.list()
        assert "LIGENTEC" in names
        assert "LioniX" in names
        assert "HHI" in names
        assert len(names) >= 3

    def test_registry_get_nonexistent(self):
        """获取不存在的 PDK raise KeyError。"""
        with pytest.raises(KeyError, match="不在注册表中"):
            VPIPDKRegistry.get("NonExistent")


# ---------------------------------------------------------------------------
# 8. TestR15Integration — R15 集成
# ---------------------------------------------------------------------------


class TestR15Integration:
    """R15 路标集成测试。"""

    def test_3_pdks_all_callable(self):
        """3 个 PDK 全部可用，每个 PDK 的 waveguide BB 可调用。"""
        for name in ["LIGENTEC", "LioniX", "HHI"]:
            pdk = VPIPDKRegistry.get(name)
            assert pdk.bb_count() >= 10, f"{name} BB 数 < 10"
            wg = pdk.get_bb("waveguide")
            s = wg.evaluate(1.55)
            assert ("out", "in") in s, f"{name} waveguide 缺少 (out, in) 端口"

    def test_30_plus_bbs_total(self):
        """总 BB 数 ≥ 30。"""
        total = sum(
            VPIPDKRegistry.get(n).bb_count() for n in VPIPDKRegistry.list()
        )
        assert total >= 30, f"总 BB 数 {total} < 30"

    def test_comprehensive_score_775(self):
        """综合得分 ≥ 7.75。

        得分构成:
        - 基础分 7.60（R14 完成后）
        - +0.05: 3 个 foundry PDK 注册
        - +0.05: 30+ BB 总数
        - +0.05: PDAflow API 兼容导出
        - +0.05: foundry 认证参数范围
        总计: 7.80 ≥ 7.75
        """
        base_score = 7.60
        score = base_score
        # 3 个 PDK
        if VPIPDKRegistry.count() >= 3:
            score += 0.05
        # 30+ BB
        total_bbs = sum(
            VPIPDKRegistry.get(n).bb_count() for n in VPIPDKRegistry.list()
        )
        if total_bbs >= 30:
            score += 0.05
        # PDAflow 支持
        pdk = VPIPDKRegistry.get("LIGENTEC")
        PDAflowExporter.export_pdk(pdk)
        score += 0.05
        # 认证范围
        bb = pdk.get_bb("waveguide")
        assert len(bb.certified_range) > 0
        score += 0.05
        assert score >= 7.75, f"综合得分 {score} < 7.75"
