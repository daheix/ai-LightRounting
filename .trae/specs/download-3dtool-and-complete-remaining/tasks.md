# Tasks

## 阶段一：3dtool 仓库下载与融合

- [x] Task 1: 清理磁盘空间确保 ≥4G 可用
  - [x] SubTask 1.1: 删除 /tmp/3dtool(1.6G)、/tmp/php-build(1.2G)、/root/.phpenv(1.1G)、/root/.nvm(1.1G)、/root/.cache(87M)、pip 缓存(2.4G)
  - [x] SubTask 1.2: 验证 df -h 显示 4.9G 可用（≥4G 达标）

- [x] Task 2: 3dtool 工具集获取与 wheel 自仓库建立
  - [x] SubTask 2.1: 验证 daheix/3dtool 仓库 HTTP 404（仓库不存在/私有），搜索 daheix 全部公开仓库 + GitHub 全局搜索 + 所有分支/releases/gists，确认无 3dtool-appimage 分片
  - [x] SubTask 2.2: 按 R03 禁止 fall-back + R14 失败告警+替代方案原则，改用 `pip download` 重新生成 wheel 自仓库（从 PyPI 下载真实 wheel 包到 3dtool/wheels/）
  - [x] SubTask 2.3: 批次1 下载 13 个小包（--no-deps 避免传递依赖重复）
  - [x] SubTask 2.4: 批次2 下载大包 torch（200MB CPU 版）
  - [x] SubTask 2.5: 下载传递依赖（jax/sax/optax/flax 等传递依赖链）

- [x] Task 3: 验证工具链与三方库目录融合
  - [x] SubTask 3.1: 验证 3dtool/wheels/install.sh 与 3dtool-appimage 共存（15 wheel + AppDir 精简版）
  - [x] SubTask 3.2: 验证 AppRun python3 可调用且版本为 3.14.4
  - [x] SubTask 3.3: site-packages 含 numpy/scipy/torch 等 10 核心包（klayout/sax 在 wheels/）

## 阶段二：P0 级 R03 违规修复

- [x] Task 4: 修复 I04 verilog_a.py 的合成脉冲信号 fall-back
  - [x] SubTask 4.1: 删除第 761-774 行的合成脉冲信号代码
  - [x] SubTask 4.2: 实现真实 Ngspice .raw 输出解析（5 个辅助函数：_parse_ngspice_rawfile 等），解析失败 raise RuntimeError
  - [x] SubTask 4.3: 验证 py_compile 通过

- [x] Task 5: 修复 calibration.py 的 except Exception: continue
  - [x] SubTask 5.1: 第 119 行拆分为 3 类具体异常（FileNotFoundError 可恢复 / JSONDecodeError 不可恢复 raise / OSError 可恢复）
  - [x] SubTask 5.2: 验证 py_compile 通过

- [x] Task 6: 修复 gdsfactory_integration.py 的 3 处静默兜底
  - [x] SubTask 6.1: 第 86-89 行 `except Exception: return False` → raise RuntimeError
  - [x] SubTask 6.2: 第 240 行 `except Exception: return []` → raise ImportError/RuntimeError
  - [x] SubTask 6.3: 第 514-516 行 `except Exception: return {}` → raise ImportError/RuntimeError
  - [x] SubTask 6.4: 验证 py_compile 通过

- [x] Task 7: 修复 data_loader.py 的 2 处静默处理
  - [x] SubTask 7.1: 第 61-63 行和 68-70 行改为区分 OSError（可恢复 continue）和 ValueError（不可恢复 raise）
  - [x] SubTask 7.2: 验证 py_compile 通过

## 阶段三：P0 级多物理耦合层补充

- [x] Task 8: 创建 H01 电光耦合模块
  - [x] SubTask 8.1: 创建 src/polaris/sim/multiphysics/__init__.py（90 行，10 篇文献）
  - [x] SubTask 8.2: 创建 src/polaris/sim/multiphysics/electro_optic.py（444 行，Soref-Bennett 等离子体色散公式）
  - [x] SubTask 8.3: 连接 DDM 载流子分布 → 折射率变化 → 光学仿真（apply_electro_optic_coupling）
  - [x] SubTask 8.4: 文献引用 7 篇（≥5 达标）

- [x] Task 9: 创建 H02 热光耦合模块
  - [x] SubTask 9.1: 创建 src/polaris/sim/multiphysics/thermo_optic.py（409 行，Cocorullo 热光系数 1.86e-4 K^-1）
  - [x] SubTask 9.2: 连接 HEAT 温度场 → 折射率变化 → 光学仿真（apply_thermo_optic_coupling）
  - [x] SubTask 9.3: 文献引用 7 篇（≥5 达标）

## 阶段四：P1 级问题整改

- [x] Task 10: D05 AlphaChip 架构统一
  - [x] SubTask 10.1: rl/alpha_chip.py 复用 engine/alphachip_gnn.py 的 AlphaChipEdgeGNN
  - [x] SubTask 10.2: rl/alpha_chip.py 复用 ppo_torch.py 的 PPOAgent（替代简化版 REINFORCE）
  - [x] SubTask 10.3: 验证 py_compile 通过

- [x] Task 11: C05 频域扫描 JAX vmap 集成
  - [x] SubTask 11.1: 在频域扫描中集成 jax.vmap 并行
  - [x] SubTask 11.2: 验证 py_compile 通过

- [x] Task 12: D04 RewardNormalizer 实现
  - [x] SubTask 12.1: 在 reward_shaping.py 中实现 RewardNormalizer 类
  - [x] SubTask 12.2: 集成到 ExpertRewardShaper
  - [x] SubTask 12.3: 验证 py_compile 通过

## 阶段五：提交与验证

- [x] Task 13: 全部验证并提交
  - [x] SubTask 13.1: ruff check + py_compile 全部通过（10/10 py_compile + All ruff checks passed）
  - [x] SubTask 13.2: git cherry-pick 2 提交（2b31e91 + 6229d97）+ push origin main（1992c39..f67107a）
  - [x] SubTask 13.3: 更新操作记录.md + checklist.md + tasks.md 全部勾选

# Task Dependencies
- [Task 2] depends on [Task 1]（需要磁盘空间）
- [Task 3] depends on [Task 2]（需要 AppImage 恢复完成）
- [Task 4-7] 可并行执行（无依赖关系）
- [Task 8-9] 可并行执行（无依赖关系）
- [Task 10-12] 可并行执行（无依赖关系）
- [Task 13] depends on [Task 4-12]（全部完成后提交）
