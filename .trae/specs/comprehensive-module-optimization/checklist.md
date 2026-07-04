# Checklist

## 真实用例100%准确率
- [ ] 6个pipeline_failed修复（Tarjan SCC替代Kahn拓扑排序）
- [ ] 19个gdsfactory演示文件分类为non_circuit_demo
- [ ] 真实用例可测试342个成功率100%

## R03零fall-back
- [ ] trainer 3处except:pass清零
- [ ] flow 1处except:pass清零
- [ ] circuit 1处except:pass清零
- [ ] verify_advanced 24处return None/return []清零
- [ ] router_advanced 21处return None/return []清零
- [ ] flow 18处return None/return []清零
- [ ] gds_tools 15处return None/return []清零
- [ ] 其余模块return None/return []清零

## R05零TODO/FIXME/HACK
- [ ] circuit 10处TODO清零
- [ ] lumerical 5处TODO清零
- [ ] verify_advanced 3处TODO清零
- [ ] flow/gds_tools/nn/parasitic/yield TODO清零

## R11质量门禁
- [ ] place/analytical.py 1480L拆分到≤800L
- [x] pdk/catalog.py 936L拆分到≤800L ✅ 76L/781L/128L, 43测试通过
- [x] gui/interactive.py 824L拆分到≤800L ✅ 93L/594L/268L, 30测试通过
- [x] gui/web_server.py 823L拆分到≤800L ✅ 156L/353L/487L, 30测试通过
- [x] quantum_advanced/distributed_ppo.py 808L拆分到≤800L ✅ 406L/229L/90L/295L, 42测试通过
- [x] drc/engine.py 803L拆分到≤800L ✅ 465L/219L/233L, 51测试通过
- [ ] 43个超80行函数拆分
- [ ] 12个圈复杂度>15函数降低

## 测试覆盖
- [ ] multiphysics测试补充
- [ ] nn测试补充
- [ ] gds_tools测试补充
- [ ] flow测试补充

## 规则合规
- [ ] R03无fall-back
- [ ] R02学术诚信（Tarjan 1972文献溯源）
- [ ] R05无TODO/FIXME/HACK
- [ ] R04不参与GPU
- [ ] R11 V8极简main分支
- [ ] R07操作记录
