# PoLaRIS 千轮迭代优化工程 - Implementation Plan (1000 Tasks)

> **总轮数**: 1000 轮
> **分类**: 10 大类 / 100 小类 / 1000 原子任务
> **每轮粒度**: 1-4 小时，可独立验证，单独提交

---

## 第一阶段：基础夯实（R101-R300，200 轮）

### [ ] R101: 启动保活脚本与自动提交脚本
- **Priority**: high
- **Depends On**: None
- **Description**: 启动 keepalive 保活脚本和 auto_commit 自动提交脚本，确保开发过程不中断
- **Acceptance Criteria Addressed**: AC-10
- **Test Requirements**:
  - `programmatic` TR-101.1: 保活脚本进程存在
  - `programmatic` TR-101.2: 自动提交脚本进程存在
  - `programmatic` TR-101.3: /tmp/keepalive.log 正常更新

### [ ] R102: 创建工作目录（3-开发规则 #0）
- **Priority**: high
- **Depends On**: R101
- **Description**: 按 3-开发规则创建 polaris-20260630 工作目录，迁移项目代码
- **Acceptance Criteria Addressed**: AC-10
- **Test Requirements**:
  - `programmatic` TR-102.1: 工作目录存在且结构完整
  - `programmatic` TR-102.2: git 仓库正常初始化
  - `programmatic` TR-102.3: 所有代码文件迁移完成

### [ ] R103: 基线测试 - 全量测试运行
- **Priority**: high
- **Depends On**: R102
- **Description**: 运行完整测试套件，记录基线数据（通过数、耗时、覆盖率）
- **Acceptance Criteria Addressed**: AC-8, AC-10
- **Test Requirements**:
  - `programmatic` TR-103.1: 全量测试通过数与 v4.12 一致（337 passed）
  - `programmatic` TR-103.2: 记录总耗时作为性能基线
  - `programmatic` TR-103.3: 记录覆盖率基线

### [ ] R104: 基线测试 - 冒烟测试
- **Priority**: high
- **Depends On**: R103
- **Description**: 运行冒烟测试，验证核心功能正常
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-104.1: test_smoke.py 2/2 通过
  - `programmatic` TR-104.2: 冒烟测试耗时≤2分钟

### [ ] R105: 代码质量基线 - 圈复杂度扫描
- **Priority**: medium
- **Depends On**: R103
- **Description**: 使用 radon 扫描全代码库圈复杂度，记录基线数据
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-105.1: 生成 radon cc 报告
  - `programmatic` TR-105.2: 统计复杂度>15 的函数数量
  - `programmatic` TR-105.3: 识别复杂度最高的 20 个函数

### [ ] R106: 代码质量基线 - 函数行长扫描
- **Priority**: medium
- **Depends On**: R105
- **Description**: 扫描所有函数行长，识别超长函数
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-106.1: 统计>80行的函数数量
  - `programmatic` TR-106.2: 识别最长的 20 个函数
  - `programmatic` TR-106.3: 统计>800行的文件数量

### [ ] R107: 代码质量基线 - 类型注解覆盖率
- **Priority**: medium
- **Depends On**: R106
- **Description**: 扫描类型注解覆盖率
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-107.1: 统计函数参数类型注解覆盖率
  - `programmatic` TR-107.2: 统计返回值类型注解覆盖率
  - `programmatic` TR-107.3: 生成类型覆盖率报告

### [ ] R108: 学术诚信基线 - docstring 文献引用统计
- **Priority**: high
- **Depends On**: R103
- **Description**: 统计每个模块 docstring 中的文献引用数量
- **Acceptance Criteria Addressed**: AC-9
- **Test Requirements**:
  - `programmatic` TR-108.1: 统计 22 子包各模块 docstring 引用数
  - `programmatic` TR-108.2: 识别引用<5的模块清单
  - `human-judgment` TR-108.3: 抽查 10 个模块引用真实性

### [ ] R109: R03 fall-back 基线扫描
- **Priority**: high
- **Depends On**: R103
- **Description**: 扫描代码中潜在的 fall-back 模式（except: pass / return None / return [] 等）
- **Acceptance Criteria Addressed**: AC-8, AC-9
- **Test Requirements**:
  - `programmatic` TR-109.1: grep 统计 `except: pass` 数量
  - `programmatic` TR-109.2: grep 统计 `return None` 数量
  - `programmatic` TR-109.3: 生成 fall-back 风险清单

### [ ] R110: R04 GPU 合规性检查
- **Priority**: high
- **Depends On**: R103
- **Description**: 检查代码中是否有 GPU 相关实现（CuPy/CUDA/ROCm/FP16 等）
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-110.1: grep 检查 cupy/cuda/rocm/metal 关键词
  - `programmatic` TR-110.2: 检查 gpu_backend.py 状态
  - `programmatic` TR-110.3: 确认 R04 合规

### [ ] R111: DRC 模块现状审查
- **Priority**: high
- **Depends On**: R103
- **Description**: 详细审查 DRC 模块现有实现，识别已实现和缺失的规则
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-111.1: 列出 DRC 模块所有文件和函数
  - `programmatic` TR-111.2: 标记已实现的 DRC 规则清单
  - `human-judgment` TR-111.3: 评估现有实现质量

### [ ] R112: LVS 模块现状审查
- **Priority**: high
- **Depends On**: R111
- **Description**: 详细审查 LVS 模块现有实现
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-112.1: 列出 LVS 模块所有文件和函数
  - `programmatic` TR-112.2: 标记已实现的 LVS 功能清单
  - `human-judgment` TR-112.3: 评估现有实现质量

### [ ] R113: 寄生提取模块现状审查
- **Priority**: high
- **Depends On**: R112
- **Description**: 详细审查寄生提取模块现有实现
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-113.1: 列出寄生提取模块所有文件和函数
  - `programmatic` TR-113.2: 标记已实现功能清单
  - `human-judgment` TR-113.3: 评估现有实现质量

### [ ] R114: 良率分析模块现状审查
- **Priority**: high
- **Depends On**: R113
- **Description**: 详细审查良率分析模块现有实现
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-114.1: 列出良率分析模块所有文件和函数
  - `programmatic` TR-114.2: 标记已实现功能清单
  - `human-judgment` TR-114.3: 评估现有实现质量

### [ ] R115: gdsfactory 集成现状审查
- **Priority**: high
- **Depends On**: R114
- **Description**: 详细审查 gdsfactory 集成现状
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-115.1: 列出所有 gdsfactory 相关导入和接口
  - `programmatic` TR-115.2: 测试 gdsfactory 安装状态
  - `human-judgment` TR-115.3: 评估集成深度

### [ ] R116: RL 布局布线模块现状审查
- **Priority**: high
- **Depends On**: R115
- **Description**: 详细审查 RL 布局布线模块现有实现和性能
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-116.1: 列出 RL 模块所有文件和函数
  - `programmatic` TR-116.2: 运行基准测试记录性能基线
  - `human-judgment` TR-116.3: 评估算法先进性

### [ ] R117: FDTD 仿真器现状审查
- **Priority**: high
- **Depends On**: R116
- **Description**: 详细审查 FDTD 仿真器实现和性能
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-117.1: 列出 FDTD 模块所有文件和函数
  - `programmatic` TR-117.2: 运行基准测试记录性能基线
  - `human-judgment` TR-117.3: 评估数值方法先进性

### [ ] R118: FDE 模式求解器现状审查
- **Priority**: high
- **Depends On**: R117
- **Description**: 详细审查 FDE 模式求解器实现和性能
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-118.1: 列出 FDE 模块所有文件和函数
  - `programmatic` TR-118.2: 运行基准测试记录性能基线
  - `human-judgment` TR-118.3: 评估数值方法先进性

### [ ] R119: EME 本征模展开现状审查
- **Priority**: high
- **Depends On**: R118
- **Description**: 详细审查 EME 模块实现和性能
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-119.1: 列出 EME 模块所有文件和函数
  - `programmatic` TR-119.2: 运行基准测试记录性能基线
  - `human-judgment` TR-119.3: 评估数值方法先进性

### [ ] R120: BPM 光束传播法现状审查
- **Priority**: high
- **Depends On**: R119
- **Description**: 详细审查 BPM 模块实现和性能
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-120.1: 列出 BPM 模块所有文件和函数
  - `programmatic` TR-120.2: 运行基准测试记录性能基线
  - `human-judgment` TR-120.3: 评估数值方法先进性

---

### DRC 18 规则实现（R121-R180，60 轮）

### [ ] R121: DRC Width 规则 - 最小线宽检查（几何算法实现）
- **Priority**: high
- **Depends On**: R111
- **Description**: 实现 DRC Width 规则，检查多边形边之间的最小宽度
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-121.1: 矩形波导宽度检查通过
  - `programmatic` TR-121.2: 弯曲波导宽度检查通过
  - `programmatic` TR-121.3: 宽度违规准确报错并定位

### [ ] R122: DRC Width 规则 - 单元测试完善
- **Priority**: high
- **Depends On**: R121
- **Description**: 为 Width 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-122.1: 正常通过用例 5 个
  - `programmatic` TR-122.2: 违规检测用例 5 个
  - `programmatic` TR-122.3: 边界条件用例 3 个

### [ ] R123: DRC Spacing 规则 - 最小间距检查
- **Priority**: high
- **Depends On**: R122
- **Description**: 实现 DRC Spacing 规则，检查图形之间的最小间距
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-123.1: 平行波导间距检查
  - `programmatic` TR-123.2: 弯曲波导间距检查
  - `programmatic` TR-123.3: 间距违规准确报错

### [ ] R124: DRC Spacing 规则 - 单元测试完善
- **Priority**: high
- **Depends On**: R123
- **Description**: 为 Spacing 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-124.1: 正常通过用例 5 个
  - `programmatic` TR-124.2: 违规检测用例 5 个
  - `programmatic` TR-124.3: 边界条件用例 3 个

### [ ] R125: DRC Enclosure 规则 - 层包围检查
- **Priority**: high
- **Depends On**: R124
- **Description**: 实现 DRC Enclosure 规则，检查一层图形对另一层的包围
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-125.1: 完全包围通过
  - `programmatic` TR-125.2: 部分包围违规检测
  - `programmatic` TR-125.3: 包围量计算准确

### [ ] R126: DRC Enclosure 规则 - 单元测试完善
- **Priority**: high
- **Depends On**: R125
- **Description**: 为 Enclosure 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-126.1: 正常通过用例 5 个
  - `programmatic` TR-126.2: 违规检测用例 5 个
  - `programmatic` TR-126.3: 边界条件用例 3 个

### [ ] R127: DRC Coverage 规则 - 层覆盖检查
- **Priority**: high
- **Depends On**: R126
- **Description**: 实现 DRC Coverage 规则，检查一层对另一层的覆盖百分比
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-127.1: 完全覆盖通过
  - `programmatic` TR-127.2: 覆盖不足违规检测
  - `programmatic` TR-127.3: 覆盖率计算准确

### [ ] R128: DRC Coverage 规则 - 单元测试完善
- **Priority**: high
- **Depends On**: R127
- **Description**: 为 Coverage 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-128.1: 正常通过用例 5 个
  - `programmatic` TR-128.2: 违规检测用例 5 个
  - `programmatic` TR-128.3: 边界条件用例 3 个

### [ ] R129: DRC Density 规则 - 图形密度检查
- **Priority**: medium
- **Depends On**: R128
- **Description**: 实现 DRC Density 规则，检查指定区域内的图形密度
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-129.1: 密度合规通过
  - `programmatic` TR-129.2: 密度超标/不足违规检测
  - `programmatic` TR-129.3: 网格密度计算准确

### [ ] R130: DRC Density 规则 - 单元测试完善
- **Priority**: medium
- **Depends On**: R129
- **Description**: 为 Density 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-130.1: 正常通过用例 5 个
  - `programmatic` TR-130.2: 违规检测用例 5 个
  - `programmatic` TR-130.3: 边界条件用例 3 个

### [ ] R131: DRC Notch 规则 - 凹角宽度检查
- **Priority**: medium
- **Depends On**: R130
- **Description**: 实现 DRC Notch 规则，检查图形凹角的最小宽度
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-131.1: 凹角合规通过
  - `programmatic` TR-131.2: 凹角过窄违规检测
  - `programmatic` TR-131.3: 凹角定位准确

### [ ] R132: DRC Notch 规则 - 单元测试完善
- **Priority**: medium
- **Depends On**: R131
- **Description**: 为 Notch 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-132.1: 正常通过用例 3 个
  - `programmatic` TR-132.2: 违规检测用例 3 个
  - `programmatic` TR-132.3: 边界条件用例 2 个

### [ ] R133: DRC Via 规则 - 通孔尺寸/间距检查
- **Priority**: high
- **Depends On**: R132
- **Description**: 实现 DRC Via 规则，检查通孔的尺寸和间距
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-133.1: 通孔尺寸检查
  - `programmatic` TR-133.2: 通孔间距检查
  - `programmatic` TR-133.3: 通孔阵列检查

### [ ] R134: DRC Via 规则 - 单元测试完善
- **Priority**: high
- **Depends On**: R133
- **Description**: 为 Via 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-134.1: 正常通过用例 5 个
  - `programmatic` TR-134.2: 违规检测用例 5 个
  - `programmatic` TR-134.3: 边界条件用例 3 个

### [ ] R135: DRC Area 规则 - 最小面积检查
- **Priority**: medium
- **Depends On**: R134
- **Description**: 实现 DRC Area 规则，检查图形的最小面积
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-135.1: 面积合规通过
  - `programmatic` TR-135.2: 面积过小违规检测
  - `programmatic` TR-135.3: 面积计算准确

### [ ] R136: DRC Area 规则 - 单元测试完善
- **Priority**: medium
- **Depends On**: R135
- **Description**: 为 Area 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-136.1: 正常通过用例 5 个
  - `programmatic` TR-136.2: 违规检测用例 5 个
  - `programmatic` TR-136.3: 边界条件用例 3 个

### [ ] R137: DRC Angle 规则 - 最小角度检查
- **Priority**: medium
- **Depends On**: R136
- **Description**: 实现 DRC Angle 规则，检查图形拐角的最小角度
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-137.1: 角度合规通过
  - `programmatic` TR-137.2: 锐角违规检测
  - `programmatic` TR-137.3: 角度计算准确

### [ ] R138: DRC Angle 规则 - 单元测试完善
- **Priority**: medium
- **Depends On**: R137
- **Description**: 为 Angle 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-138.1: 正常通过用例 3 个
  - `programmatic` TR-138.2: 违规检测用例 3 个
  - `programmatic` TR-138.3: 边界条件用例 2 个

### [ ] R139: DRC End-of-Line 规则 - 线端间距检查
- **Priority**: medium
- **Depends On**: R138
- **Description**: 实现 DRC End-of-Line 规则，检查波导端面的间距
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-139.1: 线端间距合规通过
  - `programmatic` TR-139.2: 线端间距不足违规检测
  - `programmatic` TR-139.3: 线端识别准确

### [ ] R140: DRC End-of-Line 规则 - 单元测试完善
- **Priority**: medium
- **Depends On**: R139
- **Description**: 为 End-of-Line 规则添加完整单元测试
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-140.1: 正常通过用例 3 个
  - `programmatic` TR-140.2: 违规检测用例 3 个
  - `programmatic` TR-140.3: 边界条件用例 2 个

### [ ] R141-R180: DRC 其余 8 规则 + DRC 引擎优化（40 轮，略）
> 注：R141-R180 包含 Step/Alignment/Edge/Perimeter/Symmetry/Array/Extension/MaxWidth 8 个规则实现 + 测试 + DRC 引擎性能优化 + 错误报告格式化 + 批量检查接口等共 40 轮。详细子任务在执行阶段动态生成。

---

### LVS 功能完善（R181-R230，50 轮）

### [ ] R181: LVS 器件识别 - 波导提取
- **Priority**: high
- **Depends On**: R112
- **Description**: 实现从版图中提取波导结构的算法
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-181.1: 直波导提取准确
  - `programmatic` TR-181.2: 弯曲波导提取准确
  - `programmatic` TR-181.3: 波导参数（宽度/长度）提取准确

### [ ] R182: LVS 器件识别 - 定向耦合器提取
- **Priority**: high
- **Depends On**: R181
- **Description**: 实现定向耦合器的版图识别和参数提取
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-182.1: 定向耦合器识别准确
  - `programmatic` TR-182.2: 耦合长度/间距提取准确
  - `programmatic` TR-182.3: 误报率<5%

### [ ] R183: LVS 器件识别 - MMIMMI 提取
- **Priority**: high
- **Depends On**: R182
- **Description**: 实现 MMI（多模干涉仪）的版图识别和参数提取
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-183.1: MMI 识别准确
  - `programmatic` TR-183.2: MMI 尺寸/端口数提取准确
  - `programmatic` TR-183.3: 误报率<5%

### [ ] R184: LVS 器件识别 - 环形谐振器提取
- **Priority**: high
- **Depends On**: R183
- **Description**: 实现环形谐振器的版图识别和参数提取
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-184.1: 环形谐振器识别准确
  - `programmatic` TR-184.2: 半径/耦合间距提取准确
  - `programmatic` TR-184.3: 误报率<5%

### [ ] R185: LVS 网表生成 - 连接性提取
- **Priority**: high
- **Depends On**: R184
- **Description**: 实现从版图提取电路连接关系的算法
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-185.1: 简单电路连接关系正确
  - `programmatic` TR-185.2: 复杂电路连接关系正确
  - `programmatic` TR-185.3: 悬浮节点检测准确

### [ ] R186: LVS 网表对比 - 器件匹配
- **Priority**: high
- **Depends On**: R185
- **Description**: 实现版图网表与原理图网表的器件匹配算法
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-186.1: 同构电路匹配正确
  - `programmatic` TR-186.2: 参数偏差检测准确
  - `programmatic` TR-186.3: 多余/缺失器件检测准确

### [ ] R187: LVS 错误报告 - 短路/开路检测
- **Priority**: high
- **Depends On**: R186
- **Description**: 实现短路和开路故障的检测与定位
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-187.1: 短路故障检测与定位准确
  - `programmatic` TR-187.2: 开路故障检测与定位准确
  - `programmatic` TR-187.3: 错误报告格式清晰

### [ ] R188-R230: LVS 进阶功能完善（43 轮，略）
> 注：包含参数提取匹配优化、悬浮节点检测、LVS 性能优化、SPICE 网表导入导出、层次化 LVS、LVS 单元测试完善、LVS 文档编写等共 43 轮。

---

### 寄生提取与良率分析（R231-R300，70 轮）

### [ ] R231: 寄生电阻提取 - 片电阻法
- **Priority**: high
- **Depends On**: R113
- **Description**: 实现基于片电阻（sheet resistance）的波导寄生电阻提取
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-231.1: 直波导电阻计算与解析解误差<5%
  - `programmatic` TR-231.2: 弯曲波导电阻计算准确
  - `programmatic` TR-231.3: 温度系数支持

### [ ] R232: 寄生电容提取 - 平行板近似
- **Priority**: high
- **Depends On**: R231
- **Description**: 实现基于平行板近似的波导寄生电容提取
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-232.1: 平板电容计算与解析解误差<5%
  - `programmatic` TR-232.2: 侧边电容修正
  - `programmatic` TR-232.3: 耦合电容计算

### [ ] R233: 寄生电感提取 - 近似解析法
- **Priority**: medium
- **Depends On**: R232
- **Description**: 实现基于近似解析公式的波导寄生电感提取
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-233.1: 直波导电感计算合理
  - `programmatic` TR-233.2: 互感计算
  - `programmatic` TR-233.3: 与文献典型值对比<20%误差

### [ ] R234: S 参数生成 - 寄生网络
- **Priority**: medium
- **Depends On**: R233
- **Description**: 实现从寄生参数生成 S 参数的功能
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-234.1: 简单 RLC 网络 S 参数正确
  - `programmatic` TR-234.2: 无源性验证
  - `programmatic` TR-234.3: 互易性验证

### [ ] R235: SPICE 网表输出
- **Priority**: medium
- **Depends On**: R234
- **Description**: 实现寄生参数的 SPICE 网表导出功能
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-235.1: 生成的 SPICE 网表语法正确
  - `programmatic` TR-235.2: 与仿真器兼容性验证
  - `programmatic` TR-235.3: 参数化模型支持

### [ ] R236: 良率分析 - Monte Carlo 引擎
- **Priority**: high
- **Depends On**: R114
- **Description**: 实现 Monte Carlo 仿真引擎，支持工艺偏差随机采样
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-236.1: 正态分布采样准确
  - `programmatic` TR-236.2: 均匀分布采样准确
  - `programmatic` TR-236.3: 相关采样支持

### [ ] R237: 良率分析 - 工艺偏差建模
- **Priority**: high
- **Depends On**: R236
- **Description**: 实现工艺偏差模型（宽度偏差、厚度偏差、折射率偏差等）
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-237.1: 波导宽度偏差模型
  - `programmatic` TR-237.2: 层厚度偏差模型
  - `programmatic` TR-237.3: 折射率偏差模型

### [ ] R238: 良率分析 - 良率预估
- **Priority**: high
- **Depends On**: R237
- **Description**: 实现基于 Monte Carlo 结果的良率预估算法
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-238.1: 良率估计收敛性验证
  - `programmatic` TR-238.2: 置信区间计算准确
  - `programmatic` TR-238.3: 已知分布良率计算正确

### [ ] R239: 良率分析 - 灵敏度分析
- **Priority**: medium
- **Depends On**: R238
- **Description**: 实现参数灵敏度分析（Sobol 指数 / 相关系数法）
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-239.1: 一阶灵敏度计算
  - `programmatic` TR-239.2: 总灵敏度计算
  - `programmatic` TR-239.3: 灵敏度排序正确

### [ ] R240: 良率分析 - 最坏情况分析
- **Priority**: medium
- **Depends On**: R239
- **Description**: 实现最坏情况分析（Worst Case Analysis）
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-240.1: 角点分析（Corner Analysis）
  - `programmatic` TR-240.2: 最坏情况搜索
  - `programmatic` TR-240.3: 结果物理合理

### [ ] R241-R300: 寄生提取+良率分析进阶完善（60 轮，略）
> 注：包含寄生提取精度提升、3D 效应修正、良率加速（拉丁超立方采样/重要性采样）、良率优化、批量仿真接口、完整测试套件、文档编写等共 60 轮。

---

## 第二阶段：核心增强（R301-R600，300 轮）

### gdsfactory 深度集成（R301-R350，50 轮）

### [x] R301: gdsfactory 组件导入 - GDSII 读取增强
- **Priority**: high
- **Depends On**: R115
- **Description**: 增强 GDSII 读取能力，完全兼容 gdsfactory 输出格式
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-301.1: 导入 gdsfactory 标准组件无损失
  - `programmatic` TR-301.2: 层次结构保留完整
  - `programmatic` TR-301.3: 所有层号映射正确

### [x] R302: gdsfactory 组件导出 - GDSII 写出增强
- **Priority**: high
- **Depends On**: R301
- **Description**: 增强 GDSII 写出能力，输出与 gdsfactory 兼容
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-302.1: 导出文件可被 gdsfactory 正确读取
  - `programmatic` TR-302.2: 层次结构导出完整
  - `programmatic` TR-302.3: 往返导入导出无信息损失

### [x] R303: gdsfactory PDK 双向兼容 - 层映射
- **Priority**: high
- **Depends On**: R302
- **Description**: 实现 gdsfactory PDK 与 PoLaRIS PDK 的层映射转换
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-303.1: SiEPIC PDK 层映射正确
  - `programmatic` TR-303.2: 自定义层映射支持
  - `programmatic` TR-303.3: 映射配置文件化

### [x] R304: gdsfactory 联合仿真 - 组件级
- **Priority**: high
- **Depends On**: R303
- **Description**: 实现 gdsfactory 组件直接导入 PoLaRIS 进行仿真的工作流
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-304.1: gdsfactory 波导→FDTD 仿真流程顺畅
  - `programmatic` TR-304.2: 端口自动识别与 S 参数提取
  - `programmatic` TR-304.3: 结果回传给 gdsfactory

### [ ] R305-R350: gdsfactory 集成进阶（46 轮，略）
> 注：包含电路级联合仿真、PCell 双向兼容、KLayout DRC 集成、gdsfactory 插件、完整测试、文档教程等共 46 轮。

---

### RL 布局布线增强（R351-R450，100 轮）

### [ ] R351: RL 环境增强 - 大规模电路支持
- **Priority**: high
- **Depends On**: R116
- **Description**: 升级 RL 环境，支持 100+ 组件的大规模电路布局布线
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-351.1: 100 组件电路环境初始化正常
  - `programmatic` TR-351.2: 状态空间表示高效
  - `programmatic` TR-351.3: 内存占用≤500MB

### [ ] R352: RL 算法升级 - PPO 优化
- **Priority**: high
- **Depends On**: R351
- **Description**: 升级 PPO 算法，加入 GAE、熵正则化调优、学习率调度
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-352.1: 收敛速度提升≥30%
  - `programmatic` TR-352.2: 最终性能提升≥10%
  - `programmatic` TR-352.3: 训练稳定性提升

### [ ] R353: RL 多目标优化 - 奖励函数设计
- **Priority**: high
- **Depends On**: R352
- **Description**: 实现多目标优化奖励函数（面积+时延+损耗+串扰）
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-353.1: 多目标权重可配置
  - `programmatic` TR-353.2: Pareto 前沿生成
  - `programmatic` TR-353.3: 各目标权衡合理

### [ ] R354: RL 预训练模型库 - 基础模型
- **Priority**: medium
- **Depends On**: R353
- **Description**: 建立预训练模型库，提供多种场景的预训练策略
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-354.1: 3 种基础预训练模型可用
  - `programmatic` TR-354.2: 微调收敛速度提升≥2x
  - `programmatic` TR-354.3: 模型格式标准化

### [ ] R355: RL 混合布局 - 手动约束支持
- **Priority**: medium
- **Depends On**: R354
- **Description**: 实现混合布局模式，支持用户手动放置部分组件，RL 自动布局剩余
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-355.1: 固定组件约束正确执行
  - `programmatic` TR-355.2: 区域约束正确执行
  - `programmatic` TR-355.3: 混合布局结果合理

### [ ] R356-R450: RL 增强进阶（95 轮，略）
> 注：包含 Curiosity 探索、Transformer 策略网络、多智能体协作、分层强化学习、模仿学习、离线 RL、Benchmark 构建、完整测试套件、文档教程等共 95 轮。

---

### 仿真性能优化（R451-R550，100 轮）

### [ ] R451: FDTD 性能优化 - 多级网格
- **Priority**: high
- **Depends On**: R117
- **Description**: 实现 FDTD 多级网格（Subgridding）算法，精细区域用细网格，其余用粗网格
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-451.1: 多级网格正确性验证（与均匀网格误差<1%）
  - `programmatic` TR-451.2: 性能提升≥30%
  - `programmatic` TR-451.3: 网格界面反射< -40dB

### [ ] R452: FDTD 性能优化 - 卷积完美匹配层 CPML
- **Priority**: high
- **Depends On**: R451
- **Description**: 优化 CPML 实现，减少 PML 层数，降低计算量
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-452.1: PML 反射< -50dB
  - `programmatic` TR-452.2: PML 层数从 10 减到 6
  - `programmatic` TR-452.3: 总计算量减少≥15%

### [ ] R453: FDE 性能优化 - 特征值求解加速
- **Priority**: high
- **Depends On**: R118
- **Description**: 优化 FDE 特征值求解器，使用移位-逆迭代和稀疏矩阵技术
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-453.1: 求解速度提升≥30%
  - `programmatic` TR-453.2: 精度损失<0.1%
  - `programmatic` TR-453.3: 内存占用减少≥20%

### [ ] R454: EME 性能优化 - 模式数自适应
- **Priority**: high
- **Depends On**: R119
- **Description**: 实现 EME 模式数自适应选择，根据收敛性动态调整模式数量
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-454.1: 自适应模式选择收敛正确
  - `programmatic` TR-454.2: 计算量减少≥25%
  - `programmatic` TR-454.3: 精度损失<0.5%

### [ ] R455: BPM 性能优化 - 大步长算法
- **Priority**: medium
- **Depends On**: R120
- **Description**: 实现 BPM 大步长算法（高阶 Padé 近似 / 广义传播算子）
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-455.1: 步长增大 3-5 倍
  - `programmatic` TR-455.2: 总计算时间减少≥40%
  - `programmatic` TR-455.3: 精度损失<1%

### [ ] R456: JAX(CPU) 向量化增强 - 核心循环
- **Priority**: high
- **Depends On**: R452
- **Description**: 将 FDTD/FDE 核心循环用 JAX jit/vmap 向量化重写
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-456.1: JAX 后端正确性验证
  - `programmatic` TR-456.2: 性能提升≥25%
  - `programmatic` TR-456.3: NumPy 后端仍可用（双后端）

### [ ] R457-R550: 性能优化进阶（94 轮，略）
> 注：包含 RCWA 性能优化、子网络分解加速、S 参数级联优化、内存优化、并行计算（多进程）、缓存机制、性能基准测试套件、性能文档编写等共 94 轮。

---

### 量子光子增强（R551-R600，50 轮）

### [ ] R551: 量子光子增强 - 连续变量量子计算
- **Priority**: medium
- **Depends On**: R103
- **Description**: 实现连续变量（CV）量子计算仿真框架（压缩态/位移/旋转/分束器）
- **Acceptance Criteria Addressed**: FR-8
- **Test Requirements**:
  - `programmatic` TR-551.1: 高斯态演化正确
  - `programmatic` TR-551.2: 分束器/移相器操作正确
  - `programmatic` TR-551.3: 零差检测正确

### [ ] R552: 量子光子增强 - 量子纠错编码
- **Priority**: medium
- **Depends On**: R551
- **Description**: 实现光子量子纠错码（Shor 码 / Steane 码 / 表面码简化版）
- **Acceptance Criteria Addressed**: FR-8
- **Test Requirements**:
  - `programmatic` TR-552.1: 三量子比特重复码正确
  - `programmatic` TR-552.2: Steane 码编码正确
  - `programmatic` TR-552.3: 纠错逻辑验证

### [ ] R553: 量子光子增强 - 资源态生成
- **Priority**: medium
- **Depends On**: R552
- **Description**: 实现光子资源态（GHZ 态 / 簇态 / NOON 态）生成电路
- **Acceptance Criteria Addressed**: FR-8
- **Test Requirements**:
  - `programmatic` TR-553.1: GHZ 态保真度>95%
  - `programmatic` TR-553.2: 簇态生成正确
  - `programmatic` TR-553.3: NOON 态生成正确

### [ ] R554: 量子光子增强 - 噪声模型增强
- **Priority**: medium
- **Depends On**: R553
- **Description**: 增强噪声模型（光子损耗 / 相位噪声 / 探测器暗计数 / 效率）
- **Acceptance Criteria Addressed**: FR-8
- **Test Requirements**:
  - `programmatic` TR-554.1: 损耗模型符合 Beer-Lambert 定律
  - `programmatic` TR-554.2: 相位噪声模型物理正确
  - `programmatic` TR-554.3: 探测器模型完整

### [ ] R555: 量子光子增强 - 实验数据拟合接口
- **Priority**: low
- **Depends On**: R554
- **Description**: 实现实验数据拟合接口（S 参数拟合 / 损耗提取 / 耦合效率提取）
- **Acceptance Criteria Addressed**: FR-8
- **Test Requirements**:
  - `programmatic` TR-555.1: S 参数拟合准确
  - `programmatic` TR-555.2: 损耗提取正确
  - `programmatic` TR-555.3: 拟合优度指标输出

### [ ] R556-R600: 量子光子进阶（45 轮，略）
> 注：包含量子游走、量子随机行走、量子机器学习基础、量子优越性验证、完整测试套件、文档教程等共 45 轮。

---

## 第三阶段：质量收官（R601-R1000，400 轮）

### 代码质量全面提升（R601-R700，100 轮）

### [ ] R601-R620: 函数行长优化 - 超长函数拆分（20 轮）
> 将所有>80行的函数拆分为≤80行，每轮 3-5 个函数

### [ ] R621-R640: 圈复杂度优化 - 高复杂度函数重构（20 轮）
> 将圈复杂度>15的函数重构为≤15，每轮 3-5 个函数

### [ ] R641-R660: 类型注解完善（20 轮）
> 完善所有函数的类型注解，覆盖率达 100%

### [ ] R661-R680: 文档字符串完善（20 轮）
> 完善所有公开函数/类的 docstring，Google 风格

### [ ] R681-R700: 测试覆盖率提升（20 轮）
> 将测试覆盖率从当前提升至≥90%

---

### 学术诚信全面核查（R701-R800，100 轮）

### [ ] R701-R750: 模块文献引用补齐（50 轮）
> 为每个模块 docstring 添加≥5篇文献引用，每轮 1-2 个模块

### [ ] R751-R775: 物理公式溯源验证（25 轮）
> 核查所有物理公式的文献溯源，每轮 5-10 个公式

### [ ] R776-R800: 创新点标注与说明（25 轮）
> 标注所有创新点 `*创新*` 并详细说明底层逻辑

---

### R03 fall-back 彻底清除（R801-R850，50 轮）

### [ ] R801-R825: except: pass 清除（25 轮）
> 找出并修复所有 `except: pass` / 空异常处理，替换为适当的 raise 或日志记录

### [ ] R826-R850: return None / return [] 清除（25 轮）
> 找出并修复所有静默 return None / return [] 的 fall-back 模式

---

### 性能优化与基准测试（R851-R900，50 轮）

### [ ] R851-R870: 核心模块性能调优（20 轮）
> 对 FDTD/FDE/EME/BPM/RL 进行第二轮性能调优

### [ ] R871-R885: 基准测试套件建设（15 轮）
> 建立完整的性能基准测试套件，包含 20+ 标准测试用例

### [ ] R886-R900: 内存优化（15 轮）
> 优化大仿真的内存占用，减少峰值内存 30%+

---

### 文档与教程完善（R901-R950，50 轮）

### [ ] R901-R915: API 文档 100% 覆盖（15 轮）
> 确保所有公开 API 都有文档

### [ ] R916-R930: 入门教程编写（15 轮）
> 编写从安装到第一个仿真的完整入门教程

### [ ] R931-R945: 进阶教程编写（15 轮）
> 编写进阶教程（DRC/LVS/RL/量子/性能优化）

### [ ] R946-R950: 示例库建设（5 轮）
> 建设 20+ 完整示例（器件/电路/系统级）

---

### 综合验证与收官（R951-R1000，50 轮）

### [ ] R951-R970: 全量测试回归（20 轮）
> 运行完整测试套件，修复所有失败，确保 100% 通过

### [ ] R971-R985: 集成测试完善（15 轮）
> 完善端到端集成测试，覆盖主要工作流

### [ ] R986-R995: v5.0 版本准备（10 轮）
> 版本号升级、CHANGELOG 编写、发布说明

### [ ] R996-R1000: 1000 轮收官总结（5 轮）
> 生成 1000 轮迭代总结报告，更新商业计划，准备开源发布

---

## 任务统计

| 阶段 | 轮数范围 | 轮数 | 占比 |
|------|---------|------|------|
| 第一阶段：基础夯实 | R101-R300 | 200 | 20% |
| 第二阶段：核心增强 | R301-R600 | 300 | 30% |
| 第三阶段：质量收官 | R601-R1000 | 400 | 40% |
| 机动预留 | — | 100 | 10% |
| **合计** | **R101-R1000** | **1000** | **100%** |

> **注**: 为保证任务列表可读性，本文件列出约 200 个代表性任务，剩余 800 个原子任务在执行阶段动态生成并细化。每轮任务遵循：小步快跑、单独验证、单独提交、可追溯的原则。
