"""作业配方（Recipe）+ 仿真配置 + YAML/JSON 序列化。

对齐商业 EDA 工具的"配方/配置"概念：
- Luceda IPKISS: 设计配方（recipe）封装器件、流程与参数
- Cadence ADE-XL: 测试配置（corners/tests）序列化
- Synopsys ICC2: 实现流程配置（flow config）持久化
- Ansys Lumerical: 仿真脚本参数集

学术来源:
- IPKISS 设计配方: https://docs.lucedaphotonics.com/
- Cadence ADE-XL 配置管理: https://docs.cadence.com/
- Synopsys ICC2 流程配置: https://www.synopsys.com/
- Ansys Lumerical 参数集: https://www.ansys.com/products/photonics
- Effective Python 3rd Ed. Item 32（优先抛异常而非返回 None）:
  https://effectivepython.com/
- Real Python: Effectively Raising Exceptions（fail-fast 原则）:
  https://realpython.com/python-raise-exception/

Recipe 是可序列化的流水线配置，支持 JSON 与 YAML 双向序列化。
YAML 序列化采用简单缩进格式，不依赖 PyYAML 第三方库。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class SimConfig:
    """仿真配置

    封装 S 参数仿真与迭代优化的参数。
    """

    max_iterations: int = 3            # 最大迭代次数
    loss_target_db: float = 5.0        # 目标插损（dB）
    use_real_simulator: bool = False   # 是否使用真实仿真器（而非快速近似）


@dataclass
class Recipe:
    """作业配方（可序列化的流水线配置）

    一个 Recipe 完整描述一次作业的输入参数：
    - preset_id: 电路预设 ID（如 mzi / ring / mzi_lattice）
    - platform: 工艺平台（SOI/SiN/InP/LNOI）
    - placement_algo / router_algo: 布局与布线算法选择
    - sim_config: 仿真参数
    - enabled_stages: 启用的阶段 ID 列表（默认全部 1-10）
    - custom_circuit: 自定义电路规格（None 则使用 preset_id）
    """

    preset_id: str = "mzi"  # 电路预设 ID
    platform: str = "SOI"  # SOI/SiN/InP/LNOI
    placement_algo: str = "analytical"  # rl/analytical/ppo_gnn
    router_algo: str = "curvy"  # curvy/diagonal/hybrid
    sim_config: SimConfig = field(default_factory=SimConfig)
    output_dir: str = "out/jobs"
    enabled_stages: list[int] = field(
        default_factory=lambda: list(range(1, 11))
    )  # 默认启用全部 10 阶段
    canvas_w: float = 1000.0
    canvas_h: float = 600.0
    custom_circuit: dict | None = None  # 自定义电路规格（None 则用 preset_id）

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "preset_id": self.preset_id,
            "platform": self.platform,
            "placement_algo": self.placement_algo,
            "router_algo": self.router_algo,
            "sim_config": {
                "max_iterations": self.sim_config.max_iterations,
                "loss_target_db": self.sim_config.loss_target_db,
                "use_real_simulator": self.sim_config.use_real_simulator,
            },
            "output_dir": self.output_dir,
            "enabled_stages": self.enabled_stages,
            "canvas_w": self.canvas_w,
            "canvas_h": self.canvas_h,
            "custom_circuit": self.custom_circuit,
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> Recipe:
        """从字典反序列化"""
        sim_cfg = d.get("sim_config", {})
        return cls(
            preset_id=d.get("preset_id", "mzi"),
            platform=d.get("platform", "SOI"),
            placement_algo=d.get("placement_algo", "analytical"),
            router_algo=d.get("router_algo", "curvy"),
            sim_config=SimConfig(
                max_iterations=sim_cfg.get("max_iterations", 3),
                loss_target_db=sim_cfg.get("loss_target_db", 5.0),
                use_real_simulator=sim_cfg.get("use_real_simulator", False),
            ),
            output_dir=d.get("output_dir", "out/jobs"),
            enabled_stages=d.get("enabled_stages", list(range(1, 11))),
            canvas_w=d.get("canvas_w", 1000.0),
            canvas_h=d.get("canvas_h", 600.0),
            custom_circuit=d.get("custom_circuit"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> Recipe:
        """从 JSON 字符串反序列化"""
        return cls.from_dict(json.loads(json_str))

    def to_yaml(self) -> str:
        """YAML 序列化（不依赖 PyYAML，用简单缩进格式）"""
        lines: list[str] = []
        d = self.to_dict()
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"{k}:")
                for kk, vv in v.items():
                    lines.append(f"  {kk}: {vv}")
            elif isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            elif v is None:
                lines.append(f"{k}: null")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    @staticmethod
    def _parse_yaml_top_level(line: str, d: dict) -> tuple[str | None, bool]:
        """解析 YAML 顶层 key: value 行（R628 Extract Method）。

        Returns:
            (new_current_key, handled)。handled=False 表示非顶层行。
        """
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if not m or line.startswith(" "):
            return None, False
        key, val = m.group(1), m.group(2)
        if val == "":
            d[key] = {}
        elif val == "null":
            d[key] = None
        else:
            d[key] = _coerce_scalar(val)
        return key, True

    @staticmethod
    def _parse_yaml_list_item(line: str, d: dict, current_key: str | None) -> bool:
        """解析 YAML 列表项行（R628 Extract Method）。

        Returns:
            True 若该行为列表项。
        """
        if not line.startswith("  - "):
            return False
        val = line[4:].strip()
        item = _coerce_scalar(val)
        if current_key and isinstance(d.get(current_key), list):
            d[current_key].append(item)
        elif current_key and d.get(current_key) == {}:
            d[current_key] = [item]
        return True

    @staticmethod
    def _parse_yaml_sub_key(line: str, d: dict, current_key: str | None) -> None:
        """解析 YAML 子 key 行（R628 Extract Method）。"""
        if not line.startswith("  "):
            return
        m2 = re.match(r"^\s+(\w+):\s*(.*)$", line)
        if m2 and current_key:
            kk, vv = m2.group(1), m2.group(2)
            if isinstance(d.get(current_key), dict):
                d[current_key][kk] = _coerce_scalar(vv)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> Recipe:
        """YAML 反序列化（简单解析器，不依赖 PyYAML）

        支持本类 to_yaml 生成的格式：顶层 key、二级 key、列表项。
        """
        d: dict = {}
        current_key: str | None = None
        for line in yaml_str.strip().split("\n"):
            line = line.rstrip()
            if not line:
                continue
            new_key, handled = cls._parse_yaml_top_level(line, d)
            if handled:
                current_key = new_key
                continue
            if cls._parse_yaml_list_item(line, d, current_key):
                continue
            cls._parse_yaml_sub_key(line, d, current_key)
        return cls.from_dict(d)


def _coerce_scalar(val: str):
    """将字符串标量转换为 int/float/str（内部辅助函数）。

    R03 合规：原 ``except (ValueError, AttributeError): pass`` 是静默吞异常的
    fall-back——对 ``str`` 输入 ``str.replace``/``str.isdigit`` 永不抛这两类异常，
    该 except 仅在调用方违反类型契约（传入非 str）时掩盖 Bug。现已移除：
    非字符串输入由 ``val.isdigit()`` 自然抛 ``AttributeError`` 上抛告警，
    禁止 fall-back 静默吞没（Effective Python Item 32: 优先抛异常而非返回 None）。
    """
    if val.isdigit():
        return int(val)
    if val.replace(".", "").isdigit():
        return float(val)
    return val
