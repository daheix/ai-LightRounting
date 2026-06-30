"""布局引擎子包。

负责网表解析、连接图构建、布局环境（Gymnasium 接口）
与基于 GNN 的状态编码。

参考文献：
[1] Mirhoseini A, Goldie A, Yazgan M, et al. A graph placement methodology for fast chip design[J]. Nature, 2021, 594(7862): 207-212. https://www.nature.com/articles/s41586-021-03544-w
[2] Lin Y, Dhar S, Li W, et al. DREAMPlace: Deep learning toolkit-enabled GPU acceleration for modern VLSI placement[J]. IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 2021, 40(4): 748-761. https://doi.org/10.1109/TCAD.2020.3003843
[3] Kipf T N, Welling M. Semi-supervised classification with graph convolutional networks[C]//International Conference on Learning Representations (ICLR). 2017. https://arxiv.org/abs/1609.02907
[4] Veličković P, Cucurull G, Casanova A, et al. Graph attention networks[C]//International Conference on Learning Representations (ICLR). 2018. https://arxiv.org/abs/1710.10903
[5] Schlichtkrull M, Kipf T N, Bloem P, et al. Modeling relational data with graph convolutional networks[C]//European Semantic Web Conference (ESWC). 2018: 593-607. https://arxiv.org/abs/1703.06103
[6] Gilmer J, Schoenholz S S, Riley P F, et al. Neural message passing for quantum chemistry[C]//International Conference on Machine Learning (ICML). 2017: 1263-1272. https://arxiv.org/abs/1704.01212
"""

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
