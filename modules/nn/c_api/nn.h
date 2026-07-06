/**
 * @file nn.h
 * @brief PoLaRIS polaris-nn 子模块 C ABI 接口声明
 *
 * 与 Python API（Linear/Conv2d/Attention/TransformerBlock/Adam +
 * BenchmarkEvaluator/DatasetGenerator/DataLoader）一一对应。
 * 类型定义见 ../_c_abi/polaris_types.h。
 *
 * 设计原则:
 * - 纯数据结构（POD），无 Python 对象泄漏
 * - caller 负责释放返回结构
 * - 错误码语义与 Python 异常一致：失败返回 POLARIS_ERR_INVALID
 *   （对应 Python 端 raise，R03 禁止 fall-back）
 * - 纯 NumPy 实现（R04: 不参与 GPU）
 *
 * 来源:
 * - PyTorch nn C++ frontend: https://pytorch.org/cppdocs/
 * - Vaswani et al. 2017 Transformer: https://arxiv.org/abs/1706.03762
 * - Kingma & Ba 2015 Adam: https://arxiv.org/abs/1412.6980
 * - TILOS MacroPlacement: https://github.com/TILOS-AI-Institute/MacroPlacement
 * - Apollo photonic benchmark: https://github.com/ASU-LOPE-Group/Apollo
 * - LiDAR ISPD'25 benchmark: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
 */
#ifndef POLARIS_NN_H
#define POLARIS_NN_H
#include "../_c_abi/polaris_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* polaris_nn_linear_forward: Linear 层前向 y = x @ W^T + b
 * @param x 输入张量 [N, in_features]
 * @param weight 权重 [out_features, in_features]
 * @param bias 偏置 [out_features]（可为 NULL）
 * @param out 输出张量 [N, out_features]（caller 负责 free）
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_nn.Linear(in_features, out_features).forward(x) 一致；
 * 复刻 torch.nn.Linear（https://pytorch.org/docs/stable/generated/torch.nn.Linear）。
 */
polaris_error_t polaris_nn_linear_forward(
    const polaris_tensor_t* x,
    const polaris_tensor_t* weight,
    const polaris_tensor_t* bias,
    polaris_tensor_t* out
);

/* polaris_nn_evaluate_benchmark: 综合 benchmark 评估
 * @param circuit 电路规格
 * @param placements 布局字典（{module_name: (x, y)} 编码为连续数组）
 * @param n_modules 模块数
 * @param out 输出评估结果（caller 负责 free）
 * @return POLARIS_OK 或错误码
 *
 * 与 Python polaris_nn.evaluate_benchmark(circuit, placements) 一致；
 * 计算 HPWL/重叠/利用率/拥塞度/插入损耗/DRV 等指标。
 */
polaris_error_t polaris_nn_evaluate_benchmark(
    const polaris_circuit_t* circuit,
    const double* placements, int32_t n_modules,
    polaris_benchmark_result_t* out
);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_NN_H */
