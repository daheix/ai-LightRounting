# 端到端 Demo Showcase 验收清单

## 骨架与日志
- [ ] `examples/e2e_showcase/` 目录与 `__init__.py` 已创建
- [ ] `logging_config.py` 实现控制台彩色日志 + JSONL 文件日志 + 阶段计时装饰器
- [ ] `run_showcase.py` 主入口支持 `--stage` 单阶段运行与全流程运行
- [ ] `out/e2e_showcase/{logs,gds,verilog_a,spice,reports}` 输出目录自动创建

## 阶段 1 PDK 器件目录
- [ ] 遍历 SOI/SiN/InP/LNOI 四平台
- [ ] 每平台列出器件计数与 3+ 代表器件参数
- [ ] 标注器件来源 foundry

## 阶段 2 电路规格定义
- [ ] MZI 干涉仪 CircuitSpec 含 5 器件
- [ ] Clements 4x4 CircuitSpec 含 6 分束器 + 4 相移器
- [ ] 量子玻色采样电路规格含 4 模酉矩阵

## 阶段 3 AI 布局
- [ ] 尝试加载 R34 预训练 checkpoint
- [ ] checkpoint 不存在时降级为解析布局并明确告警（非 fall-back 假数据）
- [ ] 对 3 个电路生成布局坐标
- [ ] 计算 HPWL 指标
- [ ] 输出 ASCII 布局预览

## 阶段 4 智能布线
- [ ] 对 3 个电路执行布线
- [ ] 计算总插入损耗（dB）
- [ ] 计算交叉数与弯曲数
- [ ] 输出路径几何 ASCII 预览

## 阶段 5 仿真验证
- [ ] MZI 频域 S 参数扫描 1500-1600nm
- [ ] 输出谐振波长与消光比
- [ ] Clements 酉矩阵传输计算
- [ ] MZI 调制器 PAM4 眼图生成
- [ ] 计算 BER 与 SNR

## 阶段 6 DRC/LVS 验证
- [ ] 执行 16 项 DRC 规则检查
- [ ] 输出违规清单（坐标/规则名/严重度）
- [ ] 输出 DRC 通过率
- [ ] 执行 LVS 网表比对
- [ ] 输出一致性布尔结果与差异清单

## 阶段 7 GDS 导出
- [ ] 3 个电路导出为 GDSII 文件
- [ ] 输出文件大小/结构数/层次数
- [ ] 验证 GDS 文件可重新加载

## 阶段 8 光电协同
- [ ] 为 5+ 器件生成 Verilog-A 模型文件
- [ ] 生成 Ngspice 联合仿真网表
- [ ] 生成 PAM4 眼图与 BER

## 阶段 9 量子光子验证
- [ ] 4 光子 4 模玻色采样执行
- [ ] 概率分布守恒验证（总和 = 1）
- [ ] HOM 干涉 |1,1⟩ 概率 = 0 验证
- [ ] KLM CNOT 成功率 = 0.25 验证
- [ ] Hadamard 门酉性验证

## 结构化日志
- [ ] 控制台彩色阶段头（绿/黄/红/蓝）
- [ ] JSONL 文件追加日志
- [ ] 日志含 stage_id/stage_name/status/duration_s/inputs/outputs 字段

## 汇总报告
- [ ] `out/e2e_showcase/report.md` 生成
- [ ] 报告含 9 阶段状态表
- [ ] 报告含产物文件清单
- [ ] 报告含 ASCII 可视化

## Web 页面
- [ ] `/api/showcase/run` 端点返回 run_id
- [ ] `/api/showcase/report/{run_id}` 端点返回报告
- [ ] `/api/showcase/stages/{run_id}/{stage_id}` 端点返回单阶段结果
- [ ] `showcase.html` 9 阶段卡片布局
- [ ] `showcase.js` 轮询进度与日志流
- [ ] `showcase.css` 卡片样式与状态色

## 测试与质量
- [ ] `tests/test_e2e_showcase.py` 验证 9 阶段独立运行
- [ ] 端到端串联测试通过
- [ ] JSONL 日志格式与字段完整性验证
- [ ] Markdown 报告生成验证
- [ ] ruff check All checks passed
- [ ] 全量回归测试无新增失败

## 学术诚信
- [ ] 所有器件参数标注来源（SiEPIC/Ligentec/HyperLight/Pattern Project）
- [ ] 所有公式标注推导来源
- [ ] checkpoint 降级时明确告警，无假数据 fall-back
- [ ] 量子光子验证基于真实物理公式（Aaronson 2011/Hong 1987/Knill 2001）
