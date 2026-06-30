"""R366-R370 多智能体协作 RL 测试。

覆盖:
- R366 MultiAgentPlacementEnv
- R367 IndependentPPO (IPPO)
- R368 CTDECritic (MADDPG)
- R369 CommunicationChannel (CommNet)
- R370 MultiAgentCoordinator
- R03/R02/R04 合规
- 集成测试
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from polaris.rl.rl_multi_agent import (
    CommunicationChannel,
    CTDECritic,
    GPU_DISABLED_R04,
    IndependentPPO,
    IndependentPPOAgent,
    IPPOConfig,
    MultiAgentConfig,
    MultiAgentCoordinator,
    MultiAgentPlacementEnv,
)


# =============================================================================
# fixtures
# =============================================================================

@pytest.fixture
def ma_config() -> MultiAgentConfig:
    return MultiAgentConfig(grid_size=(8, 8), n_agents=2, max_devices=64, seed=42)


@pytest.fixture
def ma_env(ma_config: MultiAgentConfig) -> MultiAgentPlacementEnv:
    return MultiAgentPlacementEnv(ma_config)


@pytest.fixture
def circuit() -> dict:
    """4 器件电路。"""
    return {
        "devices": [
            {"id": f"d{i}", "type": "mzi", "width": 50.0, "height": 30.0, "ports": ["in", "out"]}
            for i in range(4)
        ],
        "nets": [{"src": ("d0", "in"), "dst": ("d1", "out")}],
    }


@pytest.fixture
def ippo() -> IndependentPPO:
    return IndependentPPO(2, IPPOConfig(seed=42))


@pytest.fixture
def critic() -> CTDECritic:
    return CTDECritic(n_agents=2, local_state_dim=8, local_action_dim=1, seed=42)


@pytest.fixture
def comm() -> CommunicationChannel:
    return CommunicationChannel(n_agents=2, message_dim=8, seed=42)


@pytest.fixture
def coordinator(ma_env: MultiAgentPlacementEnv, circuit: dict) -> MultiAgentCoordinator:
    ma_env.set_circuit(circuit)
    return MultiAgentCoordinator(ma_env, IPPOConfig(seed=42), comm_message_dim=8)


# =============================================================================
# R366 MultiAgentPlacementEnv 测试
# =============================================================================

class TestR366Env:
    """R366 多智能体布局环境测试。"""

    def test_init_regions(self, ma_env: MultiAgentPlacementEnv) -> None:
        """初始化 2 个区域。"""
        assert ma_env.n_agents() == 2
        assert len(ma_env.regions) == 2

    def test_set_circuit(self, ma_env: MultiAgentPlacementEnv, circuit: dict) -> None:
        """设置电路并分配器件。"""
        ma_env.set_circuit(circuit)
        total = sum(len(v) for v in ma_env.agent_devices.values())
        assert total == 4

    def test_set_circuit_missing_devices(self, ma_env: MultiAgentPlacementEnv) -> None:
        with pytest.raises(ValueError, match="devices"):
            ma_env.set_circuit({"nets": []})

    def test_set_circuit_zero_devices(self, ma_env: MultiAgentPlacementEnv) -> None:
        with pytest.raises(ValueError, match=">= 1"):
            ma_env.set_circuit({"devices": [], "nets": []})

    def test_set_circuit_exceed_max(self, ma_config: MultiAgentConfig) -> None:
        cfg = MultiAgentConfig(grid_size=(8, 8), n_agents=2, max_devices=2)
        env = MultiAgentPlacementEnv(cfg)
        circuit = {
            "devices": [
                {"id": f"d{i}", "type": "mzi", "width": 50, "height": 30, "ports": []}
                for i in range(3)
            ],
            "nets": [],
        }
        with pytest.raises(ValueError, match="max_devices"):
            env.set_circuit(circuit)

    def test_grid_h_less_than_agents(self) -> None:
        cfg = MultiAgentConfig(grid_size=(1, 8), n_agents=2)
        with pytest.raises(ValueError, match="grid_h"):
            MultiAgentPlacementEnv(cfg)

    def test_build_global_occupancy_empty(
        self, ma_env: MultiAgentPlacementEnv, circuit: dict
    ) -> None:
        """无放置 → 空 CSR。"""
        ma_env.set_circuit(circuit)
        occ = ma_env.build_global_occupancy()
        assert occ.nnz == 0

    def test_agent_state(self, ma_env: MultiAgentPlacementEnv, circuit: dict) -> None:
        """agent_state 返回局部状态。"""
        ma_env.set_circuit(circuit)
        s = ma_env.agent_state(0)
        assert s["agent_id"] == 0
        assert "region" in s
        assert "local_occupancy" in s

    def test_agent_state_invalid_agent(
        self, ma_env: MultiAgentPlacementEnv, circuit: dict
    ) -> None:
        ma_env.set_circuit(circuit)
        with pytest.raises(ValueError, match="agent_id"):
            ma_env.agent_state(999)

    def test_agent_state_no_circuit(self, ma_env: MultiAgentPlacementEnv) -> None:
        with pytest.raises(ValueError, match="电路未设置"):
            ma_env.agent_state(0)

    def test_step_normal(self, ma_env: MultiAgentPlacementEnv, circuit: dict) -> None:
        """step 正常放置。"""
        ma_env.set_circuit(circuit)
        # 找到第一个属于 agent 0 的器件
        dev_id = ma_env.agent_devices[0][0] if ma_env.agent_devices[0] else ma_env.agent_devices[1][0]
        agent_id = 0 if dev_id in ma_env.agent_devices[0] else 1
        result = ma_env.step(agent_id, dev_id, 0)
        assert dev_id in ma_env.global_placement

    def test_step_wrong_agent(
        self, ma_env: MultiAgentPlacementEnv, circuit: dict
    ) -> None:
        """器件不属于该 agent → raise（R03）。"""
        ma_env.set_circuit(circuit)
        # 找一个不属于 agent 0 的器件
        for a in range(ma_env.n_agents()):
            for d in ma_env.agent_devices[a]:
                other_a = 1 - a
                with pytest.raises(ValueError, match="不属于"):
                    ma_env.step(other_a, d, 0)
                return

    def test_step_already_placed(
        self, ma_env: MultiAgentPlacementEnv, circuit: dict
    ) -> None:
        """重复放置 → raise（R03）。"""
        ma_env.set_circuit(circuit)
        for a in range(ma_env.n_agents()):
            if ma_env.agent_devices[a]:
                dev_id = ma_env.agent_devices[a][0]
                ma_env.step(a, dev_id, 0)
                with pytest.raises(ValueError, match="已放置"):
                    ma_env.step(a, dev_id, 1)
                return

    def test_step_occupied(
        self, ma_env: MultiAgentPlacementEnv, circuit: dict
    ) -> None:
        """占用 → raise（R03）。"""
        ma_env.set_circuit(circuit)
        # 找到两个属于同一 agent 的器件
        for a in range(ma_env.n_agents()):
            if len(ma_env.agent_devices[a]) >= 2:
                d0 = ma_env.agent_devices[a][0]
                d1 = ma_env.agent_devices[a][1]
                ma_env.step(a, d0, 0)
                with pytest.raises(ValueError, match="已占用"):
                    ma_env.step(a, d1, 0)
                return

    def test_step_out_of_bounds(
        self, ma_env: MultiAgentPlacementEnv, circuit: dict
    ) -> None:
        ma_env.set_circuit(circuit)
        for a in range(ma_env.n_agents()):
            if ma_env.agent_devices[a]:
                with pytest.raises(ValueError, match="越界"):
                    ma_env.step(a, ma_env.agent_devices[a][0], 9999)
                return

    def test_global_reward(self, ma_env: MultiAgentPlacementEnv, circuit: dict) -> None:
        """全局奖励。"""
        ma_env.set_circuit(circuit)
        r = ma_env.global_reward()
        assert isinstance(r, float)

    def test_global_reward_no_circuit(self, ma_env: MultiAgentPlacementEnv) -> None:
        with pytest.raises(ValueError, match="电路未设置"):
            ma_env.global_reward()


# =============================================================================
# R367 IPPO 测试
# =============================================================================

class TestR367IPPO:
    """R367 独立 PPO 测试。"""

    def test_agent_init(self) -> None:
        agent = IndependentPPOAgent(0)
        assert agent.agent_id == 0

    def test_agent_gae(self) -> None:
        agent = IndependentPPOAgent(0, IPPOConfig(seed=42))
        rewards = np.array([1.0, 1.0])
        values = np.array([0.0, 0.0])
        dones = np.array([0.0, 0.0])
        adv, ret = agent.compute_gae(rewards, values, dones)
        assert adv.shape == (2,)

    def test_agent_gae_empty(self) -> None:
        agent = IndependentPPOAgent(0)
        with pytest.raises(ValueError, match="不能为空"):
            agent.compute_gae(np.array([]), np.array([]), np.array([]))

    def test_ippo_init(self, ippo: IndependentPPO) -> None:
        assert len(ippo.agents) == 2

    def test_ippo_invalid_n_agents(self) -> None:
        with pytest.raises(ValueError):
            IndependentPPO(0)

    def test_ippo_compute_all_gae(self, ippo: IndependentPPO) -> None:
        rollouts = [
            {"rewards": np.array([1.0]), "values": np.array([0.0]), "dones": np.array([0.0])},
            {"rewards": np.array([1.0]), "values": np.array([0.0]), "dones": np.array([0.0])},
        ]
        results = ippo.compute_all_gae(rollouts)
        assert len(results) == 2

    def test_ippo_mismatch_rollouts(self, ippo: IndependentPPO) -> None:
        with pytest.raises(ValueError, match="rollouts 数"):
            ippo.compute_all_gae([{}])

    def test_ippo_rollout_missing_field(self, ippo: IndependentPPO) -> None:
        with pytest.raises(ValueError, match="缺字段"):
            ippo.compute_all_gae([{}, {}])


# =============================================================================
# R368 CTDECritic 测试
# =============================================================================

class TestR368Critic:
    """R368 CTDE critic 测试（Lowe 2017 MADDPG）。"""

    def test_q_value(self, critic: CTDECritic) -> None:
        local_states = [np.zeros(8), np.zeros(8)]
        local_actions = [np.array([1.0]), np.array([2.0])]
        q = critic.q_value(local_states, local_actions)
        assert isinstance(q, float)

    def test_q_value_wrong_states(self, critic: CTDECritic) -> None:
        with pytest.raises(ValueError, match="local_states"):
            critic.q_value([np.zeros(8)], [np.array([1.0]), np.array([2.0])])

    def test_q_value_wrong_actions(self, critic: CTDECritic) -> None:
        with pytest.raises(ValueError, match="local_actions"):
            critic.q_value([np.zeros(8), np.zeros(8)], [np.array([1.0])])

    def test_update(self, critic: CTDECritic) -> None:
        local_states = [np.zeros(8), np.zeros(8)]
        local_actions = [np.array([1.0]), np.array([2.0])]
        loss = critic.update(local_states, local_actions, target_q=1.0)
        assert loss >= 0.0

    def test_invalid_n_agents(self) -> None:
        with pytest.raises(ValueError):
            CTDECritic(0, 8, 1)


# =============================================================================
# R369 CommunicationChannel 测试
# =============================================================================

class TestR369Comm:
    """R369 CommNet 通信测试（Foerster 2016）。"""

    def test_communicate_shape(self, comm: CommunicationChannel) -> None:
        inputs = [np.zeros(8), np.zeros(8)]
        msgs = comm.communicate(inputs)
        assert len(msgs) == 2
        assert msgs[0].shape == (8,)

    def test_communicate_broadcast(self, comm: CommunicationChannel) -> None:
        """CommNet 广播：所有智能体收到相同消息。"""
        inputs = [np.random.default_rng(0).normal(size=8),
                  np.random.default_rng(1).normal(size=8)]
        msgs = comm.communicate(inputs)
        np.testing.assert_allclose(msgs[0], msgs[1])

    def test_communicate_wrong_n(self, comm: CommunicationChannel) -> None:
        with pytest.raises(ValueError, match="agent_inputs"):
            comm.communicate([np.zeros(8)])

    def test_communicate_wrong_dim(self, comm: CommunicationChannel) -> None:
        with pytest.raises(ValueError, match="输入维度"):
            comm.communicate([np.zeros(999), np.zeros(8)])

    def test_invalid_n_agents(self) -> None:
        with pytest.raises(ValueError):
            CommunicationChannel(0, 8)

    def test_invalid_message_dim(self) -> None:
        with pytest.raises(ValueError):
            CommunicationChannel(2, 0)


# =============================================================================
# R370 Coordinator 测试
# =============================================================================

class TestR370Coordinator:
    """R370 多智能体协调器测试。"""

    def test_init(self, coordinator: MultiAgentCoordinator) -> None:
        assert coordinator.env.n_agents() == 2
        assert coordinator.ippo is not None
        assert coordinator.comm is not None
        assert coordinator.critic is not None

    def test_collect_communication(
        self, coordinator: MultiAgentCoordinator, circuit: dict
    ) -> None:
        ma_env = coordinator.env
        states = [ma_env.agent_state(0), ma_env.agent_state(1)]
        msgs = coordinator.collect_communication(states)
        assert len(msgs) == 2

    def test_collect_communication_wrong_n(
        self, coordinator: MultiAgentCoordinator
    ) -> None:
        with pytest.raises(ValueError, match="agent_states"):
            coordinator.collect_communication([{}])

    def test_evaluate_global_q(
        self, coordinator: MultiAgentCoordinator
    ) -> None:
        ma_env = coordinator.env
        states = [ma_env.agent_state(0), ma_env.agent_state(1)]
        actions = [0, 1]
        q = coordinator.evaluate_global_q(states, actions)
        assert isinstance(q, float)

    def test_evaluate_global_q_wrong_actions(
        self, coordinator: MultiAgentCoordinator
    ) -> None:
        ma_env = coordinator.env
        states = [ma_env.agent_state(0), ma_env.agent_state(1)]
        with pytest.raises(ValueError, match="agent_actions"):
            coordinator.evaluate_global_q(states, [0])


# =============================================================================
# R03/R02/R04 合规
# =============================================================================

class TestCompliance:
    """合规测试。"""

    def test_r03_no_silent_fallback(self) -> None:
        from polaris.rl import rl_multi_agent as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "except: pass" not in src
        assert "except Exception: pass" not in src

    def test_r02_5plus_urls(self) -> None:
        from polaris.rl import rl_multi_agent as mod
        assert mod.__doc__ is not None
        urls = [l for l in mod.__doc__.splitlines() if "http" in l]
        assert len(urls) >= 5

    def test_r02_lowe_cited(self) -> None:
        from polaris.rl import rl_multi_agent as mod
        assert "Lowe" in mod.__doc__
        assert "1706.02275" in mod.__doc__

    def test_r02_innovation_marked(self) -> None:
        from polaris.rl import rl_multi_agent as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "*创新*" in src

    def test_r04_gpu_disabled(self) -> None:
        assert GPU_DISABLED_R04 is True

    def test_r04_no_gpu_imports(self) -> None:
        from polaris.rl import rl_multi_agent as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import cupy" not in src
        assert "import torch" not in src
        assert "import jax" not in src


# =============================================================================
# 集成测试
# =============================================================================

class TestIntegration:
    """集成测试：多智能体完整流程。"""

    def test_full_multi_agent_pipeline(
        self, ma_env: MultiAgentPlacementEnv, circuit: dict
    ) -> None:
        """完整流程：环境 → 分配 → 通信 → 放置 → 奖励。"""
        ma_env.set_circuit(circuit)
        coordinator = MultiAgentCoordinator(ma_env, IPPOConfig(seed=42), 8)
        # 收集通信
        states = [ma_env.agent_state(a) for a in range(ma_env.n_agents())]
        msgs = coordinator.collect_communication(states)
        # 评估 Q
        actions = [0] * ma_env.n_agents()
        q = coordinator.evaluate_global_q(states, actions)
        # 全局奖励
        r = ma_env.global_reward()
        assert isinstance(q, float)
        assert isinstance(r, float)
        assert len(msgs) == ma_env.n_agents()
