# publish/ — 产品发布制品

本目录存放 PoLaRIS 产品发布给第三方用的制品。

## 目录结构

```
publish/
├── wheels/      # 构建 wheel 包
├── docs/        # 发布文档（用户手册/API 文档）
└── examples/    # 使用示例
```

## 发布流程

```bash
# 1. 构建 wheel
python -m build --wheel --outdir publish/wheels/

# 2. 生成文档
# (TODO: 配置 sphinx/mkdocs)

# 3. 打包示例
cp -r examples/* publish/examples/
```

## 版本管理

遵循 SemVer 语义化版本：`MAJOR.MINOR.PATCH`
- MAJOR: 不兼容的 API 修改
- MINOR: 向下兼容的功能新增
- PATCH: 向下兼容的 Bug 修复

当前版本: 0.1.0 (Pre-Alpha)
