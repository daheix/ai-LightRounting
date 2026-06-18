"""PoLaRIS 标准光子器件库。

定义光子电路中常用的标准器件规格，包括 MZI、环形谐振器、
定向耦合器、MMI、Y 分支、光栅耦合器、加热器、波导等。

数据来源:
- GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
- UBC SiEPIC PDK: https://github.com/gdsfactory/ubc
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from polaris.data.specs import DeviceSpec

STANDARD_DEVICES: dict[str, DeviceSpec] = {
    "mzi": DeviceSpec(
        name="mzi",
        device_type="mzi",
        width_um=200.0,
        height_um=50.0,
        ports=[
            ("o1", 0.0, 25.0, "E"),
            ("o2", 200.0, 25.0, "W"),
        ],
        params={"delta_length": 10.0},
    ),
    "ring_single": DeviceSpec(
        name="ring_single",
        device_type="ring",
        width_um=60.0,
        height_um=60.0,
        ports=[
            ("o1", 0.0, 30.0, "E"),
            ("o2", 60.0, 30.0, "W"),
        ],
        params={"radius": 10.0},
    ),
    "ring_double": DeviceSpec(
        name="ring_double",
        device_type="ring",
        width_um=60.0,
        height_um=80.0,
        ports=[
            ("o1", 0.0, 20.0, "E"),
            ("o2", 60.0, 20.0, "W"),
            ("o3", 0.0, 60.0, "E"),
            ("o4", 60.0, 60.0, "W"),
        ],
        params={"radius": 10.0},
    ),
    "dc": DeviceSpec(
        name="dc",
        device_type="directional_coupler",
        width_um=40.0,
        height_um=20.0,
        ports=[
            ("o1", 0.0, 5.0, "E"),
            ("o2", 0.0, 15.0, "E"),
            ("o3", 40.0, 5.0, "W"),
            ("o4", 40.0, 15.0, "W"),
        ],
        params={"gap": 0.2, "length": 10.0},
    ),
    "mmi1x2": DeviceSpec(
        name="mmi1x2",
        device_type="mmi",
        width_um=30.0,
        height_um=20.0,
        ports=[
            ("o1", 0.0, 10.0, "E"),
            ("o2", 30.0, 5.0, "W"),
            ("o3", 30.0, 15.0, "W"),
        ],
    ),
    "mmi2x2": DeviceSpec(
        name="mmi2x2",
        device_type="mmi",
        width_um=30.0,
        height_um=20.0,
        ports=[
            ("o1", 0.0, 5.0, "E"),
            ("o2", 0.0, 15.0, "E"),
            ("o3", 30.0, 5.0, "W"),
            ("o4", 30.0, 15.0, "W"),
        ],
    ),
    "y_branch": DeviceSpec(
        name="y_branch",
        device_type="y_branch",
        width_um=20.0,
        height_um=20.0,
        ports=[
            ("o1", 0.0, 10.0, "E"),
            ("o2", 20.0, 5.0, "W"),
            ("o3", 20.0, 15.0, "W"),
        ],
    ),
    "gc": DeviceSpec(
        name="gc",
        device_type="grating_coupler",
        width_um=20.0,
        height_um=20.0,
        ports=[("o1", 10.0, 0.0, "N")],
    ),
    "heater": DeviceSpec(
        name="heater",
        device_type="heater",
        width_um=100.0,
        height_um=10.0,
        ports=[
            ("o1", 0.0, 5.0, "E"),
            ("o2", 100.0, 5.0, "W"),
        ],
        params={"length": 80.0},
    ),
    "wg_100": DeviceSpec(
        name="wg_100",
        device_type="waveguide",
        width_um=100.0,
        height_um=0.5,
        ports=[
            ("o1", 0.0, 0.25, "E"),
            ("o2", 100.0, 0.25, "W"),
        ],
        params={"length": 100.0},
    ),
    "wg_200": DeviceSpec(
        name="wg_200",
        device_type="waveguide",
        width_um=200.0,
        height_um=0.5,
        ports=[
            ("o1", 0.0, 0.25, "E"),
            ("o2", 200.0, 0.25, "W"),
        ],
        params={"length": 200.0},
    ),
    "terminator": DeviceSpec(
        name="terminator",
        device_type="terminator",
        width_um=10.0,
        height_um=10.0,
        ports=[("o1", 0.0, 5.0, "E")],
    ),
    "crossing": DeviceSpec(
        name="crossing",
        device_type="crossing",
        width_um=20.0,
        height_um=20.0,
        ports=[
            ("o1", 0.0, 10.0, "E"),
            ("o2", 20.0, 10.0, "W"),
            ("o3", 10.0, 0.0, "N"),
            ("o4", 10.0, 20.0, "S"),
        ],
    ),
}

__all__ = ["STANDARD_DEVICES"]
