# Task 5: fall-back / 假数据 / mock 终检报告

## 检查方法
- Grep 全量搜索 `src/polaris/` 全部 `.py` 文件（不区分大小写）
- 运行已有 fall-back 检查测试（test_r30_stage5_acceptance、test_r36_final_acceptance、test_meep_adjoint_backend、test_gpu_backend、test_gpu_density_field、test_calibration）
- 检查关键业务流程完整性（pdk 器件库、engine 布局、router 布线、trainer 训练、sim 仿真）
- 深入审查 try/except 错误处理模式与默认值返回模式
- 检查日期：2026-06-24

## 关键词匹配汇总

| 关键词 | 匹配数 | 合法数 | 违规数 |
|--------|--------|--------|--------|
| fallback / fall-back / fall_back | 27 | 27 | 0 |
| mock | 0 | 0 | 0 |
| fake | 9 | 9 | 0 |
| dummy | 0 | 0 | 0 |
| hardcode / hardcoded / hard_coded | 0 | 0 | 0 |
| placeholder | 0 | 0 | 0 |
| stub | 0 | 0 | 0 |
| TODO / FIXME / XXX / HACK | 0 | 0 | 0 |
| temporary / temp_value | 0 | 0 | 0 |
| default_value / placeholder_value | 0 | 0 | 0 |
| example_value / test_value | 0 | 0 | 0 |
| sample_data / synthetic_data | 0 | 0 | 0 |

### 关键词匹配说明
- **fallback (27 匹配，全部合法)**：全部出现在注释中，用于说明"非 fall-back""不 fall-back""无 fall-back"等设计声明。例如 `gpu_backend.py`、`fdtd_simulator.py`、`meep_adjoint_backend.py` 等模块明确声明不降级、不 fall-back。
- **fake (9 匹配，全部合法)**：全部出现在 `sim/ai_inverse_design.py` 的 GAN（生成对抗网络）训练代码中，`fake_batch`、`d_fake` 等为 GAN 标准术语（判别器对生成样本的输出），非假数据。
- **mock / dummy / hardcode / placeholder / stub / TODO / FIXME**：生产代码中 0 匹配。

> 注意：关键词搜索 0 违规，但深入行为审查发现 12 项 fall-back 违规（见下文"违规项详情"），这些违规通过 try/except 静默降级、返回空值/默认值等模式实现，不依赖关键词。

## 已有测试运行结果

| 测试文件 | 测试名 | 结果 |
|----------|--------|------|
| tests/test_r30_stage5_acceptance.py | TestR30RegressionCheck::test_no_fallback_in_modules | ✅ 通过 |
| tests/test_r36_final_acceptance.py | TestR36RegressionCheck::test_no_fallback_in_stage6_modules | ✅ 通过 |
| tests/test_meep_adjoint_backend.py | 全部（含 test_no_fallback_value 等 4 项 fall-back 专项检查） | ✅ 通过（2 项因 MEEP 未安装跳过） |
| tests/test_gpu_backend.py | 全部（含 test_automatic_fallback） | ✅ 通过（4 项因 CuPy 不可用跳过） |
| tests/test_gpu_density_field.py | 全部（含 test_gpu_cpu_fallback） | ✅ 通过 |
| tests/test_calibration.py | test_calibrate_total_loss_db_fallback | ✅ 通过 |

**汇总：86 passed, 6 skipped（跳过原因为 MEEP/CuPy 未安装），0 failed。**

> 已有测试覆盖范围有限：test_r30 仅检查 4 个模块文件（ipkiss_flow、caphe_backend、tidy3d_integration、ai_inverse_design），test_r36 仅检查 2 个模块文件（lumerical_integration、alpha_chip）。`pipeline/integrated.py`、`pdk/gdsfactory_integration.py`、`data/data_loader.py`、`sim/simulator.py` 等关键业务文件未被已有 fall-back 测试覆盖。

## 业务流程完整性检查

| 模块 | 流程 | 是否有 fall-back | 备注 |
|------|------|-----------------|------|
| pdk | 器件库加载 | ✅ 无 | `catalog.py:get()` 找不到器件时 raise KeyError，不返回默认器件 |
| pdk | gdsfactory GDS 生成 | ❌ 有 | `gdsfactory_integration.py` 不可用时返回空字符串，ubcpdk 不可用降级到 generic_pdk |
| engine | 布局引擎（RL 模式） | ❌ 有 | `pipeline/integrated.py:_try_load_agent` 加载失败切换随机贪心模式 |
| engine | 布局引擎（解析/层级） | ✅ 无 | `analytical_placer.py`、`hierarchical_placer.py` 正常报错 |
| router | 布线引擎（A* 网格） | ❌ 有 | `pipeline/integrated.py:_DefaultRouter.route` 布线返回空路径时静默跳过 |
| router | 布线引擎（弯曲感知） | ❌ 有 | `pipeline/integrated.py:_CurvyRouter.route` except RuntimeError: continue |
| router | 布线引擎（核心算法） | ✅ 无 | `waveguide_router.py`、`global_router.py` 找不到路径返回 None，由调用方处理 |
| trainer | 训练框架 | ✅ 无 | `distributed_learner.py` Ray 不可用时 raise，`ppo.py` 正常训练 |
| sim | 仿真模块（S 参数级联） | ❌ 有 | `sim/simulator.py` 模型不存在时静默跳过实例 |
| sim | 仿真模块（FDTD） | ✅ 无 | `fdtd_simulator.py` 后端不可用时 raise ImportError |
| sim | 仿真模块（查表估算） | ❌ 有 | `pipeline/integrated.py:_simulate_table` 未知器件损耗默认 0.0，n_crossings 固定 0 |
| sim | 仿真模块（MEEP Adjoint） | ✅ 无 | `meep_adjoint_backend.py` MEEP 不可用时 raise ImportError |
| sim | 仿真模块（AI 逆向设计） | ⚠️ 边界 | `ai_inverse_design.py` JAX 不可用时用 numpy 有限差分（数值等价，显式告警） |
| data | 数据加载 | ❌ 有 | `data_loader.py` 数据目录不存在时返回空列表 |

## 违规项详情

### 违规 1：RL agent 加载失败切换随机贪心模式
- **文件**：`src/polaris/pipeline/integrated.py:127-160`
- **上下文**：`_try_load_agent` 方法在检查点不存在（第 137 行）或加载异常（第 159 行）时，设置 `self._agent = None` 并切换为随机贪心模式，仅记录 warning 不报错。
- **影响**：`place()` 方法（第 172-174 行）检测 `self._agent is None` 后调用 `_place_random`，使用固定种子随机布局。这是典型的"训练失败时返回随机策略"fall-back。
- **应改为**：加载失败时 raise RuntimeError，由调用方决定是否显式选择 random 模式。

### 违规 2：布线失败静默跳过连接（弯曲感知）
- **文件**：`src/polaris/pipeline/integrated.py:336-346`
- **上下文**：`_CurvyRouter.route` 中 `except RuntimeError: continue`，布线异常时跳过该连接，不报错。
- **影响**：部分连接被静默丢弃，输出 paths 字典缺少连接，后续仿真结果不完整。
- **应改为**：记录 error 并 raise，或至少在返回结果中标记未布线连接。

### 违规 3：布线返回空路径静默跳过（A* 网格）
- **文件**：`src/polaris/pipeline/integrated.py:284-287`
- **上下文**：`_DefaultRouter.route` 中 `if grid_path:` 为 False 时跳过，不报错。
- **影响**：布线找不到路径时连接被静默丢弃。
- **应改为**：找不到路径时记录 error 并 raise 或标记。

### 违规 4：gdsfactory 不可用返回空字符串
- **文件**：`src/polaris/pdk/gdsfactory_integration.py:40-48, 98-102, 145-149, 191-196`
- **上下文**：gdsfactory import 失败时 `_HAS_GDSFACTORY = False`，`generate_mzi_gds`/`generate_ring_resonator_gds`/`generate_component_gds` 返回空字符串 `""`。
- **影响**：调用方得到空路径，GDS 生成静默失败。
- **应改为**：gdsfactory 为必装依赖，不可用时 raise ImportError。

### 违规 5：ubcpdk 不可用降级到 gdsfactory generic_pdk
- **文件**：`src/polaris/pdk/gdsfactory_integration.py:104-122, 152-167`
- **上下文**：`except ImportError:` 后从 ubcpdk 切换到 gdsfactory generic_pdk 生成器件。
- **影响**：使用不同 PDK 的器件参数，结果不一致。
- **应改为**：ubcpdk 为指定 PDK 依赖，不可用时 raise。

### 违规 6：查表估算未知器件损耗默认 0.0
- **文件**：`src/polaris/pipeline/integrated.py:418`
- **上下文**：`loss = self._LOSS_TABLE.get(dev.device_type, 0.0)` — 器件类型不在损耗表中时返回 0.0。
- **影响**：未知器件损耗被低估为 0，总损耗估算偏低。
- **应改为**：未知器件类型时 raise KeyError 或记录 warning。

### 违规 7：波导长度参数不存在用宽度代替
- **文件**：`src/polaris/pipeline/integrated.py:420`
- **上下文**：`length = dev.params.get("length", dev.width_um)` — 波导长度参数缺失时用宽度值代替。
- **影响**：物理错误，宽度（~0.5μm）与长度（~100μm）量级差异巨大，损耗计算严重失真。
- **应改为**：长度参数缺失时 raise ValueError。

### 违规 8：查表估算 n_crossings 固定返回 0
- **文件**：`src/polaris/pipeline/integrated.py:424`
- **上下文**：`return {"total_loss_db": total_loss, "n_crossings": 0}` — 查表模式不计算交叉数，固定返回 0。
- **影响**：交叉损耗被忽略，损耗估算偏低。
- **应改为**：基于 paths 几何实际计算交叉数，或在接口文档中明确声明此模式不计算交叉。

### 违规 9：数据目录不存在返回空列表
- **文件**：`src/polaris/data/data_loader.py:48-50`
- **上下文**：`if not p.exists(): logger.error(...); return []` — 数据目录不存在时返回空列表。
- **影响**：调用方得到空数据集，后续流程静默使用空数据。
- **应改为**：raise FileNotFoundError。

### 违规 10：仿真模型不存在静默跳过实例
- **文件**：`src/polaris/sim/simulator.py:94-96`
- **上下文**：`if model_name in self.models: instance_s[inst_name] = ...` — 模型不存在时跳过该实例，不报错。
- **影响**：级联仿真缺少实例，结果错误或崩溃。
- **应改为**：模型不存在时 raise KeyError。

### 边界情况：JAX 不可用使用 numpy 有限差分
- **文件**：`src/polaris/sim/ai_inverse_design.py:55-67`
- **上下文**：JAX import 失败时 `_HAS_JAX = False`，使用 numpy + 中心有限差分计算梯度，记录 warning。
- **判定**：数值精度等价（有限差分是数值精确的），性能较低，有显式告警。注释声明"非 fall-back，而是显式告警的替代后端"。从严格规则看仍属替代后端降级，但从学术诚信角度看结果正确。**标记为边界情况，建议保留但明确文档说明。**

## 结论

### 终检结果：❌ 未通过

全量 grep 关键词搜索 0 违规（所有关键词匹配均为合法：GAN 术语、注释中的设计声明）。已有 fall-back 检查测试全部通过（86 passed, 6 skipped）。

但深入行为审查发现 **10 项明确违规 + 1 项边界情况**，集中在以下文件：
- `src/polaris/pipeline/integrated.py`（6 项违规：RL 加载降级、布线静默跳过×2、查表默认值×3）
- `src/polaris/pdk/gdsfactory_integration.py`（2 项违规：返回空字符串、PDK 降级）
- `src/polaris/data/data_loader.py`（1 项违规：目录不存在返回空列表）
- `src/polaris/sim/simulator.py`（1 项违规：模型不存在静默跳过）
- `src/polaris/sim/ai_inverse_design.py`（1 项边界：JAX 降级 numpy 有限差分）

### 已有测试的盲区
已有 fall-back 检查测试（test_r30、test_r36）仅覆盖 6 个模块文件，且仅检查关键词模式，未覆盖行为层面的 fall-back（try/except 降级、返回空值/默认值）。建议扩展测试覆盖范围至 `pipeline/integrated.py`、`pdk/gdsfactory_integration.py`、`data/data_loader.py`、`sim/simulator.py`。

### 修复建议优先级
1. **P0（立即修复）**：违规 7（波导长度用宽度代替，物理错误）、违规 1（RL 加载降级随机）、违规 2/3（布线静默跳过）
2. **P1（尽快修复）**：违规 6/8（查表默认值）、违规 10（仿真模型跳过）、违规 9（数据目录返回空）
3. **P2（建议修复）**：违规 4/5（gdsfactory 返回空字符串/PDK 降级）
4. **P3（边界讨论）**：ai_inverse_design.py JAX 降级（数值等价，建议保留+文档说明）
