# 光电子单位统一+深度优化+1000子任务 Checklist

## 阶段1: P0 单位bug修复

- [ ] pretrain.py canvas_w默认1.0→1000.0，缺失raise KeyError
- [ ] pretrain.py 归一化1e5→1000.0（canvas_w/1000.0）
- [ ] transfer_learning.py canvas_w默认1.0→1000.0
- [ ] transfer_learning.py 归一化1e5→1000.0
- [ ] rl_pareto.py width→width_um字段读取，缺失raise KeyError
- [ ] rl_pareto.py _CANVAS_SIZE_UM=3200→动态读取circuit canvas_w
- [ ] rl_advanced.py width→width_um，_CANVAS_SIZE_UM动态读取
- [ ] 调用simphony前显式换算 wl_um = wl_nm/1000.0
- [ ] specs.py docstring标注单位制（μm/nm/dB/ps）

## 阶段2: P0 42个超80行函数拆分

- [ ] route/__init__.py bend_compensate 259L 拆分
- [ ] inverse/adjoint.py run_adjoint_optimization 201L 拆分
- [ ] place/align.py _align_d2_global 193L 拆分
- [ ] eme/solver.py solve_eme 192L 拆分
- [ ] bpm/solver.py solve_bpm 187L 拆分
- [ ] fdfd/solver.py solve_fdfd 176L 拆分
- [ ] gds_tools multi_clip_gdsii 150L 拆分
- [ ] 15个100-125L函数拆分完成
- [ ] 16个81-94L函数拆分完成
- [ ] 全量扫描：0个超80行业务函数

## 阶段3: P1 真实用例持续扩充

- [ ] 搜索IMEC/AIM/AMF公开示例
- [ ] 搜索IEEE/Optica论文公开数据
- [ ] 下载新数据源到real_board/
- [ ] 从SiEPIC GDS提取更多expert_demos三元组
- [ ] real_board/ 总用例数≥5000

## 阶段4: P1 DRC通过率持续提升

- [ ] 优化siepic多器件GDS的DRC
- [ ] 优化expert_demos端口坐标精度
- [ ] 改进矩阵拓扑端口对齐
- [ ] DRC通过率≥50%

## 阶段5: 验证与提交

- [ ] 单位一致性验证（全部模块扫描，0处不一致）
- [ ] 全量回归测试通过率≥97%
- [ ] 质量门禁验证（0超80行函数，0 except:pass，0 TODO）
- [ ] 操作记录.md追加本轮记录
- [ ] 代码提交到main分支并push
