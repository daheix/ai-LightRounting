# Checklist

## 光器件模型资料库
- [ ] 四大平台（SOI/SiN/InP/LNOI）器件库全部实现，覆盖被动+主动器件
- [ ] 每个器件含几何参数、电光参数、端口定义、包围盒
- [ ] 每个器件参数附带 `source` 字段（文献作者/年份 + 网址 URL）
- [ ] 无虚构数据：所有数值落在公开文献报告区间内
- [ ] 无可靠文献的参数标注为 `estimated` 并给出估算依据
- [ ] 器件支持平移/旋转变换，端口坐标正确更新
- [ ] `DeviceCatalog` 支持按平台/类别检索与序列化（JSON/YAML）

## 来源网址核对（禁止假数据）
- [ ] SOI 平台来源网址可达：latitudeda.com、iccsz.com、cloud.tencent.com（台积电/三星）、noeic.com
- [ ] SiN 平台来源网址可达：imec-int.com、lionix-international.com、doi.org/10.3390/app13063660、patsnap.com、c.m.163.com
- [ ] InP 平台来源网址可达：doi.org/10.3390/app9081588、doi.org/10.1109/JSTQE.2018.2866565、aptechnologies.co.uk、ep.cntronics.com、photonics-benelux.org
- [ ] LNOI 平台来源网址可达：doi.org/10.37188/lam.2025.047、doi.org/10.1364/OL.481827、mdpi.com/2304-6732/12/7/648、doi.org/10.37188/CO.2021-0115、doi.org/10.1364/AOP.411024、doi.org/10.1038/s41586-018-0551-y
- [ ] AI 算法来源网址可达：openreview.net（NeurIPS 2022）、mlforsystems.org（NeurIPS 2025）、chipfoundryservices.com、github.com/Thinklab-SJTU/EDA-AI

## 布局引擎
- [ ] 网表解析器能解析器件实例与连接关系为图结构
- [ ] 布局环境实现 Gymnasium 接口（observation/action/reward）
- [ ] 布局奖励综合面积、HPWL 线长、拥塞、重叠惩罚
- [ ] GNN 编码器能融合图特征与栅格空间特征
- [ ] 布局结果无器件重叠、端口朝向合理

## 布线引擎
- [ ] 波导布线满足最小弯曲半径约束（SOI 2-6μm / SiN 50-100μm）
- [ ] 波导布线满足最小间距约束（SOI 1μm / SiN 2μm）
- [ ] 等长路径约束生效（MZI 臂、差分对长度差 < 阈值）
- [ ] 交叉最小化，必要时使用专用 crossing 器件（0.3dB/-30dB）
- [ ] 拥塞检测与热力图输出正常
- [ ] 损耗预算不超限

## AI 训练框架
- [ ] PPO 智能体实现 actor-critic + clip + GAE
- [ ] 训练循环能跑通：采样→GNN→PPO→环境→奖励→更新
- [ ] 支持断点续训与指标记录
- [ ] 数据集合成器能生成 10/100/1000 器件级网表
- [ ] baseline 解由经典布线器生成并标注奖励

## 评测与可视化
- [ ] matplotlib 版图渲染正常（器件+波导）
- [ ] 支持导出 GDS 兼容中间格式
- [ ] 指标报告含总面积、总线长、总损耗、拥塞分布、DRC 违规数
- [ ] CLI 端到端流水线跑通（网表→布局→布线→版图→报告）

## 测试与质量
- [ ] 器件库参数溯源校验测试通过（source.url 字段非空）
- [ ] 布局/布线约束合规测试通过
- [ ] 训练收敛性冒烟测试通过（小规模网表）
- [ ] 无 lint/typecheck 错误
