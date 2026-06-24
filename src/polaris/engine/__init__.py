"""布局引擎子包。

负责网表解析、连接图构建、布局环境（Gymnasium 接口）
与基于 GNN 的状态编码。
"""
<<<<<<< HEAD

# R33: AlphaChip Edge-GNN 对齐（光电子专用边特征 + 多关系 + GAT）
from polaris.engine.alphachip_gnn import (
    NET_RELATION_CONTROL,
    NET_RELATION_ELECTRICAL,
    NET_RELATION_OPTICAL,
    NUM_NET_RELATIONS,
    PHOTONIC_EDGE_DIM,
    AlphaChipEdgeGNN,
    GATLayer,
    MultiRelationalEdgeGraphEncoder,
    PhotonicEdgeFeatureConfig,
    build_photonic_edge_features,
)

__all__ = [
    # R33 AlphaChip Edge-GNN 对齐
    "AlphaChipEdgeGNN",
    "GATLayer",
    "MultiRelationalEdgeGraphEncoder",
    "NET_RELATION_CONTROL",
    "NET_RELATION_ELECTRICAL",
    "NET_RELATION_OPTICAL",
    "NUM_NET_RELATIONS",
    "PHOTONIC_EDGE_DIM",
    "PhotonicEdgeFeatureConfig",
    "build_photonic_edge_features",
]
=======
>>>>>>> trae/solo-agent-pkVjID
