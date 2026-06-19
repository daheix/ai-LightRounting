# wheels/ — 构建 wheel 包

存放 `python -m build` 生成的 wheel 制品。

```bash
# 构建命令
python -m build --wheel --outdir publish/wheels/

# 安装发布包
pip install publish/wheels/polaris_pnr-0.1.0-py3-none-any.whl
```
