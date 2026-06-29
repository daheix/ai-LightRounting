# 100 轮商业 Bug 排查核查清单

> 每轮迭代开始前必须执行此清单

---

## 每轮开始前核查

```
[ ] 确认在 main 分支: git branch --show-current
[ ] 确认 auto_commit 守护进程运行: ps aux | grep auto_commit
[ ] 确认 keepalive 守护进程运行: ps aux | grep keepalive
[ ] 确认无未提交代码: git status --short
[ ] 读取操作记录.md 最新轮次
[ ] 读取商业活动计划表-五年.md 待覆盖区域
```

---

## 每轮排查流程

### 阶段 1: 源码扫描（D1-D5 五维度）
```
[ ] D1 物理公式: 遍历子包所有函数，提取数字常量与文献比对
[ ] D2 算法实现: AST 解析验证伪代码与实际代码一致性
[ ] D3 数据流: 跟踪输入→处理→输出，检查无静默丢弃
[ ] D4 API 契约: 检查 docstring 参数/类型/范围与代码一致
[ ] D5 边界条件: 测试空输入/零除/NaN/Inf/溢出
```

### 阶段 2: 问题分类
```
[ ] 发现 P0 问题? → 立即修复（不进入下一阶段）
[ ] 发现 P1 问题? → 标记，当日修复
[ ] 发现 P2 问题? → 标记，本轮内修复
[ ] 未发现问题? → 声明无 Bug，附覆盖范围说明
```

### 阶段 3: 修复验证
```
[ ] 代码修改完成
[ ] 新增回归测试覆盖修复点
[ ] pytest 运行通过（全部测试）
[ ] AST 扫描确认无新 R03 违规
```

### 阶段 4: 文档同步
```
[ ] 操作记录.md 追加本轮记录（5 分钟内）
[ ] 标记下一轮待覆盖区域
[ ] 更新进度文件: echo "R{N}" > /tmp/current_round
```

---

## R6 专项核查（R6-R10: sim/ 仿真核心）

### R6 聚焦文件
- sim/fdtd_jax_backend.py — FDTD 物理常数/数值稳定性
- sim/fdtd_gpu_engine.py — GPU 战略合规

### R6 必查项
```
[ ] MU0/EPS0/光速 c/电阻 q/普朗克 h → CODATA 2018 精确值
[ ] FDTD 时间步长稳定性（Courant-Friedrichs-Lewy 条件）
[ ] PML 吸收边界条件参数
[ ] Yee 网格离散化正确性
[ ] use_gpu 必须为 False（R04）
[ ] JAX 后端无 GPU fallback
```

### R6 已知问题追溯
- R5-P0-2: MU0 = 1.257e-6（H/m，修正后）→ 需持续核查
- R5-P0-3: GPUFDTDEngine.__init__ raise R04 → 需持续核查
