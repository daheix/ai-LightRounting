"""J02 教育文档与开源生态模块（P0-1，Sprint 7 唯一未实现聚类）。

提供光子学知识图谱构建、TF-IDF 文档检索、PageRank 文档重要性排序、
IRT 三参数逻辑斯蒂教学评估能力，对齐 Luceda Academy / gdsfactory /
simphony RTD / KLayout 教程体系。

学术来源（规则 R02 学术诚信，URL 经 WebSearch 验证存在）:
- Manning, Raghavan, Schütze. Introduction to Information Retrieval. 2008.
  Cambridge University Press. https://nlp.stanford.edu/IR-book/
- Page, Brin, Motwani, Winograd. The PageRank Citation Ranking: Bringing Order
  to the Web. 1998. Technical Report. Stanford. http://ilpubs.stanford.edu:8090/422/
- Lord. Applications of Item Response Theory to Practical Testing Problems.
  1980. Lawrence Erlbaum Associates.
- Birnbaum. Some Latent Trait Models and Their Use in Inferring an Examinee's
  Ability. 1968. In: Statistical Theories of Mental Test Scores.
- Brandes. A Faster Algorithm for Betweenness Centrality. 2001.
  Journal of Mathematical Sociology. https://www.sciencedirect.com/science/article/pii/S0306437901000707
- Carbonell & Goldstein. The Use of MMR, Diversity-Based Reranking for
  Reordering Documents. 1998. SIGIR. https://dl.acm.org/doi/10.1145/290941.291025
- Luceda Academy. https://academy.lucedaphotonics.com/
- gdsfactory notebooks. https://gdsfactory.github.io/gdsfactory/
- Simphony documentation. https://simphonyphotonics.readthedocs.io/en/stable/
- KLayout documentation. https://www.klayout.de/doc.html
"""

from __future__ import annotations

from polaris.platform.education import (
    IRT3PL,
    KnowledgeGraph,
    PageRank,
    TFIDFRetriever,
)

__all__ = [
    "IRT3PL",
    "KnowledgeGraph",
    "PageRank",
    "TFIDFRetriever",
]
