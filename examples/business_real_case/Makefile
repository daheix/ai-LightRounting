# PoLaRIS 业务侧真实调用示例 Makefile
# 编译 main.c（C 业务侧调用 8 个子模块 C ABI + orchestrator）
#
# 用法:
#   make check_headers  # 仅验证头文件包含通过（无需链接子模块 C 实现）
#   make                # 编译（需链接子模块 C 实现 libpolaris_*.so）
#   make clean          # 清理编译产物
#
# R03 禁止 fall-back: 头文件包含/编译失败即报错退出，不静默兜底。

CC = gcc
CFLAGS = -Wall -Wextra -O2 -std=c11 \
    -I../../modules/_c_abi \
    -I../../modules/core/c_api \
    -I../../modules/pdk/c_api \
    -I../../modules/gdsio/c_api \
    -I../../modules/place/c_api \
    -I../../modules/route/c_api \
    -I../../modules/sparam/c_api \
    -I../../modules/pam4/c_api \
    -I../../modules/drc/c_api \
    -I../../modules/lvs/c_api \
    -I../../modules/inverse/c_api \
    -I../../modules/klm/c_api \
    -I../../modules/boson/c_api \
    -I../../modules/orchestrator/c_api

# 链接子模块 C 实现（当前 PoLaRIS 主路径为 Python，C ABI 头文件先行声明接口）
# 实际运行需构建 libpolaris_cabi.so（包含 8 个子模块 C 实现），此处给出链接参数。
LDFLAGS = -L../../modules/_c_abi -lpolaris_cabi

TARGET = polaris_business_case

all: $(TARGET)

$(TARGET): main.c
	$(CC) $(CFLAGS) -o $(TARGET) main.c $(LDFLAGS)

# 仅验证头文件包含通过（-fsyntax-only 不生成目标文件，不链接库）
# 适用于无 C 实现库时验证 API 调用方式正确性
check_headers:
	$(CC) $(CFLAGS) -fsyntax-only main.c

clean:
	rm -f $(TARGET)

.PHONY: all check_headers clean
