import uuid
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime
import math
import statistics

from backend.models.schemas import (
    DataSnapshot, ComparisonResult, ComparisonDimension,
    AnomalyPoint, Node, Edge, GapPair
)


class DataComparator:
    def __init__(self):
        self.snapshots: Dict[str, DataSnapshot] = {}

    def save_snapshot(self, snapshot: DataSnapshot) -> DataSnapshot:
        if snapshot.id is None:
            snapshot.id = str(uuid.uuid4())
        if snapshot.created_at is None:
            snapshot.created_at = datetime.now()
        self.snapshots[snapshot.id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[DataSnapshot]:
        return self.snapshots.get(snapshot_id)

    def list_snapshots(self) -> List[DataSnapshot]:
        return list(self.snapshots.values())

    def delete_snapshot(self, snapshot_id: str) -> bool:
        if snapshot_id in self.snapshots:
            del self.snapshots[snapshot_id]
            return True
        return False

    def compare_snapshots(
        self,
        snapshot_ids: List[str],
        dimensions: Optional[List[ComparisonDimension]] = None
    ) -> ComparisonResult:
        if dimensions is None:
            dimensions = [
                ComparisonDimension.NODE_COUNT,
                ComparisonDimension.EDGE_COUNT,
                ComparisonDimension.GAP_COUNT,
                ComparisonDimension.TOP_ENTITIES,
                ComparisonDimension.CENTRALITY_DISTRIBUTION,
                ComparisonDimension.GAP_SCORE_DISTRIBUTION
            ]

        snapshots = []
        for sid in snapshot_ids:
            snapshot = self.get_snapshot(sid)
            if snapshot:
                snapshots.append(snapshot)

        if len(snapshots) < 2:
            raise ValueError("需要至少两个快照进行比较")

        snapshot_names = [s.name for s in snapshots]
        anomalies = []

        node_comparison = self._compare_nodes(snapshots)
        edge_comparison = self._compare_edges(snapshots)
        gap_comparison = self._compare_gaps(snapshots)

        if ComparisonDimension.NODE_COUNT in dimensions:
            node_anomalies = self._detect_count_anomalies(
                snapshots, "node_count", [len(s.nodes) for s in snapshots]
            )
            anomalies.extend(node_anomalies)

        if ComparisonDimension.EDGE_COUNT in dimensions:
            edge_anomalies = self._detect_count_anomalies(
                snapshots, "edge_count", [len(s.edges) for s in snapshots]
            )
            anomalies.extend(edge_anomalies)

        if ComparisonDimension.GAP_COUNT in dimensions:
            gap_anomalies = self._detect_count_anomalies(
                snapshots, "gap_count", [len(s.gap_pairs) for s in snapshots]
            )
            anomalies.extend(gap_anomalies)

        if ComparisonDimension.TOP_ENTITIES in dimensions:
            entity_anomalies = self._detect_entity_anomalies(snapshots)
            anomalies.extend(entity_anomalies)

        summary = self._generate_comparison_summary(snapshots, anomalies, dimensions)

        return ComparisonResult(
            snapshot_ids=snapshot_ids,
            snapshot_names=snapshot_names,
            comparison_time=datetime.now(),
            dimensions=dimensions,
            node_comparison=node_comparison,
            edge_comparison=edge_comparison,
            gap_comparison=gap_comparison,
            anomalies=anomalies,
            summary=summary
        )

    def _compare_nodes(self, snapshots: List[DataSnapshot]) -> Dict[str, Dict[str, Any]]:
        all_nodes = set()
        node_snapshot_map: Dict[str, List[bool]] = defaultdict(lambda: [False] * len(snapshots))
        node_data: Dict[str, Dict[str, Any]] = {}

        for i, snapshot in enumerate(snapshots):
            for node in snapshot.nodes:
                all_nodes.add(node.id)
                node_snapshot_map[node.id][i] = True
                if node.id not in node_data:
                    node_data[node.id] = {
                        'label': node.label,
                        'snapshots': [],
                        'size_variation': [],
                        'centrality_variation': []
                    }
                node_data[node.id]['snapshots'].append(snapshot.name)
                node_data[node.id]['size_variation'].append(node.size)
                if node.betweenness_centrality is not None:
                    node_data[node.id]['centrality_variation'].append(node.betweenness_centrality)

        result = {}
        for node_id in all_nodes:
            presence = node_snapshot_map[node_id]
            is_common = all(presence)
            is_unique = sum(presence) == 1

            data = node_data[node_id]
            sizes = data.get('size_variation', [])
            centralities = data.get('centrality_variation', [])

            result[node_id] = {
                'label': data.get('label', node_id),
                'is_common': is_common,
                'is_unique': is_unique,
                'present_in': [snapshots[i].name for i, p in enumerate(presence) if p],
                'absent_in': [snapshots[i].name for i, p in enumerate(presence) if not p],
                'size_variation': {
                    'values': sizes,
                    'mean': statistics.mean(sizes) if sizes else 0,
                    'std': statistics.stdev(sizes) if len(sizes) > 1 else 0,
                    'min': min(sizes) if sizes else 0,
                    'max': max(sizes) if sizes else 0
                },
                'centrality_variation': {
                    'values': centralities,
                    'mean': statistics.mean(centralities) if centralities else 0,
                    'std': statistics.stdev(centralities) if len(centralities) > 1 else 0,
                    'min': min(centralities) if centralities else 0,
                    'max': max(centralities) if centralities else 0
                }
            }

        return result

    def _compare_edges(self, snapshots: List[DataSnapshot]) -> Dict[str, Dict[str, Any]]:
        all_edges = set()
        edge_snapshot_map: Dict[Tuple[str, str], List[bool]] = defaultdict(lambda: [False] * len(snapshots))
        edge_weights: Dict[Tuple[str, str], List[int]] = defaultdict(list)

        for i, snapshot in enumerate(snapshots):
            for edge in snapshot.edges:
                edge_key = tuple(sorted([edge.source, edge.target]))
                all_edges.add(edge_key)
                edge_snapshot_map[edge_key][i] = True
                edge_weights[edge_key].append(edge.weight)

        result = {}
        for edge_key in all_edges:
            presence = edge_snapshot_map[edge_key]
            weights = edge_weights[edge_key]

            result[f"{edge_key[0]}-{edge_key[1]}"] = {
                'source': edge_key[0],
                'target': edge_key[1],
                'is_common': all(presence),
                'is_unique': sum(presence) == 1,
                'present_in': [snapshots[i].name for i, p in enumerate(presence) if p],
                'weight_variation': {
                    'values': weights,
                    'mean': statistics.mean(weights) if weights else 0,
                    'std': statistics.stdev(weights) if len(weights) > 1 else 0,
                    'min': min(weights) if weights else 0,
                    'max': max(weights) if weights else 0
                }
            }

        return result

    def _compare_gaps(self, snapshots: List[DataSnapshot]) -> Dict[str, Dict[str, Any]]:
        all_gaps = set()
        gap_snapshot_map: Dict[Tuple[str, str], List[bool]] = defaultdict(lambda: [False] * len(snapshots))
        gap_scores: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        gap_data: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

        for i, snapshot in enumerate(snapshots):
            for gap in snapshot.gap_pairs:
                gap_key = tuple(sorted([gap.concept1, gap.concept2]))
                all_gaps.add(gap_key)
                gap_snapshot_map[gap_key][i] = True
                gap_scores[gap_key].append(gap.score)
                gap_data[gap_key].append({
                    'score': gap.score,
                    'reason': gap.reason,
                    'snapshot': snapshot.name
                })

        result = {}
        for gap_key in all_gaps:
            presence = gap_snapshot_map[gap_key]
            scores = gap_scores[gap_key]
            data = gap_data[gap_key]

            result[f"{gap_key[0]}-{gap_key[1]}"] = {
                'concept1': gap_key[0],
                'concept2': gap_key[1],
                'is_common': all(presence),
                'is_unique': sum(presence) == 1,
                'present_in': [snapshots[i].name for i, p in enumerate(presence) if p],
                'score_variation': {
                    'values': scores,
                    'mean': statistics.mean(scores) if scores else 0,
                    'std': statistics.stdev(scores) if len(scores) > 1 else 0,
                    'min': min(scores) if scores else 0,
                    'max': max(scores) if scores else 0
                },
                'details': data
            }

        return result

    def _detect_count_anomalies(
        self,
        snapshots: List[DataSnapshot],
        dimension: str,
        values: List[int]
    ) -> List[AnomalyPoint]:
        anomalies = []
        if len(values) < 2:
            return anomalies

        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0

        for i, (snapshot, val) in enumerate(zip(snapshots, values)):
            if std_val > 0:
                z_score = abs(val - mean_val) / std_val
                if z_score > 2:
                    for j, other_snapshot in enumerate(snapshots):
                        if i != j:
                            deviation = abs(val - values[j]) / max(values[j], 1) * 100
                            severity = "high" if z_score > 3 else "medium"

                            anomalies.append(AnomalyPoint(
                                id=str(uuid.uuid4()),
                                type=f"count_{dimension}",
                                description=f"{snapshot.name} 的 {dimension} 与 {other_snapshot.name} 存在显著差异",
                                snapshot1=snapshot.name,
                                snapshot2=other_snapshot.name,
                                severity=severity,
                                score=z_score,
                                details={
                                    'value1': val,
                                    'value2': values[j],
                                    'deviation_percent': deviation,
                                    'z_score': z_score,
                                    'mean': mean_val,
                                    'std': std_val
                                }
                            ))

        return anomalies

    def _detect_entity_anomalies(self, snapshots: List[DataSnapshot]) -> List[AnomalyPoint]:
        anomalies = []
        if len(snapshots) < 2:
            return anomalies

        all_entities = set()
        entity_snapshots: Dict[str, set] = defaultdict(set)

        for i, snapshot in enumerate(snapshots):
            for node in snapshot.nodes:
                all_entities.add(node.id)
                entity_snapshots[node.id].add(snapshot.name)

        for entity in all_entities:
            present_in = entity_snapshots[entity]
            if len(present_in) == 1:
                snapshot_name = next(iter(present_in))
                other_snapshots = [s.name for s in snapshots if s.name != snapshot_name]

                for other_name in other_snapshots:
                    anomalies.append(AnomalyPoint(
                        id=str(uuid.uuid4()),
                        type="unique_entity",
                        description=f"实体 '{entity}' 仅存在于 '{snapshot_name}'，在 '{other_name}' 中缺失",
                        snapshot1=snapshot_name,
                        snapshot2=other_name,
                        severity="medium",
                        score=1.0,
                        details={
                            'entity': entity,
                            'only_in': snapshot_name,
                            'missing_in': other_name
                        }
                    ))

        return anomalies

    def _generate_comparison_summary(
        self,
        snapshots: List[DataSnapshot],
        anomalies: List[AnomalyPoint],
        dimensions: List[ComparisonDimension]
    ) -> str:
        lines = [
            f"## 多源数据交叉对标分析报告",
            f"",
            f"### 基本信息",
            f"- 比较时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 参与比较的快照数量: {len(snapshots)}",
            f"- 参与比较的快照: {', '.join([s.name for s in snapshots])}",
            f"- 分析维度: {', '.join([d.value for d in dimensions])}",
            f"",
            f"### 快照统计",
        ]

        for s in snapshots:
            lines.extend([
                f"#### {s.name}",
                f"- 关键词: {', '.join(s.keywords)}",
                f"- 论文数量: {s.total_papers}",
                f"- 实体数量: {s.total_entities}",
                f"- 节点数量: {len(s.nodes)}",
                f"- 边数量: {len(s.edges)}",
                f"- 知识盲区数量: {len(s.gap_pairs)}",
                f""
            ])

        if anomalies:
            high_count = sum(1 for a in anomalies if a.severity == "high")
            medium_count = sum(1 for a in anomalies if a.severity == "medium")

            lines.extend([
                f"### 异常检测结果",
                f"- 总异常数: {len(anomalies)}",
                f"- 严重异常: {high_count}",
                f"- 中等异常: {medium_count}",
                f""
            ])

            if high_count > 0:
                lines.append("#### 严重异常:")
                for a in anomalies:
                    if a.severity == "high":
                        lines.append(f"- {a.description} (得分: {a.score:.2f})")
                lines.append("")
        else:
            lines.extend([
                f"### 异常检测结果",
                f"- 未检测到显著异常",
                f""
            ])

        lines.append("---")
        return "\n".join(lines)


data_comparator = DataComparator()
