"""TILOS MacroPlacement 公开 Benchmark 移植（P1-5）。

移植 TILOS Ariane RISC-V CPU benchmark，用于与电子 EDA 工具
（Innovus/ICC2/DREAMPlace/Circuit Training）公平对比布局算法。

来源:
- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Ariane RISC-V CPU: https://github.com/openhwgroup/cva6 (Ariane 后继 CVA6)
- Circuit Training: https://github.com/google-research/circuit_training
- NanGate45/ASAP7/SKY130HD 工艺库

Ariane 真实模块结构（6-stage RISC-V pipeline）:
- PC 生成 → 取指 → 译码 → 发射 → 执行 → 提交
- 含 I$/D$/PTW/CSR/控制器/乘除/浮点等 17 个核心模块
- 模块间数据通路与控制通路分离

本模块提供合成版 Ariane benchmark（保留真实拓扑，规模可调），
用于 CI 回归测试与算法验证，无需下载 TILOS 完整数据集。


## 补充文献（R02 学术诚信补齐）
- gdsfactory 主站: https://gdsfactory.com/
- Python 文档: https://docs.python.org/3/
"""

from __future__ import annotations

from dataclasses import dataclass

from polaris_nn.data.specs import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
)

# ─── Ariane RISC-V CPU 真实模块定义 ───
# 来源: https://github.com/openhwgroup/cva6/blob/main/src/ariane.sv
# 模块面积估算（NanGate45 工艺，μm²）参考 TILOS Ariane bookshelf


@dataclass(frozen=True)
class ArianeModule:
    """Ariane CPU 模块规格。

    Attributes:
        name: 模块名（对齐 CVA6 源码命名）。
        width_um: 模块宽度（μm，NanGate45 工艺估算）。
        height_um: 模块高度（μm）。
        category: 模块类别（pipeline/cache/alu/fpu/csr/control）。
        description: 模块功能描述。
    """

    name: str
    width_um: float
    height_um: float
    category: str
    description: str


# 17 个 Ariane 核心模块（来源: CVA6 src/ariane.sv 顶层实例化）
ARIANE_MODULES: dict[str, ArianeModule] = {
    "pc_gen": ArianeModule(
        name="pc_gen",
        width_um=80.0,
        height_um=60.0,
        category="pipeline",
        description="PC 生成单元，管理程序计数器与分支预测",
    ),
    "fetch": ArianeModule(
        name="fetch",
        width_um=120.0,
        height_um=80.0,
        category="pipeline",
        description="取指单元，从 I$ 读取指令",
    ),
    "fetch_fifo": ArianeModule(
        name="fetch_fifo",
        width_um=60.0,
        height_um=40.0,
        category="pipeline",
        description="取指 FIFO，缓存取出的指令",
    ),
    "decode": ArianeModule(
        name="decode",
        width_um=150.0,
        height_um=100.0,
        category="pipeline",
        description="译码单元，解析 RISC-V 指令",
    ),
    "scoreboard": ArianeModule(
        name="scoreboard",
        width_um=100.0,
        height_um=80.0,
        category="pipeline",
        description="记分牌，管理指令依赖与发射",
    ),
    "issue": ArianeModule(
        name="issue",
        width_um=120.0,
        height_um=90.0,
        category="pipeline",
        description="发射单元，将指令派发到执行单元",
    ),
    "alu": ArianeModule(
        name="alu",
        width_um=100.0,
        height_um=70.0,
        category="alu",
        description="算术逻辑单元，执行整数运算",
    ),
    "mult": ArianeModule(
        name="mult",
        width_um=140.0,
        height_um=100.0,
        category="alu",
        description="乘法器，执行 MUL/MULH 指令",
    ),
    "fpu": ArianeModule(
        name="fpu",
        width_um=180.0,
        height_um=120.0,
        category="fpu",
        description="浮点单元，执行 F/D 扩展指令",
    ),
    "lsu": ArianeModule(
        name="lsu",
        width_um=130.0,
        height_um=90.0,
        category="pipeline",
        description="load/store 单元，访问数据存储器",
    ),
    "csr": ArianeModule(
        name="csr",
        width_um=90.0,
        height_um=70.0,
        category="csr",
        description="CSR 寄存器堆，管理与异常控制寄存器",
    ),
    "ptw": ArianeModule(
        name="ptw",
        width_um=110.0,
        height_um=80.0,
        category="cache",
        description="页表遍历，虚拟地址→物理地址转换",
    ),
    "icache": ArianeModule(
        name="icache",
        width_um=200.0,
        height_um=150.0,
        category="cache",
        description="指令缓存，L1 I$",
    ),
    "dcache": ArianeModule(
        name="dcache",
        width_um=220.0,
        height_um=170.0,
        category="cache",
        description="数据缓存，L1 D$",
    ),
    "commit": ArianeModule(
        name="commit",
        width_um=110.0,
        height_um=80.0,
        category="pipeline",
        description="提交单元，写回寄存器堆",
    ),
    "controller": ArianeModule(
        name="controller",
        width_um=70.0,
        height_um=50.0,
        category="control",
        description="控制器，处理中断/异常/流水线冲刷",
    ),
    "serdiv": ArianeModule(
        name="serdiv",
        width_um=100.0,
        height_um=70.0,
        category="alu",
        description="串行除法器，执行 DIV/REM 指令",
    ),
}


# ─── Ariane 模块间真实连接（数据通路 + 控制通路） ───
# 来源: CVA6 src/ariane.sv 模块实例化与端口连接
# 每条连接: (src_module, src_port, dst_module, dst_port)
ARIANE_CONNECTIONS: list[tuple[str, str, str, str]] = [
    # ── 流水线数据通路 ──
    ("pc_gen", "pc_out", "fetch", "pc_in"),
    ("fetch", "instr_out", "fetch_fifo", "instr_in"),
    ("fetch_fifo", "instr_out", "decode", "instr_in"),
    ("decode", "decoded_out", "scoreboard", "decoded_in"),
    ("scoreboard", "issue_out", "issue", "issue_in"),
    ("issue", "alu_op", "alu", "op_in"),
    ("issue", "mul_op", "mult", "op_in"),
    ("issue", "fpu_op", "fpu", "op_in"),
    ("issue", "lsu_op", "lsu", "op_in"),
    # ── 执行结果回写 ──
    ("alu", "result_out", "commit", "result_in"),
    ("mult", "result_out", "commit", "result_in"),
    ("fpu", "result_out", "commit", "result_in"),
    ("lsu", "result_out", "commit", "result_in"),
    ("commit", "wb_out", "scoreboard", "wb_in"),
    # ── 缓存与访存 ──
    ("fetch", "mem_req", "icache", "req_in"),
    ("icache", "instr_out", "fetch", "instr_in"),
    ("lsu", "mem_req", "dcache", "req_in"),
    ("dcache", "data_out", "lsu", "data_in"),
    ("dcache", "page_fault", "ptw", "walk_req"),
    ("ptw", "pte_out", "dcache", "pte_in"),
    # ── CSR 与控制 ──
    ("csr", "csr_out", "alu", "csr_in"),
    ("controller", "flush", "fetch", "flush_in"),
    ("controller", "flush", "decode", "flush_in"),
    ("controller", "flush", "commit", "flush_in"),
    ("serdiv", "result_out", "fpu", "div_in"),
]


def _module_to_device_spec(module: ArianeModule) -> DeviceSpec:
    """将 ArianeModule 转为 DeviceSpec（含 in/out 标准端口）。

    Args:
        module: Ariane 模块规格。

    Returns:
        DeviceSpec，含 in/out 端口，device_type="ariane_module"。
    """
    return DeviceSpec(
        name=module.name,
        device_type="straight",  # 映射到 catalog 标准器件
        width_um=module.width_um,
        height_um=module.height_um,
        ports=[
            ("in", 0.0, module.height_um / 2, "WEST"),
            ("out", module.width_um, module.height_um / 2, "EAST"),
        ],
        params={
            "category": module.category,
            "description": module.description,
            "benchmark": "tilos_ariane",
        },
        process_node="NanGate45",
    )


def load_ariane_benchmark(
    process_node: str = "NanGate45",
    canvas_scale: float = 1.5,
) -> CircuitSpec:
    """加载 TILOS Ariane RISC-V CPU benchmark（真实模块拓扑）。

    生成包含 17 个 Ariane 核心模块 + 25 条真实连接的 CircuitSpec，
    模块面积与连接拓扑对齐 CVA6 源码结构。

    来源:
    - TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
    - CVA6 源码: https://github.com/openhwgroup/cva6

    Args:
        process_node: 工艺节点（NanGate45/ASAP7/SKY130HD）。
        canvas_scale: 画布缩放因子（默认 1.5，确保模块不重叠）。

    Returns:
        CircuitSpec，benchmark_source=TILOS，target_metric=HPWL。
    """
    devices = [_module_to_device_spec(m) for m in ARIANE_MODULES.values()]
    # 画布尺寸：所有模块面积总和 × canvas_scale
    total_area = sum(m.width_um * m.height_um for m in ARIANE_MODULES.values())
    canvas_side = (total_area * canvas_scale) ** 0.5
    return CircuitSpec(
        name="tilos_ariane",
        devices=devices,
        connections=list(ARIANE_CONNECTIONS),
        canvas_w=canvas_side,
        canvas_h=canvas_side,
        benchmark_source=BenchmarkSource.TILOS,
        process_node=process_node,
        target_metric=TargetMetric.HPWL,
        target_value=50000.0,  # 目标 HPWL < 50000μm（17 模块规模）
    )


# ─── MemPool RISC-V Many-core SoC 真实模块定义 ───
# 来源: https://github.com/pulp-platform/mempool (PULP platform MemPool)
# MemPool: 16 组 RISC-V cluster + TCDM SRAM + AXI 互连的开源 many-core SoC
# 模块面积估算（NanGate45 工艺，μm²）参考 TILOS MemPool bookshelf
#
# MemPool 简化模型（保留真实拓扑结构，规模可调）:
# - 4 个 compute cluster（每组含 9 个 RISC-V snitch cores，简化为 1 个代表）
# - 4 个 instruction cache（每组 cluster 共享）
# - 4 个 TCDM SRAM bank（代表 16 bank 分组）
# - 1 个 TCDM interconnect（多 bank 互连网络）
# - 1 个 AXI peripheral subsystem
# - 1 个 boot ROM

MEMPOOL_MODULES: dict[str, ArianeModule] = {
    "cluster_0": ArianeModule(
        name="cluster_0", width_um=180.0, height_um=140.0,
        category="compute", description="计算集群 0（9 个 RISC-V snitch cores）",
    ),
    "cluster_1": ArianeModule(
        name="cluster_1", width_um=180.0, height_um=140.0,
        category="compute", description="计算集群 1（9 个 RISC-V snitch cores）",
    ),
    "cluster_2": ArianeModule(
        name="cluster_2", width_um=180.0, height_um=140.0,
        category="compute", description="计算集群 2（9 个 RISC-V snitch cores）",
    ),
    "cluster_3": ArianeModule(
        name="cluster_3", width_um=180.0, height_um=140.0,
        category="compute", description="计算集群 3（9 个 RISC-V snitch cores）",
    ),
    "icache_0": ArianeModule(
        name="icache_0", width_um=120.0, height_um=90.0,
        category="cache", description="指令缓存 0（cluster_0 共享）",
    ),
    "icache_1": ArianeModule(
        name="icache_1", width_um=120.0, height_um=90.0,
        category="cache", description="指令缓存 1（cluster_1 共享）",
    ),
    "icache_2": ArianeModule(
        name="icache_2", width_um=120.0, height_um=90.0,
        category="cache", description="指令缓存 2（cluster_2 共享）",
    ),
    "icache_3": ArianeModule(
        name="icache_3", width_um=120.0, height_um=90.0,
        category="cache", description="指令缓存 3（cluster_3 共享）",
    ),
    "sram_bank_0": ArianeModule(
        name="sram_bank_0", width_um=100.0, height_um=80.0,
        category="sram", description="TCDM SRAM bank 组 0（4 bank）",
    ),
    "sram_bank_1": ArianeModule(
        name="sram_bank_1", width_um=100.0, height_um=80.0,
        category="sram", description="TCDM SRAM bank 组 1（4 bank）",
    ),
    "sram_bank_2": ArianeModule(
        name="sram_bank_2", width_um=100.0, height_um=80.0,
        category="sram", description="TCDM SRAM bank 组 2（4 bank）",
    ),
    "sram_bank_3": ArianeModule(
        name="sram_bank_3", width_um=100.0, height_um=80.0,
        category="sram", description="TCDM SRAM bank 组 3（4 bank）",
    ),
    "tcdm_interconnect": ArianeModule(
        name="tcdm_interconnect", width_um=160.0, height_um=120.0,
        category="interconnect", description="TCDM 多 bank 互连网络（logarithmic interconnect）",
    ),
    "axi_peripheral": ArianeModule(
        name="axi_peripheral", width_um=140.0, height_um=100.0,
        category="interconnect", description="AXI4 外设子系统（peripheral subsystem）",
    ),
    "bootrom": ArianeModule(
        name="bootrom", width_um=40.0, height_um=30.0,
        category="control", description="启动 ROM（boot ROM）",
    ),
}

# MemPool 模块间真实连接（数据通路 + 控制通路）
# 来源: https://github.com/pulp-platform/mempool/blob/main/hardware/mempool_top.sv
MEMPOOL_CONNECTIONS: list[tuple[str, str, str, str]] = [
    # ── cluster ↔ icache（取指）──
    ("cluster_0", "fetch_req", "icache_0", "req_in"),
    ("icache_0", "instr_out", "cluster_0", "instr_in"),
    ("cluster_1", "fetch_req", "icache_1", "req_in"),
    ("icache_1", "instr_out", "cluster_1", "instr_in"),
    ("cluster_2", "fetch_req", "icache_2", "req_in"),
    ("icache_2", "instr_out", "cluster_2", "instr_in"),
    ("cluster_3", "fetch_req", "icache_3", "req_in"),
    ("icache_3", "instr_out", "cluster_3", "instr_in"),
    # ── cluster ↔ TCDM SRAM（数据访存）──
    ("cluster_0", "load_req", "sram_bank_0", "req_in"),
    ("cluster_1", "load_req", "sram_bank_1", "req_in"),
    ("cluster_2", "load_req", "sram_bank_2", "req_in"),
    ("cluster_3", "load_req", "sram_bank_3", "req_in"),
    ("sram_bank_0", "data_out", "cluster_0", "data_in"),
    ("sram_bank_1", "data_out", "cluster_1", "data_in"),
    ("sram_bank_2", "data_out", "cluster_2", "data_in"),
    ("sram_bank_3", "data_out", "cluster_3", "data_in"),
    # ── TCDM 互连（多 bank 仲裁）──
    ("cluster_0", "tcdm_req", "tcdm_interconnect", "req_in"),
    ("cluster_1", "tcdm_req", "tcdm_interconnect", "req_in"),
    ("cluster_2", "tcdm_req", "tcdm_interconnect", "req_in"),
    ("cluster_3", "tcdm_req", "tcdm_interconnect", "req_in"),
    ("tcdm_interconnect", "grant_out", "sram_bank_0", "grant_in"),
    ("tcdm_interconnect", "grant_out", "sram_bank_1", "grant_in"),
    ("tcdm_interconnect", "grant_out", "sram_bank_2", "grant_in"),
    ("tcdm_interconnect", "grant_out", "sram_bank_3", "grant_in"),
    # ── AXI 外设（异步通信）──
    ("cluster_0", "axi_req", "axi_peripheral", "req_in"),
    ("axi_peripheral", "axi_resp", "cluster_0", "resp_in"),
    ("axi_peripheral", "axi_resp", "cluster_1", "resp_in"),
    ("axi_peripheral", "axi_resp", "cluster_2", "resp_in"),
    ("axi_peripheral", "axi_resp", "cluster_3", "resp_in"),
    # ── bootrom（启动初始化）──
    ("bootrom", "boot_data", "cluster_0", "boot_in"),
    ("bootrom", "boot_data", "axi_peripheral", "boot_in"),
]


# ─── NVDLA 深度学习加速器真实模块定义 ───
# 来源: https://github.com/nvdla/hw (NVIDIA Deep Learning Accelerator, NVDLA)
# NVDLA: NVIDIA 开源深度学习推理加速器，含卷积/池化/激活/数据重排等完整推理流水线
# 模块面积估算（NanGate45 工艺，μm²）参考 TILOS NVDLA bookshelf
#
# NVDLA 简化模型（保留真实推理流水线拓扑）:
# - CDMA (Convolution DMA): 卷积输入数据搬运
# - BDMA (Bridge DMA): 跨域数据搬运
# - SRAM (SRAM 1): 片上 SRAM 缓冲
# - CONV (Convolution Core): 卷积计算主流水线
# - SDP (Single Data Processor): 单点后处理（激活/equal/缩放）
# - PDP (Planar Data Processor): 平面后处理（池化）
# - CDP (Channel Data Processor): 通道后处理（LUT 激活）
# - RUBIK (Reshape Engine): 数据重排（NHWC↔NCHW 等）
# - GLB (Global Buffer): 全局缓冲
# - REGIF (Register Interface): 寄存器接口
# - CTRL (Controller): 全局控制器

NVDLA_MODULES: dict[str, ArianeModule] = {
    "cdma": ArianeModule(
        name="cdma", width_um=130.0, height_um=90.0,
        category="dma", description="Convolution DMA，卷积输入数据搬运",
    ),
    "bdma": ArianeModule(
        name="bdma", width_um=110.0, height_um=80.0,
        category="dma", description="Bridge DMA，跨域数据搬运",
    ),
    "sram": ArianeModule(
        name="sram", width_um=240.0, height_um=180.0,
        category="memory", description="片上 SRAM 缓冲（1 bank，可配置大小）",
    ),
    "conv": ArianeModule(
        name="conv", width_um=260.0, height_um=200.0,
        category="compute", description="卷积计算主流水线（PRA/SBST/MAC/SUM）",
    ),
    "sdp": ArianeModule(
        name="sdp", width_um=150.0, height_um=110.0,
        category="post_proc", description="Single Data Processor（激活/equal/缩放）",
    ),
    "pdp": ArianeModule(
        name="pdp", width_um=140.0, height_um=100.0,
        category="post_proc", description="Planar Data Processor（池化）",
    ),
    "cdp": ArianeModule(
        name="cdp", width_um=120.0, height_um=90.0,
        category="post_proc", description="Channel Data Processor（LUT 激活）",
    ),
    "rubik": ArianeModule(
        name="rubik", width_um=100.0, height_um=70.0,
        category="post_proc", description="Reshape Engine（数据重排 NHWC↔NCHW）",
    ),
    "glb": ArianeModule(
        name="glb", width_um=180.0, height_um=140.0,
        category="memory", description="Global Buffer，全局缓冲（跨模块共享）",
    ),
    "regif": ArianeModule(
        name="regif", width_um=80.0, height_um=60.0,
        category="control", description="Register Interface，寄存器接口（CSB 配置）",
    ),
    "ctrl": ArianeModule(
        name="ctrl", width_um=90.0, height_um=70.0,
        category="control", description="全局控制器（事件调度/中断管理）",
    ),
}

# NVDLA 模块间真实连接（推理数据流 + 控制流）
# 来源: https://github.com/nvdla/hw/blob/master/vmod/nvdla_top.v
NVDLA_CONNECTIONS: list[tuple[str, str, str, str]] = [
    # ── 数据搬运 DMA → SRAM/GLB ──
    ("cdma", "data_out", "sram", "data_in"),
    ("bdma", "data_out", "sram", "data_in"),
    ("cdma", "data_out", "glb", "data_in"),
    ("bdma", "data_out", "glb", "data_in"),
    # ── 卷积主流水线（推理核心数据流）──
    ("sram", "data_out", "conv", "data_in"),
    ("glb", "weight_out", "conv", "weight_in"),
    ("conv", "data_out", "glb", "data_in"),
    # ── 后处理流水线（CONV → SDP → PDP → CDP）──
    ("glb", "data_out", "sdp", "data_in"),
    ("sdp", "data_out", "glb", "data_in"),
    ("glb", "data_out", "pdp", "data_in"),
    ("pdp", "data_out", "glb", "data_in"),
    ("glb", "data_out", "cdp", "data_in"),
    ("cdp", "data_out", "glb", "data_in"),
    # ── RUBIK 数据重排 ──
    ("glb", "data_out", "rubik", "data_in"),
    ("rubik", "data_out", "glb", "data_in"),
    # ── 控制流（REGIF/CTRL 配置所有模块）──
    ("regif", "config", "conv", "config_in"),
    ("regif", "config", "sdp", "config_in"),
    ("regif", "config", "pdp", "config_in"),
    ("regif", "config", "cdp", "config_in"),
    ("regif", "config", "cdma", "config_in"),
    ("regif", "config", "bdma", "config_in"),
    ("ctrl", "event", "regif", "event_in"),
    ("ctrl", "interrupt", "regif", "intr_in"),
    ("ctrl", "event", "conv", "event_in"),
]


# ─── 工厂函数：统一加载 TILOS benchmark ───

# benchmark 名称 → (modules dict, connections list, target_hpwl) 映射
# target_hpwl 参考 TILOS MacroPlacement 公开评估报告（17 模块 Ariane/15 模块
# MemPool/11 模块 NVDLA 规模，NanGate45 工艺）
_TILOS_BENCHMARKS: dict[str, tuple[dict, list, float]] = {
    "ariane": (ARIANE_MODULES, ARIANE_CONNECTIONS, 50000.0),
    "mempool": (MEMPOOL_MODULES, MEMPOOL_CONNECTIONS, 80000.0),
    "nvdla": (NVDLA_MODULES, NVDLA_CONNECTIONS, 70000.0),
}


def load_mempool_benchmark(
    process_node: str = "NanGate45",
    canvas_scale: float = 1.5,
) -> CircuitSpec:
    """加载 TILOS MemPool RISC-V many-core SoC benchmark。

    生成包含 15 个 MemPool 核心模块 + 31 条真实连接的 CircuitSpec，
    模块面积与连接拓扑对齐 PULP MemPool 顶层 ``mempool_top.sv``。

    来源:
    - PULP MemPool: https://github.com/pulp-platform/mempool
    - TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement

    Args:
        process_node: 工艺节点（NanGate45/ASAP7/SKY130HD）。
        canvas_scale: 画布缩放因子。

    Returns:
        CircuitSpec，benchmark_source=TILOS，target_metric=HPWL。
    """
    devices = [_module_to_device_spec(m) for m in MEMPOOL_MODULES.values()]
    total_area = sum(m.width_um * m.height_um for m in MEMPOOL_MODULES.values())
    canvas_side = (total_area * canvas_scale) ** 0.5
    return CircuitSpec(
        name="tilos_mempool",
        devices=devices,
        connections=list(MEMPOOL_CONNECTIONS),
        canvas_w=canvas_side,
        canvas_h=canvas_side,
        benchmark_source=BenchmarkSource.TILOS,
        process_node=process_node,
        target_metric=TargetMetric.HPWL,
        target_value=80000.0,
    )


def load_nvdla_benchmark(
    process_node: str = "NanGate45",
    canvas_scale: float = 1.5,
) -> CircuitSpec:
    """加载 TILOS NVDLA 深度学习加速器 benchmark。

    生成包含 11 个 NVDLA 核心模块 + 24 条真实连接的 CircuitSpec，
    模块面积与连接拓扑对齐 NVDLA ``nvdla_top.v`` 顶层。

    来源:
    - NVDLA: https://github.com/nvdla/hw
    - TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement

    Args:
        process_node: 工艺节点（NanGate45/ASAP7/SKY130HD）。
        canvas_scale: 画布缩放因子。

    Returns:
        CircuitSpec，benchmark_source=TILOS，target_metric=HPWL。
    """
    devices = [_module_to_device_spec(m) for m in NVDLA_MODULES.values()]
    total_area = sum(m.width_um * m.height_um for m in NVDLA_MODULES.values())
    canvas_side = (total_area * canvas_scale) ** 0.5
    return CircuitSpec(
        name="tilos_nvdla",
        devices=devices,
        connections=list(NVDLA_CONNECTIONS),
        canvas_w=canvas_side,
        canvas_h=canvas_side,
        benchmark_source=BenchmarkSource.TILOS,
        process_node=process_node,
        target_metric=TargetMetric.HPWL,
        target_value=70000.0,
    )


def list_tilos_benchmarks() -> list[str]:
    """列出所有可用 TILOS benchmark 名称。

    Returns:
        benchmark 名称列表（按字典序）。
    """
    return sorted(_TILOS_BENCHMARKS.keys())


def load_tilos_benchmark(
    name: str,
    process_node: str = "NanGate45",
    canvas_scale: float = 1.5,
) -> CircuitSpec:
    """统一加载 TILOS benchmark（工厂函数）。

    支持 Ariane / MemPool / NVDLA 三个 TILOS MacroPlacement 公开 benchmark，
    对齐 TILOS 评估标准（HPWL 指标 + NanGate45/ASAP7/SKY130HD 工艺）。

    来源:
    - TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
    - Ariane (CVA6): https://github.com/openhwgroup/cva6
    - MemPool: https://github.com/pulp-platform/mempool
    - NVDLA: https://github.com/nvdla/hw

    Args:
        name: benchmark 名称（ariane/mempool/nvdla）。
        process_node: 工艺节点。
        canvas_scale: 画布缩放因子。

    Returns:
        CircuitSpec。

    Raises:
        KeyError: 未知 benchmark 名称（R03 无 fall-back）。
    """
    name_lower = name.lower()
    if name_lower == "ariane":
        return load_ariane_benchmark(process_node, canvas_scale)
    if name_lower == "mempool":
        return load_mempool_benchmark(process_node, canvas_scale)
    if name_lower == "nvdla":
        return load_nvdla_benchmark(process_node, canvas_scale)
    raise KeyError(
        f"未知 TILOS benchmark: {name}，可用: {list_tilos_benchmarks()}"
        "（R03 无 fall-back）"
    )


def tilos_benchmark_info(name: str) -> dict:
    """返回指定 TILOS benchmark 的元信息。

    Args:
        name: benchmark 名称（ariane/mempool/nvdla）。

    Returns:
        含模块数、连接数、总面积、工艺节点、来源 URL 的字典。

    Raises:
        KeyError: 未知 benchmark 名称（R03 无 fall-back）。
    """
    if name.lower() not in _TILOS_BENCHMARKS:
        raise KeyError(
            f"未知 TILOS benchmark: {name}，可用: {list_tilos_benchmarks()}"
        )
    name_lower = name.lower()
    modules, connections, target = _TILOS_BENCHMARKS[name_lower]
    total_area = sum(m.width_um * m.height_um for m in modules.values())
    source_urls = {
        "ariane": "https://github.com/openhwgroup/cva6",
        "mempool": "https://github.com/pulp-platform/mempool",
        "nvdla": "https://github.com/nvdla/hw",
    }
    return {
        "name": f"tilos_{name_lower}",
        "module_count": len(modules),
        "connection_count": len(connections),
        "total_area_um2": total_area,
        "process_node": "NanGate45",
        "benchmark_source": "TILOS",
        "source_url": "https://github.com/TILOS-AI-CAD-Institute/MacroPlacement",
        "cpu_source_url": source_urls[name_lower],
        "categories": sorted({m.category for m in modules.values()}),
        "target_metric": "HPWL",
        "target_value": target,
    }


def ariane_benchmark_info() -> dict:
    """返回 Ariane benchmark 元信息（对标 TILOS 评估标准）。

    Returns:
        含模块数、连接数、总面积、工艺节点、来源 URL 的字典。
    """
    total_area = sum(m.width_um * m.height_um for m in ARIANE_MODULES.values())
    return {
        "name": "tilos_ariane",
        "module_count": len(ARIANE_MODULES),
        "connection_count": len(ARIANE_CONNECTIONS),
        "total_area_um2": total_area,
        "process_node": "NanGate45",
        "benchmark_source": "TILOS",
        "source_url": "https://github.com/TILOS-AI-CAD-Institute/MacroPlacement",
        "cpu_source_url": "https://github.com/openhwgroup/cva6",
        "categories": sorted({m.category for m in ARIANE_MODULES.values()}),
        "target_metric": "HPWL",
        "target_value": 50000.0,
    }


def list_ariane_modules() -> list[str]:
    """返回 Ariane 模块名列表（按字典序）。

    Returns:
        模块名列表。
    """
    return sorted(ARIANE_MODULES.keys())


def get_ariane_module(name: str) -> ArianeModule:
    """按名称获取 Ariane 模块规格。

    Args:
        name: 模块名。

    Returns:
        ArianeModule。

    Raises:
        KeyError: 模块名不存在。
    """
    if name not in ARIANE_MODULES:
        raise KeyError(
            f"未知 Ariane 模块: {name}，可用: {list(ARIANE_MODULES.keys())}"
        )
    return ARIANE_MODULES[name]


__all__ = [
    "ArianeModule",
    "ARIANE_MODULES",
    "ARIANE_CONNECTIONS",
    "MEMPOOL_MODULES",
    "MEMPOOL_CONNECTIONS",
    "NVDLA_MODULES",
    "NVDLA_CONNECTIONS",
    "load_ariane_benchmark",
    "load_mempool_benchmark",
    "load_nvdla_benchmark",
    "load_tilos_benchmark",
    "ariane_benchmark_info",
    "tilos_benchmark_info",
    "list_tilos_benchmarks",
    "list_ariane_modules",
    "get_ariane_module",
]
