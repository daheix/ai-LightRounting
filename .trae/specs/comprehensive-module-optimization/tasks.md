# Tasks

## 阶段1: P0 真实用例100%准确率（并行）

- [ ] Task 1: 修复6个pipeline_failed——Tarjan SCC替代Kahn拓扑排序
  - [ ] SubTask 1.1: 在place/analytical.py实现_tarjan_scc()强连通分量算法
  - [ ] SubTask 1.2: 实现_condensation_dag()收缩SCC为DAG
  - [ ] SubTask 1.3: 修改_legalize()用SCC depth替代Kahn depth
  - [ ] SubTask 1.4: 回归测试6个失败用例（Crossings/MZI1/mzi_bends等）
  - [ ] SubTask 1.5: 验证真实用例100%成功率

- [ ] Task 2: 分类19个gdsfactory演示文件为non_circuit_demo
  - [ ] SubTask 2.1: 在test_real_circuits.py增加预筛逻辑（connections/routes/nets全空→non_circuit_demo）
  - [ ] SubTask 2.2: 更新测试报告统计（non_circuit_demo不计入失败率）
  - [ ] SubTask 2.3: 验证361→342可测试用例，336/342=98.2%→修复Task1后100%

## 阶段2: P0 R03 except:pass清零（并行）

- [ ] Task 3: 清理trainer模块3处except:pass
  - [ ] SubTask 3.1: 定位trainer/中3处except:pass，改为raise TrainerError
- [ ] Task 4: 清理flow模块1处except:pass
  - [ ] SubTask 4.1: 定位flow/中except:pass，改为raise FlowError
- [ ] Task 5: 清理circuit模块1处except:pass
  - [ ] SubTask 5.1: 定位circuit/中except:pass，改为raise CircuitError

## 阶段3: P0 R03 return None/return []清零（并行，按模块分批）

- [ ] Task 6: 清理verify_advanced 24处fall-back（6 return None + 18 return []）
  - [ ] SubTask 6.1: 逐处审核，假数据改raise，合法空返回加注释
- [ ] Task 7: 清理router_advanced 21处fall-back（12 return None + 9 return []）
  - [ ] SubTask 7.1: 逐处审核，假数据改raise，合法空返回加注释
- [ ] Task 8: 清理flow 18处fall-back（14 return None + 4 return []）
  - [ ] SubTask 8.1: 逐处审核，假数据改raise，合法空返回加注释
- [ ] Task 9: 清理gds_tools 15处fall-back（11 return None + 4 return []）
  - [ ] SubTask 9.1: 逐处审核，假数据改raise，合法空返回加注释
- [ ] Task 10: 清理其余模块return None/return []（place 3 + pdk_advanced 2 + gui 3 + nn 3 + multiphysics 2 + core 1 + drc 2 + yield 1）
  - [ ] SubTask 10.1: 逐处审核全部模块剩余fall-back

## 阶段4: P1 R05 TODO/FIXME清零（并行）

- [ ] Task 11: 清理circuit 10处TODO/FIXME
  - [ ] SubTask 11.1: 转issue或直接实现
- [ ] Task 12: 清理lumerical 5处TODO
  - [ ] SubTask 12.1: 转issue或直接实现
- [ ] Task 13: 清理verify_advanced 3处TODO
  - [ ] SubTask 13.1: 转issue或直接实现
- [ ] Task 14: 清理flow/gds_tools/nn/parasitic/yield剩余TODO（各1-2处）
  - [ ] SubTask 14.1: 逐处清理

## 阶段5: P1 超长文件拆分（并行）

- [ ] Task 15: 拆分place/analytical.py（1480L→多文件）
  - [ ] SubTask 15.1: 提取align.py（端口对齐）
  - [ ] SubTask 15.2: 提取legalize.py（合法化）
  - [ ] SubTask 15.3: 提取residual.py（残余修复）
  - [ ] SubTask 15.4: 提取metrics.py（HPWL/密度梯度）
- [x] Task 16: 拆分pdk/catalog.py（936L→catalog+devices+filters）✅ 76L/781L/128L, 43测试通过
- [x] Task 17: 拆分gui/interactive.py（824L→widgets+dialogs+menus）✅ 93L/594L/268L, 30测试通过
- [x] Task 18: 拆分gui/web_server.py（823L→routes+handlers+static）✅ 156L/353L/487L, 30测试通过
- [x] Task 19: 拆分quantum_advanced/distributed_ppo.py（808L→actor+critic+rollout+update）✅ 406L/229L/90L/295L, 42测试通过
- [x] Task 20: 拆分drc/engine.py（803L→rules+checks+reporter）✅ 465L/219L/233L, 51测试通过

## 阶段6: P2 超长函数拆分+高复杂度降低（并行，按模块分批）

- [ ] Task 21: 拆分place超长函数（_residual_pair_fix 293L + _align_d2_global 202L + _align_ports 144L + _find_nearest_legal_pos_1d 126L + _legalize 133L）
- [ ] Task 22: 拆分yield超长函数（6个超80行函数）
- [ ] Task 23: 拆分gds_tools超长函数（10个超80行函数）
- [ ] Task 24: 拆分flow/inverse/fdfd/fdtd/eme/bpm/orchestrator/sparam超长函数
- [ ] Task 25: 降低12个圈复杂度>15函数

## 阶段7: P2 测试覆盖率补充（并行）

- [ ] Task 26: 补充multiphysics测试（44文件仅35测试函数）
- [ ] Task 27: 补充nn测试（23文件仅48测试函数）
- [ ] Task 28: 补充gds_tools测试（35文件仅79测试函数）
- [ ] Task 29: 补充flow测试（24文件仅47测试函数）
- [ ] Task 30: 补充其余模块测试

## 阶段8: 验证与提交

- [ ] Task 31: 全量回归测试（448真实用例+200组合电路）
- [ ] Task 32: 质量门禁验证（0 except:pass / 0 TODO / 0 超800行文件）
- [ ] Task 33: 操作记录更新+代码提交

# Task Dependencies
- Task 1/2 可并行（修复bug+分类演示文件独立）
- Task 3/4/5 可并行（3个模块except:pass独立）
- Task 6-10 可并行（5批模块fall-back独立）
- Task 11-14 可并行（4批TODO独立）
- Task 15-20 可并行（6个文件拆分独立）
- Task 21-25 可并行（5批函数拆分独立，依赖Task 15-20完成）
- Task 26-30 可并行（5批测试补充独立）
- Task 31 依赖Task 1-25完成
- Task 32 依赖Task 31完成
- Task 33 依赖Task 32完成
