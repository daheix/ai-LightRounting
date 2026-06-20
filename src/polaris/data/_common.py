"""数据加载器共享工具函数。

来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- PICBench: https://github.com/PICDA/PICBench
- PhIDO: https://github.com/JPPhotonics/PhIDO-Release
"""

from __future__ import annotations


def split_port_ref(ref: str) -> tuple[str, str]:
    """拆分端口引用 'device,port' → (device, port)。

    支持两种分隔符：
    - 逗号分隔：``"dev_name,port_name"``
    - 冒号分隔：``"dev_name:port_name"``

    无分隔符时返回 ``(ref, "o1")``，默认端口名为 ``o1``。

    Args:
        ref: 端口引用字符串。

    Returns:
        (device_name, port_name) 元组。
    """
    if "," in ref:
        parts = ref.split(",", 1)
        return parts[0].strip(), parts[1].strip()
    if ":" in ref:
        parts = ref.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return ref.strip(), "o1"
