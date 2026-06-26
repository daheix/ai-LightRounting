"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5."""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
-"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2."""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.110"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://me"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = [""""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.2566"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class Tfsf"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E_inc[i]  位于 i·dx      （与 2D E_z[i, j] 同位）
        H_inc[i]  位于 (i+"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E_inc[i]  位于 i·dx      （与 2D E_z[i, j] 同位）
        H_inc[i]  位于 (i+0.5)·dx （与 2D H_y[i, j] 同位）

    Attributes:
        nx: 1D 网格点数，"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E_inc[i]  位于 i·dx      （与 2D E_z[i, j] 同位）
        H_inc[i]  位于 (i+0.5)·dx （与 2D H_y[i, j] 同位）

    Attributes:
        nx: 1D 网格点数，须 ≥ i1+2（提供 E_inc[i1+1]）。
        dx: 网格间距（米），与 2"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E_inc[i]  位于 i·dx      （与 2D E_z[i, j] 同位）
        H_inc[i]  位于 (i+0.5)·dx （与 2D H_y[i, j] 同位）

    Attributes:
        nx: 1D 网格点数，须 ≥ i1+2（提供 E_inc[i1+1]）。
        dx: 网格间距（米），与 2D 网格 dx 相同。
        dt: 时间步（秒），与 2D 主网格相同。
        ca, cb:"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E_inc[i]  位于 i·dx      （与 2D E_z[i, j] 同位）
        H_inc[i]  位于 (i+0.5)·dx （与 2D H_y[i, j] 同位）

    Attributes:
        nx: 1D 网格点数，须 ≥ i1+2（提供 E_inc[i1+1]）。
        dx: 网格间距（米），与 2D 网格 dx 相同。
        dt: 时间步（秒），与 2D 主网格相同。
        ca, cb: 1D leapfrog 系数（真空，cb = dt/ε_0）。
        da, db: 1D leap"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] += (cb_ez/dx) · H_inc[i0-1]    # TF 节点补齐入射 H
    E_z[i1+1, :] -= (cb_ez/dx) · H_inc[i1]      # SF 节点剔除入射 H

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["TfsfBox", "Incident1D", "apply_tfsf_correction"]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E_inc[i]  位于 i·dx      （与 2D E_z[i, j] 同位）
        H_inc[i]  位于 (i+0.5)·dx （与 2D H_y[i, j] 同位）

    Attributes:
        nx: 1D 网格点数，须 ≥ i1+2（提供 E_inc[i1+1]）。
        dx: 网格间距（米），与 2D 网格 dx 相同。
        dt: 时间步（秒），与 2D 主网格相同。
        ca, cb: 1D leapfrog 系数（真空，cb = dt/ε_0）。
        da, db: 1D leapfrog 系数（真空，db = dt/μ_0）。
        e_inc: 入射电场 E_z (nx,)。
        h_inc: 入