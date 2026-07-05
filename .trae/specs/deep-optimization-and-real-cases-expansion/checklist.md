# Checklist

## 49个超80行函数拆分
- [ ] inverse/run_adjoint_optimization 201L拆分
- [ ] place/_align_d2_global 193L拆分
- [ ] place/_residual_pair_fix 154L拆分
- [ ] eme/solve_eme 192L拆分
- [ ] bpm/solve_bpm 187L拆分
- [ ] fdfd/solve_fdfd 176L拆分
- [ ] route/route_circuit 179L拆分
- [ ] gds_tools 6个超80行函数拆分
- [ ] yield 3个超80行函数拆分
- [ ] 其余模块超80行函数拆分
- [ ] 业务代码超80行函数=0

## 真实用例下载扩充
- [ ] ubcpdk下载（~50个用例）
- [ ] cspdk下载（~30个用例）
- [ ] vtt下载（~20个用例）
- [ ] gdsfactory-test-data下载（~100个用例）
- [ ] Luxtelligence LNOI PDK下载（~40个用例）
- [ ] SiEPICfab Shuksan PDK下载（~20个用例）
- [ ] Apollo benchmark下载
- [ ] Perceval量子光子下载
- [ ] KLayout PCells下载
- [ ] Quantum RF PDK下载
- [ ] real_board/总用例数≥1000

## DRC通过率提升
- [ ] PORT_ALIGNMENT弯曲波导补偿实现
- [ ] gdsfactory用例DRC通过率0%→30%+
- [ ] DENSITY_MIN自适应画布实现
- [ ] lidar大电路DRC通过率提升
- [ ] 矩阵型拓扑端口对齐改进
- [ ] 矩阵拓扑DRC 0%→40%+
- [ ] 真实用例DRC通过率3.6%→≥30%

## R36路标补齐
- [x] pretrain.py实现（BC预训练）（460行，10 demos/35 samples/final_loss=1.2375，文献Pomerleau 1989/Ross 2011）
- [x] transfer_learning.py实现（迁移学习）（454行，4参数加载/2冻结/4可训练/final_loss=0.8835，文献Yosinski 2014/Pan 2010）
- [x] D12逆向设计showcase（3个标准器件FoM≥10%）（3/3达标：MMI 16.59dB/WDM 10.06dB/Y分支 10.92dB，文献Piggott 2015/Hughes 2018）

## 13个超800行测试套件拆分
- [ ] verify_advanced/tests 1841L拆分
- [ ] router_advanced/tests 1420L拆分
- [ ] flow/tests 1290L拆分
- [ ] optimizer/tests 1217L拆分
- [ ] trainer/tests 1132L拆分
- [ ] 其余8个测试套件拆分
- [ ] 全部文件≤800行

## 全量回归验证
- [ ] 1000+真实用例端到端测试
- [ ] 组合电路200个DRC通过率≥40%
- [ ] 质量门禁：0超80行函数/0超800行文件/0 except:pass/0 TODO
- [ ] DRC通过率≥30%

## 规则合规
- [ ] R03无fall-back
- [ ] R02学术诚信（新数据源标注来源和license）
- [ ] R05无TODO/FIXME/HACK
- [ ] R04不参与GPU
- [ ] R11 V8极简main分支
- [ ] R07操作记录
