# Checklist

## P0-1 布局重叠修复
- [x] `_place_random` 增加重叠检测（`_has_overlap`）
- [x] `_place_random` 增加合法化（`_legalize_overlaps` + `_find_nearest_free`）
- [x] `_place_random` 增加画布扩大重试（3 次 ×1.5）
- [x] 辅助函数来源注释标注 DREAMPlace TCAD 2020

## P0-2 布线拥塞修复
- [x] `_CurvyRouter` 拆分到 `polaris.pipeline.curvy_router` 独立文件
- [x] 实现 rip-up and reroute 算法（最多 3 次迭代）
- [x] 障碍物半宽优化为 waveguide_width/2 + min_spacing_um = 1.25μm
- [x] 复用同一 GridRouter 实例
- [x] `_DefaultSimulator` 拆分到 `polaris.pipeline.default_simulator`

## P0-3 DRC 规则缺失修复
- [x] `CheckContext` 添加 `canvas_w`/`canvas_h`/`pin_pairs` 字段
- [x] `check_enclosure` 函数实现（IHP SG25H5 PDK 来源）
- [x] `check_notch` 函数实现（KLayout DRC runset 来源）
- [x] `check_pin_match` 函数实现（SiEPIC EBeam PDK 来源）
- [x] `ConstraintChecker.check()` 调用全部 16 项 ViolationType 检查
- [x] `SimLoop._check_constraints` 填充 CheckContext 的 waveguide_widths 字段（默认 0.5μm）
- [x] `SimLoop._check_constraints` 填充 CheckContext 的 waveguide_lengths 字段（path 长度）
- [x] `SimLoop._check_constraints` 填充 CheckContext 的 device_areas 字段（w×h）
- [x] `SimLoop._check_constraints` 填充 CheckContext 的 port_connections 字段（从 circuit.connections 提取）
- [x] `SimLoop._check_constraints` 填充 CheckContext 的 canvas_w/canvas_h 字段（从 circuit 提取）
- [x] `SimLoop._check_constraints` 填充 CheckContext 的 pin_pairs 字段（从 circuit 端口方向提取）
- [x] 修复 `ViolationType.ENCLOSEMENT` 拼写错误 → `ENCLOSURE`（5 个文件）

## 验证
- [x] `tests/test_sim_loop.py` 测试通过（27 passed）
- [x] `tests/test_integration.py` 测试通过
- [x] DRC 测试通过（127 passed: test_drc_extended/test_klayout_drc/test_fabrication_constraints/test_hierarchical_drc/test_r23_eqdrc）
- [x] MVP 5 次迭代成功率 100% (>= 80%)
- [x] MVP DRC 通过率 100%
- [x] `integrated.py` 文件行数 589 < 600（规则 7.1）
- [x] 无新增 fall-back / 假数据（规则 14.1）
- [x] 新增参数均标注 PDK / 论文来源（规则 18 学术诚信）
