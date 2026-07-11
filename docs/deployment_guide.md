# PoLaRIS 部署指南

> 版本 v5.0.0 · 2026-07 · 安装、配置、部署与性能调优
> 数据来源：`pyproject.toml` / `modules/gui/src/polaris_gui/web_server.py` / `R04-不参与GPU.md` / 代码 Grep 实测
> 学术诚信（R02/R03）：所有依赖版本、端口号、环境变量均从项目实际代码提取，禁止编造

---

## 目录

1. [系统要求](#1-系统要求)
2. [安装方式](#2-安装方式)
3. [核心依赖](#3-核心依赖)
4. [Web GUI 部署](#4-web-gui-部署)
5. [Docker 部署](#5-docker-部署)
6. [JAX CPU 配置](#6-jax-cpu-配置)
7. [性能调优](#7-性能调优)
8. [环境变量参考](#8-环境变量参考)
9. [故障排查](#9-故障排查)
10. [卸载](#10-卸载)

---

## 1. 系统要求

| 项目 | 要求 | 来源 |
|------|------|------|
| 操作系统 | Linux（推荐 Ubuntu 22.04）/ macOS / Windows | `getting_started.md` §1.1 |
| Python | ≥ 3.9（推荐 3.11） | `pyproject.toml` `requires-python = ">=3.9"` |
| 解释器分类 | CPython 3.9 / 3.10 / 3.11 / 3.12 | `pyproject.toml` classifiers |
| CPU | 任意 x86_64 / ARM64 | 纯 CPU，无需 GPU（R04） |
| GPU | 🚫不参与（R04 战略决策，不可撤销） | `.trae/rules/R04-不参与GPU.md` |
| 内存 | 最低 4GB，推荐 8GB+（大电路仿真） | 仿真矩阵规模 |
| 磁盘 | ≥ 500MB（代码 + 依赖） | 实测 |

### R04 战略说明（不可撤销）

PoLaRIS 项目战略决策（2026-06-25 项目所有者指示）：**不参与 GPU 计算**。

- 禁止 CuPy / CUDA / ROCm / AppleMetal 等所有 GPU 后端
- 禁止 FP16 / BF16 半精度、多卡 GPU 分布式
- 纯 NumPy / SciPy / JAX(CPU) 实现
- GPU 相关功能点标记 `🚫不参与`，不计入覆盖率

来源：`.trae/rules/R04-不参与GPU.md`

---

## 2. 安装方式

> **重要**：PyPI 包名为 `polaris-pnr`（见 `pyproject.toml` `name = "polaris-pnr"`），而非 `polaris`。命令行入口为 `polaris`（见 `[project.scripts] polaris = "polaris.pipeline:main"`）。

### 2.1 开发模式安装（推荐开发者）

```bash
git clone https://github.com/daheix/ai-LightRounting.git
cd ai-LightRounting
pip install -e ".[dev]"
```

开发模式（`-e`）使修改源码后立即生效，无需重装。
仓库地址来源：`pyproject.toml` `[project.urls] Repository`。

### 2.2 用户模式安装

```bash
pip install polaris-pnr
```

### 2.3 可选依赖

以下为 `pyproject.toml` `[project.optional-dependencies]` 真实声明：

```bash
pip install -e ".[gdsfactory]"   # gdsfactory PDK 集成（需 Python 3.10-3.13）
pip install -e ".[sipann]"       # SiPANN 模型库（需 Python 3.10-3.13）
pip install -e ".[dev]"          # pytest / ruff / mypy 开发工具链
```

| 可选组 | 依赖 | 版本要求 | Python 兼容性 | 说明 |
|--------|------|----------|---------------|------|
| `gdsfactory` | gdsfactory | `>=8.0` | 3.10–3.13 | PDK 集成（上游 pydantic 锁定，3.14 不可用） |
| `sipann` | SiPANN | 未锁定 | 3.10–3.13 | 模型库（依赖 tensorflow，3.14 不可用） |
| `dev` | pytest / ruff / mypy | 未锁定 | 全部 | 开发工具链 |

> 来源：`pyproject.toml` 行 41–55 的注释与版本约束。

### 2.4 逆向设计模块的 JAX 依赖（重要）

**实测发现**：JAX 用于逆向设计（`polaris_inverse`）、伴随优化（`polaris_optimizer`）、FDTD 求解器（`polaris_fdtd`），但 **未声明在 `pyproject.toml` 核心依赖中**。使用以下功能时需单独安装：

```bash
pip install jax jaxlib
```

涉及文件（均设置 `JAX_PLATFORMS=cpu` 强制 CPU 后端）：
- `modules/optimizer/src/polaris_optimizer/density_adjoint.py`
- `modules/inverse/src/polaris_inverse/level_set.py` / `topology_opt.py` / `adjoint.py` / `fdtd_jax.py`
- `modules/fdtd/src/polaris_fdtd/solver.py` / `mmi.py` / `waveguide.py`

> 仅使用布局布线、DRC/LVS、电路仿真等核心功能时无需 JAX。

### 2.5 验证安装

```bash
# 验证包导入与版本
python -c "import polaris; print(polaris.__version__)"

# 验证 CLI 入口
polaris --help

# 收集测试验证完整性（不执行）
pytest --co -q
```

---

## 3. 核心依赖

以下为 `pyproject.toml` `[project] dependencies` 真实声明的核心依赖（版本未锁定，安装时拉取最新兼容版）：

| 依赖 | 用途 | 说明 |
|------|------|------|
| `numpy` | 数值计算基础 | 矩阵运算、向量化（sliding_window_view 等） |
| `scipy` | 科学计算 | 稀疏矩阵（CSR）、`sparse.linalg.eigsh`（FDE 本征求解） |
| `networkx` | 图算法 | 布线图建模、A*/JPS 路径搜索 |
| `torch` | 深度学习 | GNN/CNN/PPO 强化学习布局 |
| `gymnasium` | 强化学习环境 | PPO 训练环境接口 |
| `matplotlib` | 可视化 | 仿真结果绘图、报告渲染 |
| `pyyaml` | 配置解析 | YAML 网表/配置读取 |
| `klayout` | 版图处理 | DRC/LVS 规则检查、GDS 读写 |
| `simphony` | 光子电路仿真 | S 参数模型参考实现 |
| `sax` | S 参数级联 | 子网络增长算法、网表风格 |
| `gdstk` | GDS 文件 | GDSII/OASIS 几何读写 |
| `shapely` | 几何运算 | 版图布尔运算、DRC 空间检查 |

> 学术依据：Simphony https://simphonyphotonics.readthedocs.io/ ；SAX https://flaport.github.io/sax/

---

## 4. Web GUI 部署

### 4.1 启动 Web Server

Web GUI 使用 **Python 内置 `http.server.ThreadingHTTPServer`** 实现（非 Flask/FastAPI），无需额外 Web 框架依赖。

来源：`modules/gui/src/polaris_gui/web_server.py` 行 44、101–103。

**服务器参数（从代码提取真实默认值）：**

| 参数 | 默认值 | 来源 |
|------|--------|------|
| 服务器类型 | `http.server.ThreadingHTTPServer` | `web_server.py:44,101` |
| 监听地址 host | `0.0.0.0` | `web_server.py:82,121` |
| 监听端口 port | `8000` | `web_server.py:82,121` |
| 阻塞模式 | `blocking=True`（默认阻塞） | `web_server.py:88` |

> 线程安全说明：`ThreadingHTTPServer` 每请求一线程（R05 Bug 修复 v4.0-WEB-THREAD），配合 `_global_lock` + `_showcase_lock` 保证并发安全。原 `HTTPServer` 单线程会导致 `/api/run` 同步运行流水线时 UI 冻结。

**启动方式一：模块直接运行**

```bash
python -m polaris_gui.web_server
# 等价于 run_server()，监听 0.0.0.0:8000
```

**启动方式二：Python 调用**

```python
from polaris_gui import run_server

run_server(host="0.0.0.0", port=8000)  # 阻塞运行
```

**启动方式三：自定义端口**

```python
from polaris_gui import WebServer

server = WebServer(host="0.0.0.0", port=9000)
server.start(blocking=True)
```

### 4.2 访问 Web GUI

浏览器访问：`http://localhost:8000`（默认端口）。

**Web GUI 提供两种模式：**

| 模式 | 说明 | API |
|------|------|-----|
| Showcase 模式 | 端到端 Demo 全流程演示（预设电路→布局布线→DRC→GDS 导出） | `POST /api/showcase/run` |
| 编辑器模式 | R19 交互式版图编辑（点/线/多边形/贝塞尔/弧/端口等对象） | `/api/editor/*` 系列端点 |

**REST API 端点（从 `web_server.py` docstring 提取）：**

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/presets` | 列出预设电路 |
| POST | `/api/run` | 运行布局布线流水线 |
| POST | `/api/showcase/run` | 启动端到端 Demo Showcase |
| GET | `/api/showcase/report/{run_id}` | 查询 Showcase 汇总报告 |
| GET | `/api/showcase/stages/{run_id}/{stage_id}` | 查询 Showcase 单阶段结果 |
| POST | `/api/jobs` | 提交作业（Recipe JSON 作为 body） |
| GET | `/api/jobs` | 列出所有作业（可选 `?status=` 过滤） |
| GET | `/api/jobs/{job_id}` | 查询作业详情 |
| GET | `/api/jobs/{job_id}/status` | 查询作业状态与进度 |
| POST | `/api/jobs/{job_id}/cancel` | 取消作业 |
| GET | `/api/jobs/{job_id}/stages/{stage_id}` | 查询阶段输出 |
| GET | `/api/jobs/{job_id}/report` | 查询作业汇总报告 |

**健康检查自测：**

```bash
curl http://localhost:8000/api/health
# 预期返回 200 + 健康 JSON
```

### 4.3 生产部署建议

`ThreadingHTTPServer` 是 Python 标准库轻量服务器，**不建议直接暴露公网**。生产环境建议前置反向代理：

**nginx 反向代理示例：**

```nginx
server {
    listen 80;
    server_name polaris.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;  # 长时间流水线运行
    }
}
```

**systemd 进程管理示例：**

```ini
# /etc/systemd/system/polaris-web.service
[Unit]
Description=PoLaRIS Web GUI
After=network.target

[Service]
Type=simple
User=polaris
WorkingDirectory=/opt/polaris
Environment=JAX_PLATFORMS=cpu
ExecStart=/opt/polaris/.venv/bin/python -m polaris_gui.web_server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now polaris-web
sudo systemctl status polaris-web
```

---

## 5. Docker 部署

> **实测**：项目根目录**无 Dockerfile**（Grep `Dockerfile|docker` 仅命中 `real_board/skywater130/` 等第三方参考板，非 PoLaRIS 主项目）。以下为**示例模板**，标注"示例"。

### 5.1 Dockerfile（示例）

```dockerfile
# 示例：PoLaRIS Web GUI 容器镜像
FROM python:3.11-slim

# 系统依赖（klayout/gdstk 需编译工具链）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用层缓存）
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY 3dtool/ ./3dtool/
COPY modules/ ./modules/

# 安装核心包
RUN pip install --no-cache-dir -e ".[dev]"

# R04：强制 JAX CPU 后端
ENV JAX_PLATFORMS=cpu
ENV JAX_ENABLE_X64=true

EXPOSE 8000

# 启动 Web GUI
CMD ["python", "-m", "polaris_gui.web_server"]
```

### 5.2 docker-compose.yml（示例）

```yaml
# 示例：Web GUI + 持久化输出目录
version: "3.9"

services:
  polaris-web:
    build: .
    container_name: polaris-web
    ports:
      - "8000:8000"
    environment:
      - JAX_PLATFORMS=cpu
      - JAX_ENABLE_X64=true
      - OMP_NUM_THREADS=4
    volumes:
      # 持久化仿真输出与 GDS 导出
      - polaris-output:/app/output
    restart: unless-stopped

volumes:
  polaris-output:
```

### 5.3 镜像构建与运行

```bash
# 构建镜像
docker build -t polaris-pnr:5.0.0 .

# 运行容器
docker run -d \
  --name polaris-web \
  -p 8000:8000 \
  -e JAX_PLATFORMS=cpu \
  -v $(pwd)/output:/app/output \
  polaris-pnr:5.0.0

# 健康检查
curl http://localhost:8000/api/health

# 查看日志
docker logs -f polaris-web
```

---

## 6. JAX CPU 配置

### 6.1 R04 强制 CPU 后端

PoLaRIS 逆向设计/FDTD/伴随优化模块使用 JAX，但 **R04 战略禁止 GPU**。代码中通过以下方式强制 CPU：

```python
# 必须在 import jax 前设置
os.environ.setdefault("JAX_PLATFORMS", "cpu")
# ...
import jax
jax.config.update("jax_platforms", "cpu")   # 强制 CPU
jax.config.update("jax_enable_x64", True)    # 双精度
```

来源：`modules/optimizer/src/polaris_optimizer/density_adjoint.py:69,75-76`；`modules/fdtd/src/polaris_fdtd/solver.py:66`。

### 6.2 环境变量设置

在启动脚本或 shell 中预设（代码使用 `setdefault`，环境变量优先级更高）：

```bash
# 强制 CPU，禁用 GPU 探测（消除 GPU 警告）
export JAX_PLATFORMS=cpu

# 启用双精度（FDE/FDTD 数值精度要求）
export JAX_ENABLE_X64=true
```

### 6.3 XLA 编译优化

JAX 使用 XLA 编译器，首次调用会触发编译（耗时），后续调用命中缓存。生产环境建议：

- 预热：启动后执行一次小规模仿真触发 JIT 编译
- 持久化缓存目录（如需）：参考 JAX 官方文档配置

> 文献：JAX 文档 https://jax.readthedocs.io/ ；XLA https://www.tensorflow.org/xla

---

## 7. 性能调优

### 7.1 纯 CPU 优化策略（R04 约束下）

R04 禁止 GPU，所有性能优化在 CPU 域内进行：

| 策略 | 配置 | 效果 |
|------|------|------|
| NumPy 向量化 | `sliding_window_view` | 9.83x 加速（R871-R885 基准） |
| LRU 缓存 | 器件模型缓存 | 最高 73x 加速 |
| 稀疏矩阵 | CSR 连通性 | 内存大幅压缩 |
| 内存映射 | `np.memmap` 大数组 | 避免内存峰值 |

> 来源：`docs/getting_started.md` §6.2；`src/polaris/sim/perf_tuning_r851.py`。

### 7.2 多线程配置

NumPy/OpenBLAS/MKL 线程数控制（**标准 NumPy 环境变量，非 PoLaRIS 自定义**）：

```bash
# 物理核数（避免超线程争用）
export OMP_NUM_THREADS=$(nproc --all)
export MKL_NUM_THREADS=$(nproc --all)
export OPENBLAS_NUM_THREADS=$(nproc --all)

# 或限制线程数（留核给 Web Server）
export OMP_NUM_THREADS=4
```

> 文献：NumPy 线程配置 https://numpy.org/doc/stable/user/threading.html

### 7.3 大电路仿真内存优化

- 使用 `generator` 流式处理替代全量数组（`memory_optimization_r886.py`）
- 使用 `np.memmap` 处理超大规模矩阵
- 分块（chunk）处理波长扫描
- 来源：`src/polaris/sim/memory_optimization_r886.py`

### 7.4 JAX JIT 编译缓存

逆向设计迭代中，JAX `jax.grad` + `jax.jit` 编译结果可复用：

- 首次迭代触发 XLA 编译（慢）
- 后续迭代命中编译缓存（快）
- 固定问题形状（网格尺寸）以最大化缓存命中

### 7.5 布局布线并行化

- 布线引擎（A*/JPS）天然可按 net 并行
- 多核 CPU 下可通过 `multiprocessing` 按 net 分发
- Bundle 布线批量处理通道

---

## 8. 环境变量参考

| 变量名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `JAX_PLATFORMS` | `cpu` | 强制 JAX 使用 CPU 后端（R04），禁止 GPU | 代码 `os.environ.setdefault` 多处 |
| `JAX_ENABLE_X64` | `true`（代码内 config） | 启用双精度浮点（FDE/FDTD 数值精度） | `density_adjoint.py:76` |
| `OMP_NUM_THREADS` | auto | OpenMP 线程数（NumPy/OpenBLAS） | 标准 NumPy 变量 |
| `MKL_NUM_THREADS` | auto | Intel MKL 线程数 | 标准 MKL 变量 |
| `OPENBLAS_NUM_THREADS` | auto | OpenBLAS 线程数 | 标准 OpenBLAS 变量 |

> **诚信声明**：`POLARIS_LOG_LEVEL` 等自定义变量经 Grep 全代码库未发现，故不列入。上表仅含代码中真实使用或标准库通用的环境变量。

---

## 9. 故障排查

### 9.1 安装问题

| 症状 | 原因 | 解决 |
|------|------|------|
| `pip install polaris` 找不到包 | 包名错误 | 使用 `pip install polaris-pnr`（`pyproject.toml` name） |
| `ModuleNotFoundError: jax` | 逆向设计模块未装 JAX | `pip install jax jaxlib`（见 §2.4） |
| gdsfactory 安装失败 | Python 版本不兼容 | 仅 Python 3.10–3.13 可用（pydantic 锁定） |
| SiPANN 安装失败 | 依赖 tensorflow 无 3.14 支持 | 仅 Python 3.10–3.13 可用 |
| klayout/gdstk 编译失败 | 缺编译工具链 | `apt install build-essential gcc g++` |

### 9.2 Web GUI 无法访问

| 症状 | 原因 | 解决 |
|------|------|------|
| 浏览器无法打开 localhost:8000 | 服务未启动 | `curl http://localhost:8000/api/health` 验证 |
| 端口被占用 | 8000 端口冲突 | 自定义端口 `WebServer(port=9000)` |
| 防火墙拦截 | iptables/ufw 规则 | `ufw allow 8000` 或用 nginx 反代 |
| `/api/run` 卡住 UI | 旧版单线程 HTTPServer | 升级到 `ThreadingHTTPServer` 版本（R05 已修） |
| 远程访问失败 | 监听 127.0.0.1 | 默认 `0.0.0.0` 已监听全部接口，检查防火墙 |

### 9.3 JAX GPU 警告

| 症状 | 原因 | 解决 |
|------|------|------|
| `No GPU/TPU found` 警告 | JAX 探测 GPU 失败 | `export JAX_PLATFORMS=cpu` 消除警告（R04） |
| 意外使用 GPU | 环境变量未设 | 代码已 `setdefault("JAX_PLATFORMS","cpu")`，环境变量优先级更高 |

### 9.4 内存不足

| 症状 | 原因 | 解决 |
|------|------|------|
| `MemoryError` / OOM | 电路规模过大 | 减小网格/波长点数；使用 `memmap` 流式处理 |
| FDTD 网格爆炸 | 三维网格过大 | 降低分辨率或缩小计算窗口 |

---

## 10. 卸载

```bash
# 卸载核心包
pip uninstall polaris-pnr

# 如安装了可选依赖
pip uninstall gdsfactory SiPANN

# 如安装了 JAX（逆向设计用）
pip uninstall jax jaxlib
```

开发模式下还需移除 editable 安装标记：

```bash
# 移除 .pth 文件
pip uninstall polaris-pnr
# 删除源码目录
rm -rf ai-LightRounting/
```

---

## 学术诚信声明（R02/R03）

- 所有依赖名称与版本约束：提取自 `pyproject.toml`（行 26–55），未编造
- Web 服务器类型、host、port：提取自 `modules/gui/src/polaris_gui/web_server.py`（行 44、82、121），未编造
- JAX 配置：提取自 `modules/optimizer/src/polaris_optimizer/density_adjoint.py` 等代码 Grep 实测
- R04 GPU 战略：提取自 `.trae/rules/R04-不参与GPU.md`
- Docker 部分：项目根目录无 Dockerfile（已 Grep 验证），提供示例模板并明确标注"示例"
- 环境变量表：仅列代码中真实使用或标准库通用变量，未列未经验证的 `POLARIS_LOG_LEVEL`
- 仓库地址：`https://github.com/daheix/ai-LightRounting`（`pyproject.toml` `[project.urls]`）
- 版本号：v5.0.0（`pyproject.toml` `version = "5.0.0"`）

## 文献来源

1. Python http.server / ThreadingHTTPServer
   https://docs.python.org/3/library/http.server.html
2. socketserver.ThreadingMixIn
   https://docs.python.org/3/library/socketserver.html#socketserver.ThreadingMixIn
3. KLayout DRC 文档
   https://www.klayout.org/doc-qt5/manual/drc_runsets.html
4. Simphony 仿真器
   https://simphonyphotonics.readthedocs.io/
5. SAX 仿真器
   https://flaport.github.io/sax/
6. JAX 文档
   https://jax.readthedocs.io/
7. NumPy 线程配置
   https://numpy.org/doc/stable/user/threading.html
8. NumPy sliding_window_view
   https://numpy.org/doc/stable/reference/generated/numpy.lib.stride_tricks.sliding_window_view.html
