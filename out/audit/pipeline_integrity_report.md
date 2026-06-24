# PoLaRIS 流程诚信审查报告

> 自动生成于 `scripts/audit_pipeline_integrity.py`
> 规则依据：项目规则 14.1（禁止 fall-back / 假数据 / mock）、规则 18（学术诚信）、规则 7.1（文件 < 600 行）

## 1. 扫描统计

- 扫描目录：`src/polaris/`
- 扫描文件数：190
- 扫描代码行数：74701
- 命中总数：19

### 1.1 按类别分布

| 类别 | 数量 |
|------|------|
| 静默吞异常 (swallow) | 0 |
| mock/fake/dummy/占位 (mock_fake) | 13 |
| 硬编码 (hardcode) | 0 |
| 降级/跳过日志 (degrade_log) | 6 |
| TODO fallback (todo_fb) | 0 |
| if not 返回空值 (empty_return) | 0 |

### 1.2 按严重度分布

| 严重度 | 数量 |
|--------|------|
| high | 0 |
| medium | 19 |
| low | 0 |

## 2. 真 fall-back 清单（违反规则 14.1，需修复）

无。

## 3. 合法异常处理清单（保留）

| 文件 | 行号 | 规则 | 代码片段 | 保留理由 |
|------|------|------|----------|----------|
| `src/polaris/ai/inverse_design.py` | 319 | P021 | `WGAN-GP 损失：L_D = E[D(fake)] - E[D(real)] + λ * GP` | WGAN-GP 损失公式中的 fake/real 是 GAN 数学术语，指生成器输出的'假'样本，非代码 fall-back |
| `src/polaris/pdk/gpic.py` | 22 | P020 | `- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock` | 文件头注释引用规则 14.1 说明禁止 mock，非 mock 代码 |
| `src/polaris/pdk/optodesigner.py` | 21 | P020 | `- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock` | 文件头注释引用规则 14.1 说明禁止 mock，非 mock 代码 |
| `src/polaris/pipeline/integrated.py` | 100 | P060 | `支持两种独立模式（非 fallback，按需选择）：` | 注释说明'支持两种独立模式（非 fallback，按需选择）'，明确声明不是 fall-back |
| `src/polaris/pipeline/integrated.py` | 422 | P060 | `支持两种独立模式（非 fallback，按需选择）：` | 同上，注释说明'非 fallback' |
| `src/polaris/pipeline/training.py` | 405 | P041 | `logger.debug("跳过空基准: %s", name)` | 解析基准数据时，既无设备也无连接的空基准跳过，是有效的输入过滤（logger.debug 记录） |
| `src/polaris/router/advanced_connectors.py` | 16 | P020 | `- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock` | 文件头注释引用规则 14.1 说明禁止 mock，非 mock 代码 |
| `src/polaris/router/curvy_router.py` | 22 | P020 | `- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock` | 文件头注释引用规则 14.1 说明禁止 mock，非 mock 代码 |
| `src/polaris/router/obstacle_grid.py` | 137 | P023 | `self._sparse: set[tuple[int, int]] = set()  # 占位，不使用` | 稀疏/稠密存储双模式中，未使用的属性初始化为空值保持接口一致，非假数据 |
| `src/polaris/router/obstacle_grid.py` | 139 | P023 | `self._array = np.zeros((0, 0), dtype=np.int32)  # 占位，不使用` | 同上，稠密模式下 _array 未使用的占位初始化 |
| `src/polaris/sim/ai_inverse_design.py` | 608 | P021 | `# 判别器损失：最大化 log(D(real)) + log(1-D(fake))` | GAN 判别器损失公式中的 D(fake) 是数学术语 |
| `src/polaris/sim/ai_inverse_design.py` | 613 | P021 | `# 生成器损失：最大化 log(D(fake))（欺骗判别器）` | GAN 生成器损失公式中的 D(fake) 是数学术语 |
| `src/polaris/sim/eqdrc.py` | 15 | P020 | `- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock` | 文件头注释引用规则 14.1 说明禁止 mock，非 mock 代码 |
| `src/polaris/sim/fdtd_simulator.py` | 309 | P060 | `这不是 FDTD 的 fallback，而是独立的解析仿真方式（差距分析 P0-4` | 注释说明'这不是 FDTD 的 fallback，而是独立的解析仿真方式' |
| `src/polaris/trainer/bc.py` | 146 | P041 | `logger.warning("BC 训练跳过：专家数据集为空")` | BC 训练时空数据集返回 {epoch:0, loss:0.0} 表示'未训练'，已 logger.warning 告警，非假数据 |
| `src/polaris/trainer/bc.py` | 274 | P041 | `logger.warning("离散 BC 训练跳过：数据集为空")` | 离散 BC 训练时空数据集返回空指标，已 logger.warning 告警 |
| `src/polaris/trainer/bc.py` | 375 | P041 | `logger.warning("BC 预训练跳过：专家数据集为空")` | BC 预训练时空数据集返回空指标，已 logger.warning 告警 |
| `src/polaris/trainer/bc.py` | 458 | P041 | `logger.warning("BC 预训练跳过：专家数据集为空")` | 离散 BC 预训练时空数据集返回空指标，已 logger.warning 告警 |
| `src/polaris/web/server.py` | 420 | P041 | `logger.warning("跳过无效 JSONL 行: %s", line[:100])` | 解析 JSONL 日志文件时跳过损坏行，是日志解析的标准容错（logger.warning 记录） |

## 4. 测试桩清单（合法）

无。

## 5. 修复验证

- 修复的真 fall-back 数量：3
- 修复后重新扫描命中数：19
- 修复后真 fall-back 数：0
- ✅ 验证通过：所有真 fall-back 已修复。

## 6. 修复明细

### `src/polaris/pdk/gdsfactory_integration.py:466` (P041)

**修复前：**
```python
except Exception as e:
    logger.debug("跳过 gdsfactory 器件 %s: %s", name, e)
```

**修复后：**
```python
改为 raise RuntimeError(f"gdsfactory 器件 '{name}' 加载失败: {e}") from e
```

- 修复理由：except Exception 捕获所有异常后用 logger.debug 静默跳过，违反规则 14.1。改为 raise RuntimeError 明确告警。

### `src/polaris/pipeline/_converters.py:135` (P041)

**修复前：**
```python
if spec is None:
    logger.warning("Placement 转换跳过 %s：未在 circuit.devices 中找到", inst_id)
    continue
```

**修复后：**
```python
改为 raise ValueError(f"Placement 转换失败：实例 '{inst_id}' 未在 circuit.devices 中找到")
```

- 修复理由：sim_placements 与 circuit.devices 不一致属于数据完整性错误，跳过会导致后续布局缺失实例。改为 raise ValueError。

### `src/polaris/sim/fdtd_gpu_engine.py:603` (P041)

**修复前：**
```python
try:
    tidy3d_result = tidy3d_adapter.run_full(device, wavelengths)
    results["tidy3d"] = tidy3d_result
except RuntimeError as e:
    logger.warning("Tidy3D 云端不可用，跳过对比: %s", e)
    results["tidy3d"] = None
```

**修复后：**
```python
改为 if not hasattr(tidy3d_adapter, "run_full"): raise RuntimeError("Tidy3D 云端后端不可用")
```

- 修复理由：Tidy3DAdapter 无 run_full 方法（原代码会抛 AttributeError 未被 except RuntimeError 捕获），且 except 后设 None 是静默兜底。改为显式检查并 raise。

