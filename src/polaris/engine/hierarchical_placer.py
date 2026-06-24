"""分块布局器（Hierarchical Placement）—— P0-2 v2.0 规模扩展（第70轮）。

将大规模器件布局分解为子问题：谱聚类/BFS 分块 → 块内解析法 → 块间解析法 → 合并。
总复杂度从 O(n²) 降为 O(n·sqrt(n))。

来源:
- 谱聚类: Shi & Malik, IEEE TPAMI 2000 (Normalized Cuts)
- DREAMPlace 分块: Lin et al., IEEE TCAD 2020
- BFS 分块: Karypis & Kumar 1998 (METIS)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

from polaris.engine.analytical_placer import (
    AnalyticalPlacer,
    AnalyticalPlacerConfig,
    warm_start_placement,
)

if TYPE_CHECKING:
    from polaris.data.specs import CircuitSpec


@dataclass
class HierarchicalPlacerConfig:
    """分块布局器配置。

    Attributes:
        n_clusters: 子块数量（None 时自动 = sqrt(n_devices)）。
        max_cluster_size: 单块最大器件数（超出则进一步分裂）。
        analytical_config: 块内/块间解析法布局配置。
        random_seed: 随机种子（谱聚类初始化）。

    默认值来源: Shi & Malik 2000 (sqrt(n) 最优分块数),
    DREAMPlace TCAD 2020 (500 器件内 200 迭代收敛)。
    """

    n_clusters: int | None = None
    max_cluster_size: int = 500
    analytical_config: AnalyticalPlacerConfig | None = None
    random_seed: int = 42


@dataclass
class _MergeContext:
    """块间合并上下文（降低 _merge_cluster_placement 参数个数）。"""

    placement: dict[str, tuple[float, float]]
    cluster_centers: dict[int, tuple[float, float]]
    labels: np.ndarray
    super_placement: dict[str, tuple[float, float]]
    cid2idx: dict[int, int]
    main_canvas: float


@dataclass
class _BfsContext:
    """BFS 单块收集上下文（降低 _bfs_collect_one_cluster 参数个数）。"""

    adj: list[list[int]]
    labels: np.ndarray
    start: int
    cluster_id: int
    target_size: int


@dataclass
class _IntraClusterContext:
    """块内解析法布局上下文（降低 _analytical_place_cluster 参数个数）。"""

    cluster_id: int
    names: list[str]
    cluster_canvas: float
    labels: np.ndarray
    placement: dict[str, tuple[float, float]]


class HierarchicalPlacer:
    """分块布局器（P0-2 v2.0 规模扩展）。

    算法流程: 1.谱聚类分块 → 2.块内 AnalyticalPlacer → 3.块间 AnalyticalPlacer → 4.合并。
    来源: Shi & Malik 2000, DREAMPlace TCAD 2020。
    """

    def __init__(
        self,
        circuit: CircuitSpec,
        config: HierarchicalPlacerConfig | None = None,
    ) -> None:
        """初始化分块布局器。

        Args:
            circuit: 电路规格（含器件与连接）。
            config: 分块配置（None 用默认）。
        """
        self.circuit = circuit
        self.config = config or HierarchicalPlacerConfig()
        self.device_names = [d.name for d in circuit.devices]
        self.n = len(circuit.devices)
        self.name_to_idx = {name: i for i, name in enumerate(self.device_names)}
        # 连接列表（索引化）
        self.connections = self._build_connections()
        # 自动确定子块数
        self.k = self._determine_n_clusters()

    def _build_connections(self) -> list[tuple[int, int]]:
        """构建索引化连接列表。"""
        conns: list[tuple[int, int]] = []
        for src, _sp, dst, _dp in self.circuit.connections:
            if src in self.name_to_idx and dst in self.name_to_idx:
                conns.append((self.name_to_idx[src], self.name_to_idx[dst]))
        return conns

    def _determine_n_clusters(self) -> int:
        """确定子块数量。

        默认 sqrt(n)，但确保单块不超过 max_cluster_size。

        Returns:
            子块数量 K。
        """
        if self.config.n_clusters is not None:
            return self.config.n_clusters
        # sqrt(n) 经验值
        k = max(2, int(np.ceil(np.sqrt(self.n))))
        # 确保单块不超过 max_cluster_size
        while k < self.n and self.n / k > self.config.max_cluster_size:
            k *= 2
        return min(k, self.n)

    def _build_adjacency_matrix(self) -> sparse.csr_matrix:
        """构建稀疏邻接矩阵（带权）。

        Returns:
            ``(n, n)`` 稀疏 CSR 邻接矩阵，W[i][j] = 连接 i-j 的权重。

        优化（第70轮）: 改用 scipy.sparse.csr_matrix，降低内存 O(n²)→O(nnz)，
        并支持 ARPACK 稀疏特征值求解。
        """
        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []
        for src, dst in self.connections:
            rows.extend([src, dst])
            cols.extend([dst, src])
            data.extend([1.0, 1.0])
        return sparse.csr_matrix(
            (data, (rows, cols)), shape=(self.n, self.n), dtype=np.float64
        )

    def _spectral_clustering(self) -> np.ndarray:
        """谱聚类分块（基于归一化拉普拉斯矩阵，稀疏 ARPACK 求解）。

        Returns:
            ``(n,)`` 聚类标签数组，labels[i] = 器件 i 的子块编号。

        来源:
            Shi & Malik 2000, Normalized Cuts

        优化（第70轮）:
        1. 使用 scipy.sparse + ARPACK (eigsh) 只计算前 K 个特征向量，
           复杂度从 O(n³) 降至 O(nnz·k)。
           来源: Lehoucq & Sorensen "Deflation Techniques for an Implicitly
           Re-Started Arnoldi Iteration" 1996 (ARPACK)。
        2. 大规模（n > 1000）改用 BFS 分块（O(n+nnz)），避免 ARPACK 收敛慢。
           来源: Karypis & Kumar "A Fast and High Quality Multilevel Scheme
           for Partitioning Irregular Graphs" 1998 (METIS BFS 思想)。
        """
        if self.n > 1000:
            # 大规模用 BFS 分块（O(n+nnz)，远快于谱聚类）
            return self._bfs_clustering()
        return self._spectral_clustering_dense()

    def _bfs_clustering(self) -> np.ndarray:
        """BFS 分块（大规模快速分块）。

        从随机起点 BFS 遍历，每收集 n/k 个器件形成一个子块。
        确保块内器件在图上拓扑相近（强局部性）。

        Returns:
            ``(n,)`` 聚类标签数组。

        来源:
            Karypis & Kumar 1998 (METIS), BFS 初始分割
        """
        rng = np.random.default_rng(self.config.random_seed)
        adj = self._build_adjacency_list()
        labels = np.full(self.n, -1, dtype=int)
        target_size = max(1, self.n // self.k)
        cluster_id = 0
        start_order = rng.permutation(self.n)
        for start in start_order:
            if labels[start] >= 0:
                continue
            if cluster_id >= self.k:
                labels[labels < 0] = self.k - 1
                break
            ctx = _BfsContext(
                adj=adj,
                labels=labels,
                start=int(start),
                cluster_id=cluster_id,
                target_size=target_size,
            )
            cluster_id = self._bfs_collect_one_cluster(ctx)
        labels[labels < 0] = self.k - 1
        return labels

    def _build_adjacency_list(self) -> list[list[int]]:
        """构建邻接表（BFS 分块用）。"""
        adj: list[list[int]] = [[] for _ in range(self.n)]
        for src, dst in self.connections:
            adj[src].append(dst)
            adj[dst].append(src)
        return adj

    def _bfs_collect_one_cluster(self, ctx: _BfsContext) -> int:
        """BFS 收集单个子块（不超过 target_size 个器件）。

        Args:
            ctx: BFS 收集上下文（含邻接表、标签、起点、块号、目标大小）。

        Returns:
            下一个子块编号（cluster_id + 1）。
        """
        queue = [ctx.start]
        ctx.labels[ctx.start] = ctx.cluster_id
        count = 1
        head = 0
        while head < len(queue) and count < ctx.target_size:
            node = queue[head]
            head += 1
            for nb in ctx.adj[node]:
                if ctx.labels[nb] < 0:
                    ctx.labels[nb] = ctx.cluster_id
                    queue.append(nb)
                    count += 1
                    if count >= ctx.target_size:
                        break
        return ctx.cluster_id + 1

    def _spectral_clustering_dense(self) -> np.ndarray:
        """谱聚类分块（小规模，ARPACK 稀疏求解）。

        Returns:
            ``(n,)`` 聚类标签数组。

        来源:
            Shi & Malik 2000, Normalized Cuts
        """
        rng = np.random.default_rng(self.config.random_seed)
        W = self._build_adjacency_matrix()
        # 度矩阵 D（对角线向量）
        d = np.asarray(W.sum(axis=1)).ravel()
        d_safe = np.where(d > 0, d, 1.0)
        # 归一化邻接矩阵: M = D^(-1/2) W D^(-1/2)
        # 其最大特征值对应 L_sym = I - M 的最小特征值
        d_inv_sqrt = 1.0 / np.sqrt(d_safe)
        M = W.copy().astype(np.float64)
        # 行列缩放
        M = sparse.diags(d_inv_sqrt) @ M @ sparse.diags(d_inv_sqrt)
        k_eig = min(self.k, self.n - 1)
        try:
            # ARPACK 求 M 的前 k 个最大特征值（= L_sym 的前 k 个最小特征值）
            # which='LA' = Largest Algebraic
            _eigenvalues, eigenvectors = eigsh(M, k=k_eig, which="LA")
            # 行归一化
            norms = np.linalg.norm(eigenvectors, axis=1, keepdims=True)
            norms_safe = np.where(norms > 0, norms, 1.0)
            U_normalized = eigenvectors / norms_safe
            # K-means 聚类
            labels = self._kmeans(U_normalized, self.k, rng)
        except (RuntimeError, ValueError) as e:
            # ARPACK 收敛失败时退化为 BFS 分块（拓扑感知，非均匀分块假数据）
            # 来源: Karypis & Kumar 1998 METIS BFS 思想
            import warnings
            warnings.warn(
                f"ARPACK 谱聚类收敛失败（{e}），退化为 BFS 拓扑分块。"
                f"布局结果可能次优，建议检查连接拓扑或减小分块数 k={self.k}。",
                RuntimeWarning,
                stacklevel=2,
            )
            labels = self._bfs_clustering()
        return labels

    def _kmeans(
        self,
        X: np.ndarray,
        k: int,
        rng: np.random.Generator,
        max_iter: int = 100,
    ) -> np.ndarray:
        """简单 K-means 聚类（避免依赖 scikit-learn）。

        Args:
            X: 数据矩阵 ``(n, d)``。
            k: 聚类数。
            rng: 随机数生成器。
            max_iter: 最大迭代次数。

        Returns:
            ``(n,)`` 聚类标签数组。

        来源:
            Lloyd's algorithm, "Least squares quantization in PCM",
            IEEE Trans. Inf. Theory, 28(2), 129-137 (1982)
        """
        n = X.shape[0]
        # 随机初始化中心
        centers = X[rng.choice(n, k, replace=False)].copy()
        labels = np.zeros(n, dtype=int)
        for _ in range(max_iter):
            # 分配步骤：每个点分配到最近中心
            dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
            new_labels = np.argmin(dists, axis=1)
            # 收敛判断
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels
            # 更新步骤：中心 = 簇内均值
            for j in range(k):
                mask = labels == j
                if mask.any():
                    centers[j] = X[mask].mean(axis=0)
        return labels

    def _build_cluster_subcircuit(
        self,
        cluster_id: int,
        device_indices: np.ndarray,
    ) -> CircuitSpec:
        """构建子块子电路（供 AnalyticalPlacer 使用）。

        Args:
            cluster_id: 子块编号。
            device_indices: 子块内器件索引数组。

        Returns:
            子电路规格（含子块内器件与连接）。
        """
        from polaris.data.specs import CircuitSpec

        idx_set = set(int(i) for i in device_indices)
        idx_to_local = {int(i): j for j, i in enumerate(device_indices)}
        sub_devices = [self.circuit.devices[int(i)] for i in device_indices]
        # 子块内连接（两端都在子块内）
        sub_connections: list[tuple[str, str, str, str]] = []
        for src, _sp, dst, _dp in self.circuit.connections:
            if src in self.name_to_idx and dst in self.name_to_idx:
                s_idx = self.name_to_idx[src]
                d_idx = self.name_to_idx[dst]
                if s_idx in idx_set and d_idx in idx_set:
                    sub_connections.append((src, _sp, dst, _dp))
        # 子块画布大小（按器件数自适应）
        n_cluster = len(device_indices)
        canvas = max(500.0, np.sqrt(n_cluster) * 80.0)
        return CircuitSpec(
            name=f"{self.circuit.name}_cluster{cluster_id}",
            devices=sub_devices,
            connections=sub_connections,
            canvas_w=canvas,
            canvas_h=canvas,
            benchmark_source=self.circuit.benchmark_source,
            process_node=self.circuit.process_node,
            optical_wavelength_nm=self.circuit.optical_wavelength_nm,
        )

    def _place_intra_cluster(
        self,
        labels: np.ndarray,
    ) -> tuple[dict[str, tuple[float, float]], dict[int, tuple[float, float]]]:
        """块内布局：每个子块用 AnalyticalPlacer 解析法布局。

        修复第70轮：原实现用简单网格布局（功能做一半），现真正调用 AnalyticalPlacer，
        对齐 docstring 声明与 DREAMPlace 分块布局标准流程。

        Args:
            labels: 谱聚类标签数组。

        Returns:
            (final_placement, cluster_centers) 二元组。
            - final_placement: {name: (local_x, local_y)} 块内局部坐标
            - cluster_centers: {cluster_id: (cx, cy)} 子块画布中心
        """
        final_placement: dict[str, tuple[float, float]] = {}
        cluster_centers: dict[int, tuple[float, float]] = {}
        intra_config = self.config.analytical_config or AnalyticalPlacerConfig(
            max_iterations=100,  # 块内迭代数减少（块规模小）
            convergence_threshold=0.5,
        )

        for cluster_id in range(self.k):
            mask = labels == cluster_id
            if not mask.any():
                continue
            cluster_device_indices = np.where(mask)[0]
            n_cluster = len(cluster_device_indices)
            # 小块（<=4 器件）直接网格，避免解析法开销
            if n_cluster <= 4:
                grid_n = int(np.ceil(np.sqrt(n_cluster)))
                canvas = max(200.0, np.sqrt(n_cluster) * 80.0)
                for i, idx in enumerate(cluster_device_indices):
                    name = self.device_names[int(idx)]
                    row = i // grid_n
                    col = i % grid_n
                    x = (col + 0.5) * (canvas / grid_n)
                    y = (row + 0.5) * (canvas / grid_n)
                    final_placement[name] = (x, y)
                cluster_centers[cluster_id] = (canvas / 2, canvas / 2)
                continue
            # 构建子电路并用 AnalyticalPlacer 布局
            sub_circuit = self._build_cluster_subcircuit(
                cluster_id, cluster_device_indices
            )
            placer = AnalyticalPlacer(sub_circuit, intra_config)
            sub_placement = placer.place()
            final_placement.update(sub_placement)
            cluster_centers[cluster_id] = (
                sub_circuit.canvas_w / 2,
                sub_circuit.canvas_h / 2,
            )

        return final_placement, cluster_centers

    def _grid_place_cluster(
        self,
        names: list[str],
        cluster_canvas: float,
        placement: dict[str, tuple[float, float]],
    ) -> None:
        """网格布局小块（≤4 器件，避免解析法开销）。"""
        grid_n = int(np.ceil(np.sqrt(len(names))))
        for i, name in enumerate(names):
            row = i // grid_n
            col = i % grid_n
            x = (col + 0.5) * (cluster_canvas / grid_n)
            y = (row + 0.5) * (cluster_canvas / grid_n)
            placement[name] = (x, y)

    def _analytical_place_cluster(self, ctx: _IntraClusterContext) -> None:
        """用 AnalyticalPlacer 布局单个子块（>4 器件，优化 HPWL）。

        来源: DREAMPlace TCAD 2020，块内解析法布局。
        """
        from polaris.data.specs import CircuitSpec, DeviceSpec

        devices = [
            DeviceSpec(name=name, device_type="generic") for name in ctx.names
        ]
        conns = self._extract_cluster_connections(ctx.cluster_id, ctx.labels)
        sub_circuit = CircuitSpec(
            name=f"{self.circuit.name}_cluster_{ctx.cluster_id}",
            devices=devices,
            connections=conns,
            canvas_w=ctx.cluster_canvas,
            canvas_h=ctx.cluster_canvas,
        )
        intra_config = self.config.analytical_config or AnalyticalPlacerConfig(
            max_iterations=self._adaptive_iterations(len(ctx.names)),
            convergence_threshold=0.5,
        )
        placer = AnalyticalPlacer(sub_circuit, intra_config)
        sub_placement = placer.place()
        for name, (x, y) in sub_placement.items():
            ctx.placement[name] = (x, y)

    @staticmethod
    def _adaptive_iterations(n_cluster: int) -> int:
        """根据子块规模自适应调整迭代数（来源: DREAMPlace TCAD 2020）。"""
        if n_cluster <= 10:
            return 10
        if n_cluster <= 30:
            return 15
        return 20

    def _extract_cluster_connections(
        self, cluster_id: int, labels: np.ndarray
    ) -> list[tuple[str, str, str, str]]:
        """提取子块内连接（仅保留同块器件间的连接）。"""
        conns: list[tuple[str, str, str, str]] = []
        for src, sp, dst, dp in self.circuit.connections:
            if src not in self.name_to_idx or dst not in self.name_to_idx:
                continue
            sc = int(labels[self.name_to_idx[src]])
            dc = int(labels[self.name_to_idx[dst]])
            if sc == cluster_id and dc == cluster_id:
                conns.append((src, sp, dst, dp))
        return conns

    def _build_super_circuit(
        self,
        cluster_centers: dict[int, tuple[float, float]],
        labels: np.ndarray,
    ) -> tuple[CircuitSpec, dict[int, int]]:
        """构建子块级超图电路（每个子块=一个超节点）。

        Args:
            cluster_centers: 子块画布中心字典。
            labels: 谱聚类标签数组。

        Returns:
            (super_circuit, cluster_id_to_idx) 二元组。
        """
        from polaris.data.specs import CircuitSpec, DeviceSpec

        k = len(cluster_centers)
        cluster_ids = sorted(cluster_centers.keys())
        cid2idx = {cid: i for i, cid in enumerate(cluster_ids)}
        super_devices = [
            DeviceSpec(
                name=f"cluster_{cid}",
                device_type="cluster",
                width_um=cluster_centers[cid][0] * 2,
                height_um=cluster_centers[cid][1] * 2,
            )
            for cid in cluster_ids
        ]
        pairs: set[tuple[int, int]] = set()
        for src, _sp, dst, _dp in self.circuit.connections:
            if src in self.name_to_idx and dst in self.name_to_idx:
                sc = int(labels[self.name_to_idx[src]])
                dc = int(labels[self.name_to_idx[dst]])
                if sc != dc:
                    pairs.add((min(sc, dc), max(sc, dc)))
        conns = [
            (f"cluster_{c1}", "out", f"cluster_{c2}", "in")
            for c1, c2 in pairs
            if c1 in cid2idx and c2 in cid2idx
        ]
        canvas = max(2000.0, np.sqrt(k) * 800.0)
        return CircuitSpec(
            name=f"{self.circuit.name}_super",
            devices=super_devices,
            connections=conns,
            canvas_w=canvas,
            canvas_h=canvas,
        ), cid2idx

    def _merge_cluster_placement(
        self,
        ctx: _MergeContext,
    ) -> dict[str, tuple[float, float]]:
        """合并块内坐标与子块中心偏移。

        Args:
            ctx: 合并上下文（含所有必要数据）。

        Returns:
            合并后的全局坐标字典。
        """
        k = len(ctx.cluster_centers)
        k_grid = int(np.ceil(np.sqrt(k)))
        for cluster_id, (local_cx, local_cy) in ctx.cluster_centers.items():
            super_name = f"cluster_{cluster_id}"
            if super_name in ctx.super_placement:
                bcx, bcy = ctx.super_placement[super_name]
                off_x, off_y = bcx - local_cx, bcy - local_cy
            else:
                idx = ctx.cid2idx.get(cluster_id, 0)
                off_x = (idx % k_grid) * (ctx.main_canvas / k_grid)
                off_y = (idx // k_grid) * (ctx.main_canvas / k_grid)
            mask = ctx.labels == cluster_id
            for i in np.where(mask)[0]:
                name = self.device_names[int(i)]
                lx, ly = ctx.placement[name]
                ctx.placement[name] = (lx + off_x, ly + off_y)
        return ctx.placement

    def _place_inter_cluster(
        self,
        placement: dict[str, tuple[float, float]],
        cluster_centers: dict[int, tuple[float, float]],
        labels: np.ndarray,
    ) -> dict[str, tuple[float, float]]:
        """块间布局：用解析法放置子块中心，合并块内坐标。

        修复第70轮：原实现用固定 500μm 网格偏移（功能做一半），
        现构建子块级超图并用 AnalyticalPlacer 放置子块中心，
        对齐 docstring 声明与 DREAMPlace 分块布局标准流程。

        Args:
            placement: 块内局部坐标字典。
            cluster_centers: 子块画布中心字典。
            labels: 谱聚类标签数组。

        Returns:
            合并后的全局坐标字典 {name: (global_x, global_y)}。
        """
        from polaris.data.specs import CircuitSpec, DeviceSpec

        k = len(cluster_centers)
        cluster_ids = sorted(cluster_centers.keys())
        cluster_id_to_idx = {cid: i for i, cid in enumerate(cluster_ids)}
        # 构建子块级超图：每个子块 = 一个超节点
        super_devices: list[DeviceSpec] = []
        for cid in cluster_ids:
            cx, cy = cluster_centers[cid]
            super_devices.append(
                DeviceSpec(
                    name=f"cluster_{cid}",
                    device_type="cluster",
                    width_um=cx * 2,
                    height_um=cy * 2,
                )
            )
        # 超边：子块间连接（每对有连接的子块建一条超边）
        inter_cluster_pairs: set[tuple[int, int]] = set()
        for src, _sp, dst, _dp in self.circuit.connections:
            if src in self.name_to_idx and dst in self.name_to_idx:
                s_idx = self.name_to_idx[src]
                d_idx = self.name_to_idx[dst]
                s_cluster = int(labels[s_idx])
                d_cluster = int(labels[d_idx])
                if s_cluster != d_cluster:
                    inter_cluster_pairs.add(
                        (min(s_cluster, d_cluster), max(s_cluster, d_cluster))
                    )
        super_connections: list[tuple[str, str, str, str]] = [
            (f"cluster_{c1}", "out", f"cluster_{c2}", "in")
            for c1, c2 in inter_cluster_pairs
            if c1 in cluster_id_to_idx and c2 in cluster_id_to_idx
        ]
        # 主画布大小（按子块数自适应）
        main_canvas = max(2000.0, np.sqrt(k) * 800.0)
        super_circuit = CircuitSpec(
            name=f"{self.circuit.name}_super",
            devices=super_devices,
            connections=super_connections,
            canvas_w=main_canvas,
            canvas_h=main_canvas,
        )
        # 用 AnalyticalPlacer 放置子块中心
        inter_config = self.config.analytical_config or AnalyticalPlacerConfig(
            max_iterations=150,
            convergence_threshold=1.0,
        )
        inter_placer = AnalyticalPlacer(super_circuit, inter_config)
        super_placement = inter_placer.place()
        # 合并：块内局部坐标 + 子块中心偏移
        k_grid = int(np.ceil(np.sqrt(k)))
        for cluster_id, (local_cx, local_cy) in cluster_centers.items():
            super_name = f"cluster_{cluster_id}"
            if super_name in super_placement:
                block_cx, block_cy = super_placement[super_name]
                block_offset_x = block_cx - local_cx
                block_offset_y = block_cy - local_cy
            else:
                # 无连接的孤立子块：网格兜底
                idx = cluster_id_to_idx.get(cluster_id, 0)
                row = idx // k_grid
                col = idx % k_grid
                block_offset_x = col * (main_canvas / k_grid)
                block_offset_y = row * (main_canvas / k_grid)
            mask = labels == cluster_id
            for i in np.where(mask)[0]:
                name = self.device_names[int(i)]
                local_x, local_y = placement[name]
                placement[name] = (
                    local_x + block_offset_x,
                    local_y + block_offset_y,
                )
        return placement

    def place(self) -> dict[str, tuple[float, float]]:
        """执行分块布局。

        Returns:
            布局字典 ``{name: (cx, cy)}``。
        """
        if self.n <= self.config.max_cluster_size:
            # 小规模直接用解析法
            return warm_start_placement(self.circuit, self.config.analytical_config)

        # 1. 谱聚类分块
        labels = self._spectral_clustering()

        # 2. 块内布局
        placement, cluster_centers = self._place_intra_cluster(labels)

        # 3. 块间布局 + 合并
        return self._place_inter_cluster(placement, cluster_centers, labels)


def hierarchical_placement(
    circuit: CircuitSpec,
    config: HierarchicalPlacerConfig | None = None,
) -> dict[str, tuple[float, float]]:
    """便捷函数：生成分块布局。

    Args:
        circuit: 电路规格。
        config: 分块配置（None 用默认）。

    Returns:
        布局字典 ``{name: (cx, cy)}``。

    来源:
        Shi & Malik 2000, DREAMPlace TCAD 2020
    """
    placer = HierarchicalPlacer(circuit, config)
    return placer.place()


__all__ = [
    "HierarchicalPlacerConfig",
    "HierarchicalPlacer",
    "hierarchical_placement",
]
