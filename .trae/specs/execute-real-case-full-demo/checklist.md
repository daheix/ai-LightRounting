# Checklist

## 真实输入参数
- [x] real_inputs.py 中所有参数有来源标注（PDK 名/文献/URL）
- [x] 波导参数 neff=2.4 来自 SiEPIC EBeam PDK 220nm SOI strip waveguide 实测
- [x] MMI 分束比 0.48:0.52 来自 SiEPIC EBeam PDK 实测值
- [x] 光栅耦合器插损 1.9dB 来自 SiEPIC EBeam PDK 实测值
- [x] PAM4 100Gbps 参数来自 IEEE 802.3bs 100GBASE-LR4 spec
- [x] 商业对标数据（Intel CWDM4）来自产品 datasheet
- [x] 无任何 mock/placeholder/合成参数

## 真实 case 端到端运行
- [x] run_real_case.py 复用已修复的 10 阶段 stage 代码
- [x] 100Gbps MZI case 10 阶段全部成功（0 失败）
- [x] Clements 4x4 case 10 阶段全部成功（0 失败）
- [x] 无任何 fall-back：失败即 raise（R03）

## 真实性分析
- [x] 每阶段输出有真实性判定（REAL_USABLE / LIMITED_BY_COMPUTE / LIMITED_BY_DATA）
- [x] stage3 AI 布局标注 LIMITED_BY_DATA（无预训练 checkpoint）
- [x] stage5 FDTD 标注 LIMITED_BY_COMPUTE（demo 网格精度）或 REAL_USABLE（解析模型）
- [x] stage10 Adjoint 标注 LIMITED_BY_COMPUTE（JAX AD 开销导致小网格）
- [x] 每阶段与商业产品对标差距已计算并标注

## 完整结果展示报告
- [x] REAL_CASE_REPORT.md 已生成
- [x] 报告含真实输入参数清单（含来源溯源表）
- [x] 报告含 10 阶段逐阶段展示（输入→输出→真实性→对标差距）
- [x] 报告含真实性统计汇总表
- [x] 报告所有数值来自真实运行结果（R02 学术诚信）
- [x] 报告商业对标数据标注来源

## 主入口集成
- [x] run_showcase.py 新增 --real-case 选项
- [x] --real-case 触发真实 case 流程
- [x] 原有合成 demo 流程不受影响（回归测试通过）

## 端到端验证与提交
- [x] `python examples/e2e_showcase/run_showcase.py --real-case` 10 阶段全部成功
- [x] REAL_CASE_REPORT.md 生成且数值真实可溯源
- [x] git add 精确文件 → commit → push origin main（R11）
- [x] 操作记录.md 追加含精确测试数值（R07）
