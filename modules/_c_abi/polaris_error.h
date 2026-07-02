/**
 * @file polaris_error.h
 * @brief PoLaRIS C ABI 统一错误处理
 *
 * 所有 C ABI 函数返回 polaris_error_t，错误信息通过 polaris_error_message 获取。
 * 设计原则：失败即返回非0错误码（R03 禁止 fall-back），不静默吞错。
 */
#ifndef POLARIS_ERROR_H
#define POLARIS_ERROR_H

#include "polaris_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief 获取错误码对应的错误信息字符串
 * @param err 错误码
 * @return 静态字符串指针（无需 free），如 "POLARIS_OK: 成功"
 */
const char* polaris_error_message(polaris_error_t err);

/**
 * @brief 获取最后一次错误的详细信息（线程局部）
 * @return 错误详情字符串（无需 free），无错误时返回 NULL
 */
const char* polaris_last_error(void);

/**
 * @brief 设置最后一次错误详情（子模块内部用）
 * @param msg 错误详情（会被复制，caller 可立即 free 原字符串）
 */
void polaris_set_last_error(const char* msg);

#ifdef __cplusplus
}
#endif

#endif /* POLARIS_ERROR_H */
