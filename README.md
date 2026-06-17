# PoLaRIS 光弈

> 光电子AI自动布局布线引擎（Photonic AI Place-and-Route Engine）

PoLaRIS（光弈）面向 SOI / SiN / InP / 薄膜铌酸锂（LNOI）等多工艺平台，提供器件资料库（PDK Lite）、AI 布局布线引擎、PPO 训练框架与版图评测的端到端流水线。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

或使用依赖清单：

```bash
pip install -r requirements-dev.txt
```

## 运行测试

```bash
pytest
```

## 代码质量

```bash
ruff check .
mypy polaris
```

## 项目结构

```
polaris/
  pdk/       # 器件模型资料库
  engine/    # 布局引擎
  router/    # 布线引擎
  trainer/   # AI 训练框架
  eval/      # 评测与可视化
tests/       # 测试
```
