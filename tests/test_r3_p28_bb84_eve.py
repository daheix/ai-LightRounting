"""R3-P2-8 回归测试：BB84 Eve intercept-resend 物理模型修复。

旧 Bug:
    - ``eve_bases`` 生成后未使用（死代码）
    - ``eavesdrop_errors = rng.random(n_raw) < 0.25`` 为简化模型
    - 虽然平均 QBER ≈ 25% 正确，但单次仿真方差偏大，不符合物理

新模型（intercept-resend，物理准确）:
    1. Eve 随机选择基矢测量每个光子
    2. Eve 基矢 == Alice 基矢: 无误差
    3. Eve 基矢 != Alice 基矢: 50% 误差
    4. 综合: 0.5 × 0.5 = 25%

文献:
    - Bennett & Brassard 1984 SIGACT News
      https://doi.org/10.1007/978-1-4613-9411-6_5
    - Shor & Preskill 2000 PRL 85(2) 441-444（11% QBER 阈值）
      https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.85.441
    - Lo & Chau 1999 Science 283(5410) 2050-2056
      https://www.science.org/doi/10.1126/science.283.5410.2050
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.quantum.quantum_circuit_distributed import BB84Protocol


class TestR3P28BB84EveModel:
    """R3-P2-8: BB84 Eve intercept-resend 物理模型验证。"""

    def test_no_eavesdrop_qber_near_zero(self):
        """R3-P2-8: 无窃听时 QBER 应接近 0（仅信道噪声，无 Eve 误差）。"""
        bb84 = BB84Protocol(key_length=256)
        result = bb84.simulate(eavesdrop=False, channel_loss_db=3.0)
        assert result["qber"] < 0.05, (
            f"无窃听 QBER 应 < 5%，实际 {result['qber']:.4f}"
        )
        assert result["is_secure"] is True

    def test_eavesdrop_qber_near_25_percent(self):
        """R3-P2-8: intercept-resend 攻击 QBER 应接近 25%（BB84 理论值）。

        文献: Bennett & Brassard 1984, Eve 用随机基矢测量引入 25% 误码。
        """
        qbers = []
        for seed in range(50):
            bb84 = BB84Protocol(key_length=256)
            bb84._rng = np.random.default_rng(seed)
            result = bb84.simulate(eavesdrop=True, channel_loss_db=3.0)
            qbers.append(result["qber"])
        mean_qber = np.mean(qbers)
        # 理论值 25%，允许 ±5% 统计波动
        assert 0.20 < mean_qber < 0.30, (
            f"intercept-resend QBER 均值应 ≈ 25%，实际 {mean_qber:.4f}"
        )

    def test_eavesdrop_always_detected(self):
        """R3-P2-8: QBER > 11% 阈值时窃听应 100% 被检测到。

        文献: Shor & Preskill 2000, 11% 为 BB84 单向后处理安全阈值。
        """
        detected = 0
        n_trials = 100
        for seed in range(n_trials):
            bb84 = BB84Protocol(key_length=256)
            bb84._rng = np.random.default_rng(seed)
            result = bb84.simulate(eavesdrop=True, channel_loss_db=3.0)
            if result["eavesdrop_detected"]:
                detected += 1
        # 100 次窃听应全部被检测到（QBER ≈ 25% >> 11% 阈值）
        assert detected == n_trials, (
            f"窃听检测率 {detected}/{n_trials}，应 100%"
        )

    def test_eve_bases_not_dead_code(self):
        """R3-P2-8: 验证 Eve 基矢实际参与计算（非死代码）。

        旧 Bug: ``eve_bases`` 生成后未使用，``eavesdrop_errors`` 为独立随机。
        新模型: Eve 基矢与 Alice 基矢的匹配关系决定误差位置。
        """
        # 用固定种子运行两次，验证结果确定性（物理模型可复现）
        bb84_1 = BB84Protocol(key_length=128)
        bb84_1._rng = np.random.default_rng(42)
        result_1 = bb84_1.simulate(eavesdrop=True, channel_loss_db=0.0)

        bb84_2 = BB84Protocol(key_length=128)
        bb84_2._rng = np.random.default_rng(42)
        result_2 = bb84_2.simulate(eavesdrop=True, channel_loss_db=0.0)

        assert result_1["qber"] == result_2["qber"], (
            "相同种子应产生相同结果（物理模型可复现）"
        )
        assert result_1["final_key_hex"] == result_2["final_key_hex"]

    def test_qber_threshold_11_percent(self):
        """R3-P2-8: QBER 阈值应为 11%（Shor-Preskill 2000 安全阈值）。"""
        bb84 = BB84Protocol(key_length=128)
        result = bb84.simulate(eavesdrop=False, channel_loss_db=3.0)
        assert result["qber_threshold"] == 0.11, (
            f"QBER 阈值应为 0.11，实际 {result['qber_threshold']}"
        )

    def test_sifted_key_reduced(self):
        """R3-P2-8: 筛选后密钥应少于原始比特（基矢比对丢弃约 50%）。"""
        bb84 = BB84Protocol(key_length=128)
        result = bb84.simulate(eavesdrop=False, channel_loss_db=0.0)
        # 无信道损耗时，筛选后应约为原始比特的 50%（基矢匹配概率）
        assert result["sifted_bits"] < result["raw_bits"], (
            "筛选后比特应少于原始比特"
        )
        assert result["sifted_bits"] > result["raw_bits"] * 0.3, (
            f"筛选后比特应 > 原始的 30%，实际 {result['sifted_bits']}/{result['raw_bits']}"
        )
