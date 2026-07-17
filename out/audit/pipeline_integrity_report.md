# PoLaRIS 流程诚信审查报告

> 自动生成于 `scripts/audit_pipeline_integrity.py`
> 规则依据：项目规则 14.1（禁止 fall-back / 假数据 / mock）、规则 18（学术诚信）、规则 7.1（文件 < 600 行）

## 1. 扫描统计

- 扫描目录：`src/polaris/`
- 扫描文件数：424
- 扫描代码行数：158124
- 命中总数：77

### 1.1 按类别分布

| 类别 | 数量 |
|------|------|
| 静默吞异常 (swallow) | 0 |
| mock/fake/dummy/占位 (mock_fake) | 75 |
| 硬编码 (hardcode) | 0 |
| 降级/跳过日志 (degrade_log) | 2 |
| TODO fallback (todo_fb) | 0 |
| if not 返回空值 (empty_return) | 0 |

### 1.2 按严重度分布

| 严重度 | 数量 |
|--------|------|
| high | 0 |
| medium | 69 |
| low | 8 |

## 2. 真 fall-back 清单（违反规则 14.1，需修复）

无。

## 3. 合法异常处理清单（保留）

无。

## 4. 测试桩清单（合法）

无。

## 5. 修复验证

- 修复的真 fall-back 数量：3
- 修复后重新扫描命中数：77
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

