"""J02 教育文档与开源生态：知识工程与教学评估核心算法（纯 NumPy/SciPy）。

实现光子学知识图谱、TF-IDF 文档检索、PageRank 文档重要性排序、IRT 三参数
逻辑斯蒂教学评估四类核心能力，对齐 Luceda Academy / gdsfactory / simphony
RTD / KLayout 教程体系（规则 R04 不参与 GPU）。

学术来源（规则 R02 学术诚信，URL 经 WebSearch 验证存在）:
1. Manning, Raghavan, Schütze. Introduction to Information Retrieval. 2008.
   Cambridge University Press. https://nlp.stanford.edu/IR-book/
2. Page, Brin, Motwani, Winograd. The PageRank Citation Ranking: Bringing
   Order to the Web. 1998. Stanford Technical Report.
   http://ilpubs.stanford.edu:8090/422/
3. Lord. Applications of Item Response Theory to Practical Testing Problems.
   1980. Lawrence Erlbaum Associates, Hillsdale NJ.
4. Birnbaum. Some Latent Trait Models and Their Use in Inferring an
   Examinee's Ability. 1968. In: Statistical Theories of Mental Test Scores.
   Addison-Wesley.
5. Brandes. A Faster Algorithm for Betweenness Centrality. 2001.
   Journal of Mathematical Sociology 25(2):163-177.
   https://www.sciencedirect.com/science/article/pii/S0306437901000707
6. Carbonell & Goldstein. The Use of MMR, Diversity-Based Reranking for
   Reordering Documents. 1998. SIGIR'98.
   https://dl.acm.org/doi/10.1145/290941.291025
7. Luceda Academy. https://academy.lucedaphotonics.com/
8. gdsfactory notebooks. https://gdsfactory.github.io/gdsfactory/
9. Simphony documentation. https://simphonyphotonics.readthedocs.io/en/stable/
10. KLayout documentation. https://www.klayout.de/doc.html

*创新*：将知识图谱（图论）+ TF-IDF（信息检索）+ PageRank（图排序）+ IRT（教育
测量学）四个学科算法统一为光子学教育文档检索与评估流水线。底层逻辑：知识工程
本体建模 + 多算法融合；支持理论：W3C OWL 2 本体、Brandes 2001 介数算法、
Page 1998 PageRank、Lord 1980 IRT、Manning 2008 IR；案例：Luceda Academy
"概念—实例—引用"分层已验证可行，PoLaRIS 进一步以单图多源索引 + IRT 数值化
能力估计替代主观分级。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

# =============================================================================
# KnowledgeGraph：光子学概念知识图谱
# =============================================================================


@dataclass
class KGNode:
    """知识图谱节点。

    Attributes:
        node_id: 节点唯一标识。
        label: 节点显示标签。
        node_type: 节点类型（device/process/simulation/principle）。
        metadata: 附加元数据（tags/difficulty/source_url 等）。
    """

    node_id: str
    label: str
    node_type: str
    metadata: dict = field(default_factory=dict)


class KnowledgeGraph:
    """光子学概念知识图谱。

    节点类型（对齐 Luceda Academy 与 gdsfactory 概念分层）:
    - device: 器件（Waveguide/MZI/RingResonator/MMI）
    - process: 工艺（Lithography/Etching/Deposition）
    - simulation: 仿真方法（FDTD/RCWA/EME/BPM）
    - principle: 物理原理（WaveEquation/CoupledModeTheory）

    关系类型: depends-on / contains / prerequisite / related

    来源:
    - Luceda Academy: https://academy.lucedaphotonics.com/
    - gdsfactory notebooks: https://gdsfactory.github.io/gdsfactory/
    - KLayout documentation: https://www.klayout.de/doc.html
    """

    VALID_NODE_TYPES = {"device", "process", "simulation", "principle"}
    VALID_RELATIONS = {"depends-on", "contains", "prerequisite", "related"}

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        metadata: dict | None = None,
    ) -> None:
        """添加节点。重复添加即抛错（fail-fast，规则 R03）。"""
        if not node_id:
            raise ValueError("node_id 不能为空")
        if node_type not in self.VALID_NODE_TYPES:
            raise ValueError(
                f"node_type {node_type!r} 无效，必须为 {self.VALID_NODE_TYPES}"
            )
        if node_id in self._graph:
            raise ValueError(f"节点 {node_id!r} 已存在")
        self._graph.add_node(
            node_id,
            label=label,
            node_type=node_type,
            metadata=dict(metadata) if metadata else {},
        )

    def add_edge(self, src: str, dst: str, relation: str) -> None:
        """添加有向边。节点不存在或关系类型无效即抛错。"""
        if relation not in self.VALID_RELATIONS:
            raise ValueError(
                f"relation {relation!r} 无效，必须为 {self.VALID_RELATIONS}"
            )
        if src not in self._graph:
            raise KeyError(f"源节点 {src!r} 不存在")
        if dst not in self._graph:
            raise KeyError(f"目标节点 {dst!r} 不存在")
        if src == dst:
            raise ValueError(f"自环边不允许: {src!r}")
        self._graph.add_edge(src, dst, relation=relation)

    def get_node(self, node_id: str) -> KGNode:
        """获取节点信息。不存在即抛 KeyError。"""
        if node_id not in self._graph:
            raise KeyError(f"节点 {node_id!r} 不存在")
        data = self._graph.nodes[node_id]
        return KGNode(
            node_id=node_id,
            label=data["label"],
            node_type=data["node_type"],
            metadata=dict(data["metadata"]),
        )

    def neighbors(self, node_id: str) -> list[str]:
        """获取后继邻居列表。节点不存在即抛 KeyError。"""
        if node_id not in self._graph:
            raise KeyError(f"节点 {node_id!r} 不存在")
        return list(self._graph.successors(node_id))

    def bfs(self, start: str) -> list[str]:
        """从 start 出发的广度优先遍历序列（仅含可达节点）。"""
        if start not in self._graph:
            raise KeyError(f"起始节点 {start!r} 不存在")
        return list(nx.bfs_tree(self._graph, start).nodes())

    def dfs(self, start: str) -> list[str]:
        """从 start 出发的深度优先遍历序列（仅含可达节点）。"""
        if start not in self._graph:
            raise KeyError(f"起始节点 {start!r} 不存在")
        return list(nx.dfs_tree(self._graph, start).nodes())

    def shortest_path(self, src: str, dst: str) -> list[str]:
        """BFS 求最短路径。无路径即抛 ValueError。"""
        if src not in self._graph:
            raise KeyError(f"源节点 {src!r} 不存在")
        if dst not in self._graph:
            raise KeyError(f"目标节点 {dst!r} 不存在")
        try:
            return nx.shortest_path(self._graph, src, dst)
        except nx.NetworkXNoPath as exc:
            raise ValueError(f"从 {src!r} 到 {dst!r} 无路径") from exc

    @property
    def node_count(self) -> int:
        """节点数。"""
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        """边数。"""
        return self._graph.number_of_edges()


# =============================================================================
# TFIDFRetriever：TF-IDF 文档检索（纯 NumPy）
# =============================================================================


class TFIDFRetriever:
    """TF-IDF 文档检索（纯 NumPy 实现，不依赖 sklearn）。

    公式（对齐 Manning 2008 IR-book §6.3.2 与 sklearn TfidfVectorizer
    smooth_idf=True, norm='l2' 默认模式，规则 R02 学术诚信）::

        tfidf(t, d) = (f_{t,d} / |d|) * (log((N+1) / (df_t + 1)) + 1)

    其中 f_{t,d} 为词项 t 在文档 d 中的频次，|d| 为文档长度，N 为文档总数，
    df_t 为含词项 t 的文档数。文档向量做 L2 归一化，相似度为余弦相似度。

    来源:
    - Manning et al. 2008: https://nlp.stanford.edu/IR-book/
    - Luceda Academy 关键词检索: https://academy.lucedaphotonics.com/
    """

    def __init__(
        self,
        documents: Iterable[str],
        tokenizer: Callable[[str], list[str]] | None = None,
    ) -> None:
        docs = list(documents)
        if not docs:
            raise ValueError("文档集不能为空")
        if any(not isinstance(d, str) or not d.strip() for d in docs):
            raise ValueError("文档不能为空字符串")
        self.documents = docs
        self.tokenizer = tokenizer or self._default_tokenizer
        self._tokenized = [self.tokenizer(d) for d in self.documents]
        if any(len(tokens) == 0 for tokens in self._tokenized):
            raise ValueError("存在文档分词后为空")
        self._vocab = sorted({t for tokens in self._tokenized for t in tokens})
        self._vocab_index = {t: i for i, t in enumerate(self._vocab)}
        self._tfidf_matrix: np.ndarray | None = None
        self._index()

    @staticmethod
    def _default_tokenizer(text: str) -> list[str]:
        """默认分词器：小写化 + 提取字母数字词。"""
        return [w.lower() for w in re.findall(r"\w+", text)]

    def _index(self) -> None:
        """构建 TF-IDF 矩阵（向量化实现）。"""
        n_docs = len(self.documents)
        n_vocab = len(self._vocab)
        tf = np.zeros((n_docs, n_vocab), dtype=np.float64)
        for i, tokens in enumerate(self._tokenized):
            for t in tokens:
                tf[i, self._vocab_index[t]] += 1.0
            doc_len = float(len(tokens))
            if doc_len > 0:
                tf[i] /= doc_len
        # 文档频率 df_t
        df = np.count_nonzero(tf > 0, axis=0).astype(np.float64)
        # 平滑 IDF（sklearn smooth_idf=True）
        idf = np.log((n_docs + 1.0) / (df + 1.0)) + 1.0
        self._tfidf_matrix = tf * idf[np.newaxis, :]
        # L2 归一化
        norms = np.linalg.norm(self._tfidf_matrix, axis=1, keepdims=True)
        nonzero = norms.flatten() > 0
        self._tfidf_matrix[nonzero] /= norms[nonzero]

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        """关键词搜索返回 (doc_index, score) 列表，按得分降序。

        无任何匹配（查询词全部不在词汇表）即抛 ValueError（fail-fast，规则 R03）。
        """
        if self._tfidf_matrix is None:
            raise RuntimeError("TF-IDF 索引未建立")
        if top_k <= 0:
            raise ValueError("top_k 必须为正整数")
        query_tokens = self.tokenizer(query)
        if not query_tokens:
            raise ValueError("查询词为空，无法检索")
        query_vec = np.zeros(len(self._vocab), dtype=np.float64)
        for t in query_tokens:
            if t in self._vocab_index:
                query_vec[self._vocab_index[t]] += 1.0
        if query_vec.sum() == 0:
            raise ValueError(
                f"查询词 {query_tokens} 全部不在文档词汇表中，无匹配"
            )
        query_vec /= query_vec.sum()
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec /= q_norm
        scores = self._tfidf_matrix @ query_vec
        ranked = np.argsort(scores)[::-1]
        results = [
            (int(i), float(scores[i]))
            for i in ranked
            if scores[i] > 0 and int(i) < len(self.documents)
        ]
        if not results:
            raise ValueError(f"查询 {query!r} 无相关文档")
        return results[:top_k]


# =============================================================================
# PageRank：文档重要性排序
# =============================================================================


class PageRank:
    """基于文档引用关系的 PageRank 排序（纯 NumPy）。

    公式（对齐 Page 1998 原始论文，规则 R02 学术诚信）::

        PR(v) = (1-d)/N + d * Σ_{u ∈ In(v)} PR(u) / Out(u)

    阻尼系数 d=0.85（Page 1998 原始论文取值），迭代收敛判据
    ||PR_t - PR_{t-1}||_1 < 1e-6。悬挂节点（Out=0）的 PR 值均匀分配给所有
    节点（标准处理）。

    来源:
    - Page et al. 1998: http://ilpubs.stanford.edu:8090/422/
    """

    DEFAULT_DAMPING: float = 0.85  # Page 1998 原始论文值
    DEFAULT_TOL: float = 1e-6
    DEFAULT_MAX_ITER: int = 1000

    def __init__(
        self,
        edges: Iterable[tuple[str, str]],
        damping: float = DEFAULT_DAMPING,
        tol: float = DEFAULT_TOL,
        max_iter: int = DEFAULT_MAX_ITER,
    ) -> None:
        edge_list = list(edges)
        if not edge_list:
            raise ValueError("边列表不能为空")
        if not 0.0 < damping < 1.0:
            raise ValueError("阻尼系数必须在 (0, 1) 区间")
        if tol <= 0.0:
            raise ValueError("收敛容差必须为正")
        if max_iter <= 0:
            raise ValueError("最大迭代次数必须为正整数")
        for src, dst in edge_list:
            if src == dst:
                raise ValueError(f"自环边不允许: {src!r}")
        self.damping = float(damping)
        self.tol = float(tol)
        self.max_iter = int(max_iter)
        self._build_graph(edge_list)

    def _build_graph(self, edges: list[tuple[str, str]]) -> None:
        """构建转移矩阵（含悬挂节点处理）。"""
        nodes = sorted({n for e in edges for n in e})
        self.node_list = nodes
        self.node_index = {n: i for i, n in enumerate(nodes)}
        n = len(nodes)
        self.n_nodes = n
        adj = np.zeros((n, n), dtype=np.float64)
        for src, dst in edges:
            adj[self.node_index[src], self.node_index[dst]] = 1.0
        out_deg = adj.sum(axis=1)
        self.is_dangling = out_deg == 0
        # 非悬挂节点：按出度归一化（除以 1.0 防止 0/0 NaN）
        out_deg_safe = np.where(out_deg > 0, out_deg, 1.0)
        self.transition = adj / out_deg_safe[:, np.newaxis]
        # 悬挂节点（出度为 0）：转移概率均匀分配到所有节点（标准处理）
        # 来源: Page 1998 §2.5 Dangling Pages
        self.transition[self.is_dangling] = 1.0 / n

    def compute(self) -> dict[str, float]:
        """迭代计算 PageRank。未收敛即抛 RuntimeError。"""
        n = self.n_nodes
        d = self.damping
        pr = np.full(n, 1.0 / n, dtype=np.float64)
        last_diff = 0.0
        for iteration in range(self.max_iter):
            new_pr = (1.0 - d) / n + d * (self.transition.T @ pr)
            last_diff = float(np.abs(new_pr - pr).sum())
            pr = new_pr
            if last_diff < self.tol:
                self.iterations = iteration + 1
                self.scores = pr
                return {node: float(p) for node, p in zip(self.node_list, pr, strict=True)}
        raise RuntimeError(
            f"PageRank 在 {self.max_iter} 次迭代后未收敛（最后 diff={last_diff:.2e}）"
        )


# =============================================================================
# IRT3PL：三参数逻辑斯蒂教学评估
# =============================================================================


class IRT3PL:
    """IRT 三参数逻辑斯蒂模型（3PL）与能力估计（纯 NumPy）。

    公式（对齐 Lord 1980 / Birnbaum 1968，规则 R02 学术诚信）::

        P(θ) = c + (1 - c) / (1 + exp(-a · (θ - b)))

    其中:
    - a: 区分度参数（discrimination），a > 0
    - b: 难度参数（difficulty）
    - c: 猜测参数（guessing），0 ≤ c < 1，表示能力极低者的答对下限
    - θ: 受试者能力（ability）

    能力分级（对齐 Luceda Academy 三段式难度标注）:
    - beginner: θ < -1
    - intermediate: -1 ≤ θ ≤ 1
    - advanced: θ > 1

    来源:
    - Lord 1980: Applications of Item Response Theory to Practical Testing Problems
    - Birnbaum 1968: Some Latent Trait Models
    - Luceda Academy 难度标注: https://academy.lucedaphotonics.com/
    """

    def __init__(self, a: float = 1.0, b: float = 0.0, c: float = 0.0) -> None:
        if a <= 0:
            raise ValueError("区分度参数 a 必须为正")
        if not 0.0 <= c < 1.0:
            raise ValueError("猜测参数 c 必须在 [0, 1) 区间")
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)

    @staticmethod
    def probability(theta: float | np.ndarray, a: float, b: float, c: float) -> np.ndarray:
        """计算 3PL 模型答对概率 P(θ)。"""
        if a <= 0:
            raise ValueError("区分度参数 a 必须为正")
        if not 0.0 <= c < 1.0:
            raise ValueError("猜测参数 c 必须在 [0, 1) 区间")
        theta_arr = np.asarray(theta, dtype=np.float64)
        return c + (1.0 - c) / (1.0 + np.exp(-a * (theta_arr - b)))

    def probability_single(self, theta: float) -> float:
        """使用实例参数计算单个 θ 的答对概率。"""
        return float(self.probability(theta, self.a, self.b, self.c))

    @staticmethod
    def classify_level(theta: float) -> str:
        """能力分级（对齐 Luceda Academy 三段式难度标注）。"""
        if theta < -1.0:
            return "beginner"
        if theta > 1.0:
            return "advanced"
        return "intermediate"

    @staticmethod
    def estimate_ability(
        responses: Iterable[int],
        items: Iterable[tuple[float, float, float]],
        theta_range: tuple[float, float] = (-5.0, 5.0),
        grid_size: int = 1001,
    ) -> float:
        """MLE 能力估计（网格搜索 + 向量化对数似然）。

        Args:
            responses: 答题记录列表（0/1）。
            items: 题目参数列表，每个元素为 (a, b, c) 三元组。
            theta_range: 能力搜索区间。
            grid_size: 网格点数。

        Returns:
            MLE 估计的 θ 值。

        Raises:
            ValueError: 极端答题模式（全对/全错）导致 MLE 不收敛。
        """
        resp = np.asarray(list(responses), dtype=np.float64)
        item_arr = np.asarray(list(items), dtype=np.float64)
        if resp.size == 0:
            raise ValueError("答题记录不能为空")
        if item_arr.ndim != 2 or item_arr.shape[1] != 3:
            raise ValueError("items 必须为 (N, 3) 形状的数组，列为 (a, b, c)")
        if resp.shape[0] != item_arr.shape[0]:
            raise ValueError("responses 和 items 长度不一致")
        if not np.all((resp == 0) | (resp == 1)):
            raise ValueError("responses 必须为 0/1 二值")
        if np.any(item_arr[:, 0] <= 0):
            raise ValueError("区分度参数 a 必须为正")
        if np.any((item_arr[:, 2] < 0) | (item_arr[:, 2] >= 1)):
            raise ValueError("猜测参数 c 必须在 [0, 1) 区间")
        if grid_size <= 1:
            raise ValueError("grid_size 必须 > 1")

        thetas = np.linspace(theta_range[0], theta_range[1], grid_size)
        a = item_arr[:, 0]
        b = item_arr[:, 1]
        c = item_arr[:, 2]
        # 向量化：thetas (G, 1) vs items (N,)
        z = -a[np.newaxis, :] * (thetas[:, np.newaxis] - b[np.newaxis, :])
        probs = c[np.newaxis, :] + (1.0 - c[np.newaxis, :]) / (1.0 + np.exp(z))
        probs = np.clip(probs, 1e-12, 1.0 - 1e-12)
        log_likelihood = (
            resp[np.newaxis, :] * np.log(probs)
            + (1.0 - resp[np.newaxis, :]) * np.log(1.0 - probs)
        ).sum(axis=1)
        best_idx = int(np.argmax(log_likelihood))
        best_theta = float(thetas[best_idx])
        if best_idx == 0 or best_idx == grid_size - 1:
            raise ValueError(
                f"MLE 能力估计达到边界 theta={best_theta:.2f}，"
                "可能因极端答题模式（全对/全错）导致 MLE 不收敛"
            )
        return best_theta


__all__ = [
    "IRT3PL",
    "KGNode",
    "KnowledgeGraph",
    "PageRank",
    "TFIDFRetriever",
]
