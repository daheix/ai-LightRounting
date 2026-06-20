# examples/ — PoLaRIS 使用示例

存放面向第三方用户的示例代码，按编号递进：

| 编号 | 文件 | 内容 | 适合人群 |
|------|------|------|----------|
| 01 | `01_minimal_mzi.py` | 最小 MZI 电路布局布线 | 首次接触本工具的用户 |
| 02 | `02_pipeline_e2e.py` | 端到端流水线无参快速演示 | 验证安装是否正常 |
| 03 | `03_ppo_training.py` | PPO 训练快速入门 | 想训练自定义模型的用户 |
| 04 | `04_pdk_catalog.py` | PDK 器件库查询与器件实例化 | 想了解器件库的用户 |

## 运行方式

```bash
# 在项目根目录执行
python publish/examples/01_minimal_mzi.py
python publish/examples/02_pipeline_e2e.py
python publish/examples/03_ppo_training.py
python publish/examples/04_pdk_catalog.py
```

## 依赖

- 核心示例（01/02/04）：仅需运行依赖子集（numpy/scipy/networkx/gymnasium）
- 训练示例（03）：运行依赖 torch（import 失败时自动回退到 NumPy PPO）

## 完整训练

示例 03 仅展示训练流程，完整训练请使用：

```bash
python scripts/train_2m.py
```

## 来源

- PoLaRIS 项目: https://github.com/polaris-eda/polaris
- PPO: Schulman et al., arXiv 1707.06347
- ExpertRewardShaper: ICLR'26 Expertise-Enhanced RL
