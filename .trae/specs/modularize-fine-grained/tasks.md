# Tasks

- [ ] Task 1: 拆分 polaris-verify → polaris-drc + polaris-lvs（最优先，v1已实现，只需拆分）
  - [ ] SubTask 1.1: 创建 `modules/drc/`（从 modules/verify/drc.py 迁移）
        pyproject + src/polaris_drc/__init__.py + c_api/drc.h + tests
        Input: {circuit, placements} → Process: 12条DRC规则 → Output: {n_violations, pass_rate, violations}
  - [ ] SubTask 1.2: 创建 `modules/lvs/`（从 modules/verify/lvs.py 迁移）
        Input: {circuit, netlist?} → Process: 拓扑比对 → Output: {is_consistent, n_mismatches}
  - [ ] SubTask 1.3: 删除旧的 modules/verify/（已被 drc+lvs 替代）

- [ ] Task 2: 拆分 polaris-sim → 7 个仿真子模块（核心工作）
  - [ ] SubTask 2.1: 创建 `modules/sparam/`（频域S参数，从 sim/models.py+mzi.py 迁移）
        Input: {wavelength, device_params} → Process: 解析模型级联 → Output: {S矩阵, 谐振波长, ER}
  - [ ] SubTask 2.2: 创建 `modules/fdtd/`（时域FDTD，从 sim/fdtd/ 迁移）
        Input: {网格, 源, eps_r} → Process: Yee时间步进 → Output: {时域场, 传输率}
  - [ ] SubTask 2.3: 创建 `modules/fde/`（频域本征模，从 sim/fde/ 迁移）
        Input: {波导截面, 波长} → Process: 本征值求解 → Output: {模式场, neff}
  - [ ] SubTask 2.4: 创建 `modules/eme/`（本征模展开，从 sim/eme/ 迁移）
        Input: {器件几何, 波长} → Process: 模式传播+匹配 → Output: {S参数}
  - [ ] SubTask 2.5: 创建 `modules/bpm/`（光束传播法，从 sim/bpm/ 迁移）
        Input: {折射率分布, 源} → Process: CN/ADI方向传播 → Output: {场分布}
  - [ ] SubTask 2.6: 创建 `modules/fdfd/`（频域有限差分，从 sim/fdfd/ 迁移）
        Input: {网格, 源, 波长} → Process: 线性方程组 → Output: {稳态场}
  - [ ] SubTask 2.7: 创建 `modules/pam4/`（PAM4信号仿真，从 sim/pam4.py 迁移）
        Input: {n_symbols, bit_rate, noise_std} → Process: 生成+噪声+检测 → Output: {BER, SNR, 眼图}
  - [ ] SubTask 2.8: 删除旧的 modules/sim/（已被7个子模块替代）

- [ ] Task 3: 拆分 polaris-quantum → polaris-boson + polaris-klm
  - [ ] SubTask 3.1: 创建 `modules/boson/`（玻色采样）
        Input: {酉矩阵, 输入态} → Process: permanent计算 → Output: {概率分布, prob_sum}
  - [ ] SubTask 3.2: 创建 `modules/klm/`（KLM CNOT）
        Input: 无 → Process: Ralph 2002 CNOT门 → Output: {success_prob=1/9, verified}
  - [ ] SubTask 3.3: 删除旧的 modules/quantum/（已被 boson+klm 替代）

- [ ] Task 4: 拆分 polaris-pdk → polaris-pdk（器件库）+ polaris-gdsio（GDSII导入导出）
  - [ ] SubTask 4.1: 创建 `modules/gdsio/`（从 pdk/gdsii.py 迁移）
        Input: {circuit 或 gds_path} → Process: klayout.db读写 → Output: {GDS文件 或 结构信息}
  - [ ] SubTask 4.2: 简化 modules/pdk/ 只保留器件库（list_platforms/get_device）

- [ ] Task 5: 更新 polaris-orchestrator 调用18个子模块
  - [ ] SubTask 5.1: 修改 flow.py，将 polaris_verify.run_drc→polaris_drc.run_drc，
        polaris_verify.run_lvs→polaris_lvs.run_lvs，polaris_sim.*→对应7个仿真子模块
  - [ ] SubTask 5.2: 更新编排顺序为对应18子模块的调用

- [ ] Task 6: 更新业务示例 main.py + main.c
  - [ ] SubTask 6.1: 更新 main.py 调用18个子模块
  - [ ] SubTask 6.2: 更新 main.c 包含18个头文件

- [ ] Task 7: 端到端验证与提交
  - [ ] SubTask 7.1: 18个子模块全部独立 import 验证
  - [ ] SubTask 7.2: orchestrator 一键调用验证
  - [ ] SubTask 7.3: 更新 modules/README.md 总览文档（18子模块 + IPO文档）
  - [ ] SubTask 7.4: git add + commit + push

# Task Dependencies
- Task 1/2/3/4 互相独立，可并行
- Task 5 依赖 Task 1-4
- Task 6 依赖 Task 5
- Task 7 依赖 Task 6
