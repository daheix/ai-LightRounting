"""示例 4：PDK 器件库查询与器件实例化。

演示如何使用 PoLaRIS 的 PDK 器件库：
- 查询四大平台（SOI/SiN/InP/LNOI）的器件清单
- 按平台/类别检索器件
- 实例化器件并查看端口/参数/来源溯源

运行方式：
    python publish/examples/04_pdk_catalog.py

来源:
- AIM Photonics: https://www.latitudeda.com/document/716
- gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
"""

from __future__ import annotations

from polaris.pdk import (
    INP_DEVICES,
    LNOI_DEVICES,
    SIN_DEVICES,
    SOI_DEVICES,
    DeviceCatalog,
    default_catalog,
)


def main() -> None:
    """运行 PDK 器件库查询示例。"""
    print("=" * 60)
    print("PoLaRIS 示例 4：PDK 器件库查询与器件实例化")
    print("=" * 60)

    # 1. 查看四大平台器件数量
    print("\n[步骤 1] 四大平台器件工厂汇总")
    print(f"  SOI:  {len(SOI_DEVICES)} 个器件工厂")
    print(f"  SiN:  {len(SIN_DEVICES)} 个器件工厂")
    print(f"  InP:  {len(INP_DEVICES)} 个器件工厂")
    print(f"  LNOI: {len(LNOI_DEVICES)} 个器件工厂")

    # 2. 构建默认 catalog
    print("\n[步骤 2] 构建默认 DeviceCatalog（注册四平台全部器件）")
    catalog = default_catalog()
    print(f"  总器件数: {len(catalog)}")
    print(f"  已注册平台: {catalog.platforms}")

    # 3. 按平台检索
    print("\n[步骤 3] 按平台检索器件")
    for platform in catalog.platforms:
        devs = catalog.list_by_platform(platform)
        print(f"  {platform}: {len(devs)} 个器件")

    # 4. 按类别检索
    print("\n[步骤 4] 按类别检索器件（SOI 平台）")
    for category in ["passive", "active", "source", "detector"]:
        devs = catalog.list_devices(platform="SOI", category=category)
        if devs:
            print(f"  SOI/{category}: {len(devs)} 个器件")
            for d in devs[:3]:
                print(f"    - {d.name} (id={d.device_id})")
            if len(devs) > 3:
                print(f"    ... 还有 {len(devs) - 3} 个")

    # 5. 实例化器件并查看端口
    print("\n[步骤 5] 实例化 SOI MMI 1x2 并查看端口/参数")
    from polaris.pdk.soi import make_mmi_1x2

    mmi = make_mmi_1x2()
    print(f"  器件名: {mmi.name}")
    print(f"  平台: {mmi.platform}")
    print(f"  类别: {mmi.category}")
    print(f"  端口数: {len(mmi.ports)}")
    for p in mmi.ports:
        print(f"    {p.name}: ({p.x:.2f}, {p.y:.2f}), 方向={p.direction.value}, 宽度={p.width:.2f}μm")
    print(f"  参数: {dict(list(mmi.params.items())[:5])}...")
    if mmi.source:
        print(f"  来源: {mmi.source.title}")
        print(f"  URL: {mmi.source.url}")

    # 6. 来源溯源校验
    print("\n[步骤 6] 来源溯源校验")
    missing = catalog.validate_sources()
    if missing:
        print(f"  警告: {len(missing)} 个器件缺少 source.url: {missing[:5]}")
    else:
        print("  全部器件 source.url 非空，溯源合规")

    print("\n示例 4 完成。")


if __name__ == "__main__":
    main()
