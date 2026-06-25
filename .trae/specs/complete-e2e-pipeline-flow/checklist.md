# Checklist

## grid_placement 修复
- [ ] grid_placement 对 Ariane benchmark 产生零边界违规
- [ ] grid_placement 对小画布大模块场景自适应扩大画布
- [ ] test_evaluate_benchmark_passed_no_overlap 通过

## stage3 torch 可选
- [ ] stage3_ai_placement.py 无 torch 时不报 ImportError
- [ ] stage3 无 torch 时使用纯 numpy PPO 后端
- [ ] test_e2e_showcase.py 全部通过

## 全流程验证
- [ ] test_web_ui.py 8 passed
- [ ] test_tilos_benchmark.py 46 passed
- [ ] test_e2e_showcase.py 全部通过
