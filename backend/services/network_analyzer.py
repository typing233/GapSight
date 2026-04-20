import networkx as nx
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
import itertools
import math

from backend.models.schemas import (
    Paper, Entity, Node, Edge, GapPair, 
    NetworkData, GapPromptRequest, GapPromptResponse
)


class NetworkAnalyzer:
    def __init__(self):
        self.G = None
        self.entities = {}
        self.papers = []
        self.keywords = []

    def build_network(
        self,
        papers: List[Paper],
        entities: Dict[str, Entity],
        cooccurrence_matrix: Dict[str, Dict[str, int]],
        keywords: List[str]
    ) -> nx.Graph:
        self.papers = papers
        self.entities = entities
        self.keywords = keywords
        
        G = nx.Graph()
        
        for entity_name, entity in entities.items():
            G.add_node(
                entity_name,
                count=entity.count,
                papers=entity.papers,
                size=max(5, min(30, entity.count * 2))
            )
        
        for e1, connections in cooccurrence_matrix.items():
            for e2, weight in connections.items():
                if e1 in G.nodes and e2 in G.nodes:
                    G.add_edge(e1, e2, weight=weight)
        
        self.G = G
        return G

    def calculate_centrality_metrics(self) -> Dict[str, Dict[str, float]]:
        if self.G is None or len(self.G.nodes) == 0:
            return {}
        
        metrics = {}
        
        if len(self.G.nodes) > 1:
            betweenness = nx.betweenness_centrality(
                self.G, 
                weight='weight',
                normalized=True
            )
        else:
            betweenness = {node: 0.0 for node in self.G.nodes}
        
        try:
            constraint = nx.constraint(self.G, weight='weight')
        except Exception:
            constraint = {}
        
        try:
            effective_size = nx.effective_size(self.G, weight='weight')
        except Exception:
            effective_size = {}
        
        for node in self.G.nodes:
            b = betweenness.get(node, 0.0)
            c = constraint.get(node, 0.5)
            es = effective_size.get(node, 1.0)
            
            if math.isnan(b) or not math.isfinite(b):
                b = 0.0
            if math.isnan(c) or not math.isfinite(c):
                c = 0.5
            if math.isnan(es) or not math.isfinite(es):
                es = 1.0
            
            metrics[node] = {
                'betweenness_centrality': b,
                'constraint': c,
                'effective_size': es
            }
        
        return metrics

    def detect_communities(self) -> Dict[str, int]:
        if self.G is None or len(self.G.nodes) < 2:
            return {node: 0 for node in self.G.nodes}
        
        try:
            communities = nx.community.louvain_communities(
                self.G, 
                weight='weight',
                seed=42
            )
        except Exception:
            try:
                communities = nx.community.greedy_modularity_communities(
                    self.G, 
                    weight='weight'
                )
            except Exception:
                return {node: 0 for node in self.G.nodes}
        
        community_map = {}
        for i, community in enumerate(communities):
            for node in community:
                community_map[node] = i
        
        return community_map

    def detect_gap_pairs(
        self,
        metrics: Dict[str, Dict[str, float]],
        communities: Dict[str, int],
        max_pairs: int = 20
    ) -> List[GapPair]:
        if self.G is None:
            return []
        
        all_nodes = list(self.G.nodes)
        if len(all_nodes) < 2:
            return []
        
        gap_candidates = []
        
        community_nodes = defaultdict(list)
        for node, comm_id in communities.items():
            community_nodes[comm_id].append(node)
        
        if len(community_nodes) >= 2:
            comm_ids = list(community_nodes.keys())
            for i in range(len(comm_ids)):
                for j in range(i + 1, len(comm_ids)):
                    comm1_nodes = community_nodes[comm_ids[i]]
                    comm2_nodes = community_nodes[comm_ids[j]]
                    
                    for n1 in comm1_nodes:
                        for n2 in comm2_nodes:
                            if not self.G.has_edge(n1, n2):
                                score = self._calculate_gap_score(n1, n2, metrics)
                                gap_candidates.append((n1, n2, score, "跨社区概念对，未建立共现连接"))
        
        if len(gap_candidates) < max_pairs:
            high_betweenness_nodes = [
                node for node in all_nodes
                if metrics.get(node, {}).get('betweenness_centrality', 0) > 0.1
            ]
            
            if len(high_betweenness_nodes) >= 2:
                for n1, n2 in itertools.combinations(high_betweenness_nodes, 2):
                    if not self.G.has_edge(n1, n2):
                        score = self._calculate_gap_score(n1, n2, metrics)
                        if (n1, n2, score, "高中介中心性节点对，存在桥接潜力") not in gap_candidates:
                            gap_candidates.append((n1, n2, score, "高中介中心性节点对，存在桥接潜力"))
        
        if len(gap_candidates) < max_pairs:
            for n1, n2 in itertools.combinations(all_nodes, 2):
                if not self.G.has_edge(n1, n2):
                    score = self._calculate_gap_score(n1, n2, metrics)
                    if score > 0.3:
                        exists = any(
                            (pair[0] == n1 and pair[1] == n2) or
                            (pair[0] == n2 and pair[1] == n1)
                            for pair in gap_candidates
                        )
                        if not exists:
                            gap_candidates.append((n1, n2, score, "潜在知识盲区，两个概念尚未建立学术关联"))
        
        gap_candidates.sort(key=lambda x: x[2], reverse=True)
        
        gap_pairs = []
        seen_pairs = set()
        
        for n1, n2, score, reason in gap_candidates[:max_pairs]:
            pair_key = tuple(sorted([n1, n2]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            
            prompt = self._generate_gap_prompt(n1, n2, reason)
            
            gap_pairs.append(GapPair(
                concept1=n1,
                concept2=n2,
                score=score,
                reason=reason,
                prompt=prompt
            ))
        
        return gap_pairs

    def _calculate_gap_score(
        self,
        node1: str,
        node2: str,
        metrics: Dict[str, Dict[str, float]]
    ) -> float:
        if self.G is None:
            return 0.0
        
        score = 0.0
        
        metric1 = metrics.get(node1, {})
        metric2 = metrics.get(node2, {})
        
        betweenness1 = metric1.get('betweenness_centrality', 0)
        betweenness2 = metric2.get('betweenness_centrality', 0)
        if betweenness1 is None or math.isnan(betweenness1) or not math.isfinite(betweenness1):
            betweenness1 = 0.0
        if betweenness2 is None or math.isnan(betweenness2) or not math.isfinite(betweenness2):
            betweenness2 = 0.0
        score += (betweenness1 + betweenness2) * 0.4
        
        constraint1 = metric1.get('constraint', 0.5)
        constraint2 = metric2.get('constraint', 0.5)
        if constraint1 is None or math.isnan(constraint1) or not math.isfinite(constraint1):
            constraint1 = 0.5
        if constraint2 is None or math.isnan(constraint2) or not math.isfinite(constraint2):
            constraint2 = 0.5
        avg_constraint = (constraint1 + constraint2) / 2
        score += (1 - avg_constraint) * 0.3
        
        if node1 in self.G.nodes and node2 in self.G.nodes:
            degree1 = self.G.degree(node1)
            degree2 = self.G.degree(node2)
            degrees = [self.G.degree(n) for n in self.G.nodes] if self.G.nodes else [1]
            max_degree = max(degrees) if degrees else 1
            avg_degree = (degree1 + degree2) / (2 * max_degree) if max_degree > 0 else 0
            score += avg_degree * 0.3
        
        if math.isnan(score) or not math.isfinite(score):
            return 0.0
        
        return min(1.0, max(0.0, score))

    def _generate_gap_prompt(self, concept1: str, concept2: str, reason: str) -> str:
        keyword_str = ", ".join(self.keywords) if self.keywords else "相关领域"
        
        templates = [
            f"基于关键词 '{keyword_str}' 的研究背景，探索 '{concept1}' 与 '{concept2}' 之间的潜在关联。{reason}。建议研究方向：1) 调查 '{concept1}' 的技术方法如何应用于 '{concept2}' 的研究问题；2) 分析两个领域在方法论上的互补性；3) 探索跨领域融合可能产生的新理论或技术突破。",
            f"在 '{keyword_str}' 研究领域中，'{concept1}' 和 '{concept2}' 是两个独立发展的研究方向。{reason}。潜在创新点：1) 将 '{concept1}' 的理论框架扩展到 '{concept2}' 问题域；2) 开发整合两种方法的混合模型；3) 识别两个领域共有的科学问题并提出统一解决方案。",
            f"研究空白分析：'{concept1}' 与 '{concept2}' 之间缺乏学术连接。{reason}。建议开题方向：1) 系统性综述两个领域的研究进展，识别交叉点；2) 设计验证性实验检验跨领域假设；3) 开发促进两个领域知识迁移的方法论框架。"
        ]
        
        return templates[hash(concept1 + concept2) % len(templates)]

    def generate_network_data(
        self,
        keywords: List[str]
    ) -> NetworkData:
        if self.G is None:
            return NetworkData(
                nodes=[],
                edges=[],
                gap_pairs=[],
                papers=self.papers,
                total_papers=len(self.papers),
                total_entities=0
            )
        
        self.keywords = keywords
        
        metrics = self.calculate_centrality_metrics()
        communities = self.detect_communities()
        gap_pairs = self.detect_gap_pairs(metrics, communities)
        
        def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
            if value is None:
                return default
            if isinstance(value, float):
                if math.isnan(value) or not math.isfinite(value):
                    return default
                return value
            return float(value) if isinstance(value, (int, float)) else default
        
        nodes = []
        for node_name in self.G.nodes:
            node_data = self.G.nodes[node_name]
            metric = metrics.get(node_name, {})
            
            nodes.append(Node(
                id=node_name,
                label=node_name,
                size=node_data.get('size', 10),
                group=communities.get(node_name, 0),
                betweenness_centrality=_safe_float(metric.get('betweenness_centrality')),
                constraint=_safe_float(metric.get('constraint')),
                effective_size=_safe_float(metric.get('effective_size'))
            ))
        
        edges = []
        for u, v, data in self.G.edges(data=True):
            edges.append(Edge(
                source=u,
                target=v,
                weight=data.get('weight', 1),
                is_gap=False
            ))
        
        for gap in gap_pairs:
            edges.append(Edge(
                source=gap.concept1,
                target=gap.concept2,
                weight=1,
                is_gap=True
            ))
        
        return NetworkData(
            nodes=nodes,
            edges=edges,
            gap_pairs=gap_pairs,
            papers=self.papers,
            total_papers=len(self.papers),
            total_entities=len(self.entities)
        )

    def generate_gap_prompt_response(
        self,
        request: GapPromptRequest
    ) -> GapPromptResponse:
        concept1 = request.concept1
        concept2 = request.concept2
        keywords = request.keywords
        papers = request.papers
        
        keyword_str = ", ".join(keywords) if keywords else "相关研究领域"
        
        paper_titles = [p.title for p in papers[:5] if p.title]
        
        research_directions = [
            f"探索 '{concept1}' 的方法在 '{concept2}' 问题域中的适用性和局限性",
            f"开发整合 '{concept1}' 与 '{concept2}' 技术的创新框架",
            f"系统性综述两个领域的研究进展，识别关键交叉点和挑战",
            f"设计验证性实验检验跨领域假设的可行性",
            f"建立两个领域之间的知识迁移方法论"
        ]
        
        papers_context = ""
        if paper_titles:
            papers_context = f"\n\n相关文献背景：\n" + "\n".join([f"- {title}" for title in paper_titles])
        
        prompt = f"""
研究空白分析报告

关键词：{keyword_str}
潜在创新连接：{concept1} ↔ {concept2}

## 研究背景
在 '{keyword_str}' 领域中，'{concept1}' 和 '{concept2}' 是两个具有重要研究价值的概念。通过文献共现网络分析发现，这两个概念之间缺乏直接的学术关联，存在知识盲区。

## 潜在创新价值
1. 理论层面：两个领域的理论融合可能产生新的研究视角和理论框架
2. 方法层面：跨领域方法迁移可能解决单一领域难以处理的问题
3. 应用层面：技术整合可能开辟新的应用场景和研究方向{papers_context}

## 建议研究方向
""" + "\n".join([f"{i+1}. {direction}" for i, direction in enumerate(research_directions)]) + f"""

## 开题建议
建议从以下角度切入：
- 从方法学角度：分析两个领域在研究方法上的互补性
- 从问题驱动角度：寻找两个领域共同关注的科学问题
- 从技术融合角度：探索技术整合的可行性和潜在效益
"""
        
        return GapPromptResponse(
            prompt=prompt.strip(),
            concept1=concept1,
            concept2=concept2,
            research_directions=research_directions
        )


network_analyzer = NetworkAnalyzer()
