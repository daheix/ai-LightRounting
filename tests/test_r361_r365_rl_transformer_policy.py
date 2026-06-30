"""R361-R365 Transformer 策略网络测试。

覆盖:
- R361 MultiHeadAttention (Vaswani 2017)
- R362 PositionalEncoding
- R363 TransformerEncoderLayer
- R364 TransformerPolicyNetwork
- R365 TransformerValueNetwork
- R03/R02/R04 合规
- 集成测试
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.rl.rl_transformer_policy import (
    AttentionConfig,
    GPU_DISABLED_R04,
    MultiHeadAttention,
    PositionalEncoding,
    TransformerConfig,
    TransformerEncoderLayer,
    TransformerPolicyNetwork,
    TransformerValueNetwork,
)


# =============================================================================
# fixtures
# =============================================================================

@pytest.fixture
def attn_config() -> AttentionConfig:
    return AttentionConfig(d_model=16, n_heads=2, d_k=8, d_ff=32, seed=42)


@pytest.fixture
def attn(attn_config: AttentionConfig) -> MultiHeadAttention:
    return MultiHeadAttention(attn_config)


@pytest.fixture
def pos_enc() -> PositionalEncoding:
    return PositionalEncoding(d_model=16, max_len=64)


@pytest.fixture
def tx_config() -> TransformerConfig:
    return TransformerConfig(
        d_model=16, n_heads=2, d_k=8, d_ff=32, n_layers=2,
        n_actions=64, max_len=64, seed=42,
    )


@pytest.fixture
def policy(tx_config: TransformerConfig) -> TransformerPolicyNetwork:
    return TransformerPolicyNetwork(tx_config)


@pytest.fixture
def value_net(tx_config: TransformerConfig) -> TransformerValueNetwork:
    return TransformerValueNetwork(tx_config)


# =============================================================================
# R361 MultiHeadAttention 测试
# =============================================================================

class TestR361MultiHeadAttention:
    """R361 多头注意力测试（Vaswani 2017 Eq.1-2）。"""

    def test_attention_shape(self, attn: MultiHeadAttention) -> None:
        """单头 attention 输出形状。"""
        Q = np.random.default_rng(0).normal(size=(5, 8))
        K = np.random.default_rng(1).normal(size=(5, 8))
        V = np.random.default_rng(2).normal(size=(5, 8))
        out, attn_w = attn.attention(Q, K, V)
        assert out.shape == (5, 8)
        assert attn_w.shape == (5, 5)

    def test_attention_weights_sum_to_one(self, attn: MultiHeadAttention) -> None:
        """softmax 后 attention weights 行和=1。"""
        Q = np.random.default_rng(0).normal(size=(3, 8))
        K = Q.copy()
        V = Q.copy()
        _, attn_w = attn.attention(Q, K, V)
        np.testing.assert_allclose(attn_w.sum(axis=-1), 1.0, atol=1e-10)

    def test_attention_1d_raises(self, attn: MultiHeadAttention) -> None:
        """Q 1D → raise（R03）。"""
        with pytest.raises(ValueError, match="2D"):
            attn.attention(np.zeros(8), np.zeros((3, 8)), np.zeros((3, 8)))

    def test_forward_shape(self, attn: MultiHeadAttention) -> None:
        """多头 forward 输出 [N, d_model]。"""
        x = np.random.default_rng(0).normal(size=(5, 16))
        out, attns = attn.forward(x)
        assert out.shape == (5, 16)
        assert len(attns) == 2  # n_heads=2

    def test_forward_d_model_mismatch(self, attn: MultiHeadAttention) -> None:
        """x 最后一维 ≠ d_model → raise（R03）。"""
        with pytest.raises(ValueError, match="d_model"):
            attn.forward(np.zeros((5, 999)))

    def test_forward_1d_raises(self, attn: MultiHeadAttention) -> None:
        """x 1D → raise（R03）。"""
        with pytest.raises(ValueError, match="2D"):
            attn.forward(np.zeros(16))

    def test_mask(self, attn: MultiHeadAttention) -> None:
        """mask 屏蔽部分 attention。"""
        x = np.random.default_rng(0).normal(size=(3, 16))
        # mask: 只 attend 到第 0 个位置
        mask = np.array([
            [True, False, False],
            [True, False, False],
            [True, False, False],
        ])
        _, attns = attn.forward(x, mask)
        # 每个位置 attention 都集中在 0
        for a in attns:
            np.testing.assert_allclose(a[:, 1:], 0.0, atol=1e-10)
            np.testing.assert_allclose(a[:, 0], 1.0, atol=1e-10)

    def test_mask_shape_mismatch(self, attn: MultiHeadAttention) -> None:
        """mask 形状不匹配 → raise（R03）。"""
        x = np.zeros((3, 16))
        with pytest.raises(ValueError, match="mask"):
            attn.forward(x, np.zeros((2, 2)))

    def test_d_model_not_divisible_by_heads(self) -> None:
        """d_model ≠ n_heads*d_k → raise（R03）。"""
        cfg = AttentionConfig(d_model=10, n_heads=3, d_k=4)  # 3*4=12≠10
        with pytest.raises(ValueError, match="d_model"):
            MultiHeadAttention(cfg)


# =============================================================================
# R362 PositionalEncoding 测试
# =============================================================================

class TestR362PositionalEncoding:
    """R362 正弦位置编码测试（Vaswani 2017 §3.5）。"""

    def test_encode_shape(self, pos_enc: PositionalEncoding) -> None:
        """encode 保持形状。"""
        x = np.zeros((5, 16))
        out = pos_enc.encode(x)
        assert out.shape == (5, 16)

    def test_encode_adds_pe(self, pos_enc: PositionalEncoding) -> None:
        """encode 添加了 PE（输出不等于输入）。"""
        x = np.zeros((5, 16))
        out = pos_enc.encode(x)
        assert not np.allclose(out, x)

    def test_pe_sin_cos(self) -> None:
        """PE[0,0]=sin(0)=0, PE[0,1]=cos(0)=1（Vaswani 2017 Eq.3-4）。"""
        pe = PositionalEncoding(d_model=4, max_len=8)
        assert pe.pe[0, 0] == pytest.approx(0.0, abs=1e-10)  # sin(0)
        assert pe.pe[0, 1] == pytest.approx(1.0, abs=1e-10)  # cos(0)

    def test_encode_d_model_mismatch(self, pos_enc: PositionalEncoding) -> None:
        """x 最后一维 ≠ d_model → raise（R03）。"""
        with pytest.raises(ValueError, match="d_model"):
            pos_enc.encode(np.zeros((5, 999)))

    def test_encode_1d_raises(self, pos_enc: PositionalEncoding) -> None:
        """x 1D → raise（R03）。"""
        with pytest.raises(ValueError, match="2D"):
            pos_enc.encode(np.zeros(16))

    def test_encode_offset_exceeds_max_len(self) -> None:
        """offset+N > max_len → raise（R03）。"""
        pe = PositionalEncoding(d_model=4, max_len=4)
        with pytest.raises(ValueError, match="max_len"):
            pe.encode(np.zeros((5, 4)))

    def test_invalid_d_model(self) -> None:
        with pytest.raises(ValueError):
            PositionalEncoding(d_model=0)

    def test_invalid_max_len(self) -> None:
        with pytest.raises(ValueError):
            PositionalEncoding(d_model=4, max_len=0)


# =============================================================================
# R363 TransformerEncoderLayer 测试
# =============================================================================

class TestR363EncoderLayer:
    """R363 Transformer 编码器层测试。"""

    def test_forward_shape(self) -> None:
        """forward 保持 [N, d_model] 形状。"""
        cfg = TransformerConfig(d_model=16, n_heads=2, d_k=8, d_ff=32, seed=42)
        layer = TransformerEncoderLayer(cfg)
        x = np.random.default_rng(0).normal(size=(5, 16))
        out = layer.forward(x)
        assert out.shape == (5, 16)

    def test_ffn_shape(self) -> None:
        """FFN 保持 [N, d_model] 形状。"""
        cfg = TransformerConfig(d_model=16, n_heads=2, d_k=8, d_ff=32, seed=42)
        layer = TransformerEncoderLayer(cfg)
        x = np.random.default_rng(0).normal(size=(5, 16))
        out = layer.ffn(x)
        assert out.shape == (5, 16)

    def test_forward_residual_effect(self) -> None:
        """forward 因残差+layernorm 改变输出。"""
        cfg = TransformerConfig(d_model=16, n_heads=2, d_k=8, d_ff=32, seed=42)
        layer = TransformerEncoderLayer(cfg)
        x = np.random.default_rng(0).normal(size=(5, 16))
        out = layer.forward(x)
        assert not np.allclose(out, x)


# =============================================================================
# R364 TransformerPolicyNetwork 测试
# =============================================================================

class TestR364PolicyNetwork:
    """R364 Transformer 策略网络测试。"""

    def test_forward_shape(self, policy: TransformerPolicyNetwork) -> None:
        """forward 返回 [n_actions] 概率分布。"""
        x = np.random.default_rng(0).normal(size=(5, 9))
        probs = policy.forward(x)
        assert probs.shape == (64,)

    def test_forward_probs_sum_to_one(self, policy: TransformerPolicyNetwork) -> None:
        """softmax 后概率和=1。"""
        x = np.random.default_rng(0).normal(size=(5, 9))
        probs = policy.forward(x)
        assert probs.sum() == pytest.approx(1.0, abs=1e-10)

    def test_forward_probs_non_negative(self, policy: TransformerPolicyNetwork) -> None:
        """概率非负。"""
        x = np.random.default_rng(0).normal(size=(5, 9))
        probs = policy.forward(x)
        assert np.all(probs >= 0.0)

    def test_forward_with_mask(self, policy: TransformerPolicyNetwork) -> None:
        """action_mask 屏蔽部分动作。"""
        x = np.random.default_rng(0).normal(size=(5, 9))
        mask = np.zeros(64, dtype=bool)
        mask[:5] = True  # 只允许前 5 个动作
        probs = policy.forward(x, action_mask=mask)
        # 屏蔽后概率集中在前 5
        assert probs[5:].sum() == pytest.approx(0.0, abs=1e-6)
        assert probs[:5].sum() == pytest.approx(1.0, abs=1e-6)

    def test_forward_wrong_feat_dim(self, policy: TransformerPolicyNetwork) -> None:
        """node_feats 最后一维 ≠ 9 → raise（R03）。"""
        with pytest.raises(ValueError, match="9"):
            policy.forward(np.zeros((5, 999)))

    def test_forward_1d_raises(self, policy: TransformerPolicyNetwork) -> None:
        """node_feats 1D → raise（R03）。"""
        with pytest.raises(ValueError, match="2D"):
            policy.forward(np.zeros(9))

    def test_forward_mask_shape_mismatch(self, policy: TransformerPolicyNetwork) -> None:
        """action_mask 形状不匹配 → raise（R03）。"""
        x = np.zeros((5, 9))
        with pytest.raises(ValueError, match="action_mask"):
            policy.forward(x, action_mask=np.zeros(999))


# =============================================================================
# R365 TransformerValueNetwork 测试
# =============================================================================

class TestR365ValueNetwork:
    """R365 Transformer 价值网络测试。"""

    def test_forward_returns_scalar(self, value_net: TransformerValueNetwork) -> None:
        """forward 返回标量 V(s)。"""
        x = np.random.default_rng(0).normal(size=(5, 9))
        v = value_net.forward(x)
        assert isinstance(v, float)

    def test_forward_wrong_feat_dim(self, value_net: TransformerValueNetwork) -> None:
        """node_feats 最后一维 ≠ 9 → raise（R03）。"""
        with pytest.raises(ValueError, match="9"):
            value_net.forward(np.zeros((5, 999)))

    def test_forward_1d_raises(self, value_net: TransformerValueNetwork) -> None:
        """node_feats 1D → raise（R03）。"""
        with pytest.raises(ValueError, match="2D"):
            value_net.forward(np.zeros(9))


# =============================================================================
# R03/R02/R04 合规
# =============================================================================

class TestCompliance:
    """合规测试。"""

    def test_r03_no_silent_fallback(self) -> None:
        from polaris.rl import rl_transformer_policy as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "except: pass" not in src
        assert "except Exception: pass" not in src

    def test_r02_5plus_urls(self) -> None:
        from polaris.rl import rl_transformer_policy as mod
        assert mod.__doc__ is not None
        urls = [l for l in mod.__doc__.splitlines() if "http" in l or "DOI:" in l]
        assert len(urls) >= 5

    def test_r02_vaswani_cited(self) -> None:
        from polaris.rl import rl_transformer_policy as mod
        assert "Vaswani" in mod.__doc__
        assert "1706.03762" in mod.__doc__

    def test_r02_innovation_marked(self) -> None:
        from polaris.rl import rl_transformer_policy as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "*创新*" in src

    def test_r04_gpu_disabled(self) -> None:
        assert GPU_DISABLED_R04 is True

    def test_r04_no_gpu_imports(self) -> None:
        from polaris.rl import rl_transformer_policy as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import cupy" not in src
        assert "import torch" not in src
        assert "import jax" not in src


# =============================================================================
# 集成测试
# =============================================================================

class TestIntegration:
    """集成测试：Transformer 策略 + 大规模布局环境。"""

    def test_policy_with_env_state(self, tx_config: TransformerConfig) -> None:
        """策略网络处理 R351 环境状态。"""
        from polaris.rl.rl_numpy_advanced import LargeScalePlacementEnv
        env = LargeScalePlacementEnv()
        # 小电路
        circuit = {
            "devices": [
                {"id": "d0", "type": "mzi", "width": 50.0, "height": 30.0, "ports": ["in", "out"]},
                {"id": "d1", "type": "ring", "width": 50.0, "height": 30.0, "ports": ["in", "out"]},
                {"id": "d2", "type": "mmi", "width": 50.0, "height": 30.0, "ports": ["in", "out"]},
            ],
            "nets": [{"src": ("d0", "in"), "dst": ("d1", "out")}],
        }
        env.set_circuit(circuit)
        state = env.build_state(circuit["devices"][0])
        node_feats = state["node_feats"]  # [3, 9]
        action_mask = state["action_mask"]  # [1024]

        # 调整 config n_actions=1024 匹配
        cfg = TransformerConfig(
            d_model=16, n_heads=2, d_k=8, d_ff=32, n_layers=2,
            n_actions=1024, max_len=1024, seed=42,
        )
        policy = TransformerPolicyNetwork(cfg)
        probs = policy.forward(node_feats, action_mask=action_mask > 0.5)
        assert probs.shape == (1024,)
        assert probs.sum() == pytest.approx(1.0, abs=1e-6)

    def test_value_with_env_state(self, tx_config: TransformerConfig) -> None:
        """价值网络处理 R351 环境状态。"""
        from polaris.rl.rl_numpy_advanced import LargeScalePlacementEnv
        env = LargeScalePlacementEnv()
        circuit = {
            "devices": [
                {"id": "d0", "type": "mzi", "width": 50.0, "height": 30.0, "ports": ["in", "out"]},
            ],
            "nets": [],
        }
        env.set_circuit(circuit)
        state = env.build_state(circuit["devices"][0])
        cfg = TransformerConfig(
            d_model=16, n_heads=2, d_k=8, d_ff=32, n_layers=2,
            n_actions=64, max_len=1024, seed=42,
        )
        value_net = TransformerValueNetwork(cfg)
        v = value_net.forward(state["node_feats"])
        assert isinstance(v, float)
