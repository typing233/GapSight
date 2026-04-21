import uuid
import json
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from io import BytesIO
import logging

from backend.models.schemas import (
    DataSnapshot, ReportRequest, ReportResult, ReportFormat,
    ComparisonResult
)

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self):
        self.reports: Dict[str, Dict[str, Any]] = {}

    def generate_report(
        self,
        request: ReportRequest,
        snapshots: List[DataSnapshot],
        comparison_result: Optional[ComparisonResult] = None
    ) -> ReportResult:
        report_id = str(uuid.uuid4())
        generated_at = datetime.now()

        title = request.title or f"GapSight 分析报告 - {generated_at.strftime('%Y-%m-%d %H:%M:%S')}"

        report_data = self._build_report_data(
            title=title,
            description=request.description,
            snapshots=snapshots,
            comparison_result=comparison_result,
            include_charts=request.include_charts,
            include_statistics=request.include_statistics,
            include_gaps=request.include_gaps,
            include_anomalies=request.include_anomalies
        )

        if request.format == ReportFormat.PDF:
            content = self._generate_pdf(report_data)
        elif request.format == ReportFormat.EXCEL:
            content = self._generate_excel(report_data)
        elif request.format == ReportFormat.JSON:
            content = self._generate_json(report_data)
        else:
            content = self._generate_json(report_data)

        report_result = ReportResult(
            report_id=report_id,
            format=request.format,
            title=title,
            generated_at=generated_at,
            file_size=len(content),
            content=content
        )

        self.reports[report_id] = {
            'result': report_result,
            'data': report_data,
            'created_at': generated_at
        }

        logger.info(f"生成报告: {title} (ID: {report_id}, 格式: {request.format.value}, 大小: {len(content)} bytes)")

        return report_result

    def _build_report_data(
        self,
        title: str,
        description: Optional[str],
        snapshots: List[DataSnapshot],
        comparison_result: Optional[ComparisonResult],
        include_charts: bool,
        include_statistics: bool,
        include_gaps: bool,
        include_anomalies: bool
    ) -> Dict[str, Any]:
        report_data = {
            'title': title,
            'description': description or "",
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'snapshots': [],
            'comparison': None,
            'statistics': {},
            'gaps': [],
            'anomalies': []
        }

        for snapshot in snapshots:
            snapshot_data = {
                'id': snapshot.id,
                'name': snapshot.name,
                'created_at': snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S') if snapshot.created_at else "",
                'keywords': snapshot.keywords,
                'statistics': {
                    'total_papers': snapshot.total_papers,
                    'total_entities': snapshot.total_entities,
                    'node_count': len(snapshot.nodes),
                    'edge_count': len(snapshot.edges),
                    'gap_count': len(snapshot.gap_pairs)
                }
            }

            if include_statistics:
                snapshot_data['node_details'] = [
                    {
                        'id': node.id,
                        'label': node.label,
                        'size': node.size,
                        'group': node.group,
                        'betweenness_centrality': node.betweenness_centrality,
                        'constraint': node.constraint,
                        'effective_size': node.effective_size
                    }
                    for node in snapshot.nodes
                ]

                snapshot_data['edge_details'] = [
                    {
                        'source': edge.source,
                        'target': edge.target,
                        'weight': edge.weight,
                        'is_gap': edge.is_gap
                    }
                    for edge in snapshot.edges
                ]

            if include_gaps:
                snapshot_data['gaps'] = [
                    {
                        'concept1': gap.concept1,
                        'concept2': gap.concept2,
                        'score': gap.score,
                        'reason': gap.reason,
                        'prompt': gap.prompt
                    }
                    for gap in snapshot.gap_pairs
                ]

            report_data['snapshots'].append(snapshot_data)

        if comparison_result:
            report_data['comparison'] = {
                'snapshot_ids': comparison_result.snapshot_ids,
                'snapshot_names': comparison_result.snapshot_names,
                'comparison_time': comparison_result.comparison_time.strftime('%Y-%m-%d %H:%M:%S'),
                'dimensions': [d.value for d in comparison_result.dimensions],
                'summary': comparison_result.summary
            }

            if include_statistics:
                report_data['comparison']['node_comparison'] = comparison_result.node_comparison
                report_data['comparison']['edge_comparison'] = comparison_result.edge_comparison
                report_data['comparison']['gap_comparison'] = comparison_result.gap_comparison

            if include_anomalies:
                report_data['comparison']['anomalies'] = [
                    {
                        'id': a.id,
                        'type': a.type,
                        'description': a.description,
                        'snapshot1': a.snapshot1,
                        'snapshot2': a.snapshot2,
                        'severity': a.severity,
                        'score': a.score,
                        'details': a.details
                    }
                    for a in comparison_result.anomalies
                ]

        if include_statistics:
            report_data['statistics'] = self._calculate_aggregate_statistics(snapshots)

        if include_gaps:
            all_gaps = []
            for snapshot in snapshots:
                for gap in snapshot.gap_pairs:
                    all_gaps.append({
                        'snapshot': snapshot.name,
                        'concept1': gap.concept1,
                        'concept2': gap.concept2,
                        'score': gap.score,
                        'reason': gap.reason
                    })
            all_gaps.sort(key=lambda x: x['score'], reverse=True)
            report_data['gaps'] = all_gaps[:50]

        if include_anomalies and comparison_result:
            report_data['anomalies'] = [
                {
                    'type': a.type,
                    'description': a.description,
                    'snapshot1': a.snapshot1,
                    'snapshot2': a.snapshot2,
                    'severity': a.severity,
                    'score': a.score
                }
                for a in comparison_result.anomalies
            ]

        return report_data

    def _calculate_aggregate_statistics(self, snapshots: List[DataSnapshot]) -> Dict[str, Any]:
        stats = {
            'total_snapshots': len(snapshots),
            'total_papers': sum(s.total_papers for s in snapshots),
            'total_entities': sum(s.total_entities for s in snapshots),
            'total_nodes': sum(len(s.nodes) for s in snapshots),
            'total_edges': sum(len(s.edges) for s in snapshots),
            'total_gaps': sum(len(s.gap_pairs) for s in snapshots),
            'per_snapshot': []
        }

        for snapshot in snapshots:
            if snapshot.nodes:
                centralities = [n.betweenness_centrality for n in snapshot.nodes if n.betweenness_centrality is not None]
                avg_centrality = sum(centralities) / len(centralities) if centralities else 0
            else:
                avg_centrality = 0

            if snapshot.gap_pairs:
                avg_gap_score = sum(g.score for g in snapshot.gap_pairs) / len(snapshot.gap_pairs)
            else:
                avg_gap_score = 0

            stats['per_snapshot'].append({
                'name': snapshot.name,
                'papers': snapshot.total_papers,
                'entities': snapshot.total_entities,
                'nodes': len(snapshot.nodes),
                'edges': len(snapshot.edges),
                'gaps': len(snapshot.gap_pairs),
                'avg_centrality': avg_centrality,
                'avg_gap_score': avg_gap_score
            })

        return stats

    def _generate_json(self, data: Dict[str, Any]) -> bytes:
        json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        return json_str.encode('utf-8')

    def _generate_pdf(self, data: Dict[str, Any]) -> bytes:
        content = self._generate_report_content(data)
        return content.encode('utf-8')

    def _generate_excel(self, data: Dict[str, Any]) -> bytes:
        content = self._generate_csv_content(data)
        return content.encode('utf-8')

    def _generate_report_content(self, data: Dict[str, Any]) -> str:
        lines = []

        lines.append("=" * 80)
        lines.append(data['title'])
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"生成时间: {data['generated_at']}")
        lines.append(f"快照数量: {len(data['snapshots'])}")
        if data['description']:
            lines.append(f"描述: {data['description']}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        lines.append("【快照信息】")
        lines.append("")
        for i, snapshot in enumerate(data['snapshots'], 1):
            lines.append(f"快照 {i}: {snapshot['name']}")
            lines.append(f"  ID: {snapshot['id']}")
            lines.append(f"  关键词: {', '.join(snapshot['keywords'])}")
            lines.append(f"  论文数量: {snapshot['statistics']['total_papers']}")
            lines.append(f"  实体数量: {snapshot['statistics']['total_entities']}")
            lines.append(f"  节点数量: {snapshot['statistics']['node_count']}")
            lines.append(f"  边数量: {snapshot['statistics']['edge_count']}")
            lines.append(f"  知识盲区数量: {snapshot['statistics']['gap_count']}")
            lines.append("")

        if data['comparison']:
            lines.append("-" * 80)
            lines.append("")
            lines.append("【交叉对标分析】")
            lines.append("")
            lines.append(f"分析维度: {', '.join(data['comparison']['dimensions'])}")
            lines.append("")

            if data['comparison'].get('anomalies'):
                lines.append("检测到的异常点:")
                lines.append("")
                for anomaly in data['comparison']['anomalies']:
                    severity_icon = "🔴" if anomaly['severity'] == "high" else "🟡"
                    lines.append(f"{severity_icon} [{anomaly['severity'].upper()}] {anomaly['type']}")
                    lines.append(f"   描述: {anomaly['description']}")
                    lines.append(f"   涉及快照: {anomaly['snapshot1']} vs {anomaly['snapshot2']}")
                    lines.append(f"   异常得分: {anomaly['score']:.2f}")
                    lines.append("")

            lines.append("")
            lines.append("分析摘要:")
            lines.append("")
            for line in data['comparison']['summary'].split('\n'):
                lines.append(f"  {line}")
            lines.append("")

        if data['gaps']:
            lines.append("-" * 80)
            lines.append("")
            lines.append("【知识盲区列表 (Top 20)】")
            lines.append("")
            for i, gap in enumerate(data['gaps'][:20], 1):
                lines.append(f"{i}. {gap['concept1']} ↔ {gap['concept2']}")
                lines.append(f"   快照: {gap['snapshot']}")
                lines.append(f"   得分: {gap['score']:.3f}")
                lines.append(f"   原因: {gap['reason']}")
                lines.append("")

        if data['statistics'] and data['statistics'].get('per_snapshot'):
            lines.append("-" * 80)
            lines.append("")
            lines.append("【统计摘要】")
            lines.append("")
            lines.append(f"总快照数: {data['statistics']['total_snapshots']}")
            lines.append(f"总论文数: {data['statistics']['total_papers']}")
            lines.append(f"总实体数: {data['statistics']['total_entities']}")
            lines.append(f"总节点数: {data['statistics']['total_nodes']}")
            lines.append(f"总边数: {data['statistics']['total_edges']}")
            lines.append(f"总知识盲区数: {data['statistics']['total_gaps']}")
            lines.append("")

            lines.append("各快照详细统计:")
            lines.append("")
            for stats in data['statistics']['per_snapshot']:
                lines.append(f"  {stats['name']}:")
                lines.append(f"    论文: {stats['papers']}, 实体: {stats['entities']}")
                lines.append(f"    节点: {stats['nodes']}, 边: {stats['edges']}, 盲区: {stats['gaps']}")
                lines.append(f"    平均中心性: {stats['avg_centrality']:.4f}")
                lines.append(f"    平均盲区得分: {stats['avg_gap_score']:.4f}")
                lines.append("")

        lines.append("=" * 80)
        lines.append("报告生成完毕 - GapSight 跨学科知识盲区探测工具")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _generate_csv_content(self, data: Dict[str, Any]) -> str:
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(["GapSight 分析报告"])
        writer.writerow([data['title']])
        writer.writerow(["生成时间", data['generated_at']])
        writer.writerow([])

        writer.writerow(["快照统计"])
        writer.writerow(["快照名称", "论文数", "实体数", "节点数", "边数", "知识盲区数", "关键词"])
        for snapshot in data['snapshots']:
            writer.writerow([
                snapshot['name'],
                snapshot['statistics']['total_papers'],
                snapshot['statistics']['total_entities'],
                snapshot['statistics']['node_count'],
                snapshot['statistics']['edge_count'],
                snapshot['statistics']['gap_count'],
                ", ".join(snapshot['keywords'])
            ])
        writer.writerow([])

        if data['gaps']:
            writer.writerow(["知识盲区列表 (Top 20)"])
            writer.writerow(["序号", "概念1", "概念2", "快照", "得分", "原因"])
            for i, gap in enumerate(data['gaps'][:20], 1):
                writer.writerow([
                    i,
                    gap['concept1'],
                    gap['concept2'],
                    gap['snapshot'],
                    f"{gap['score']:.4f}",
                    gap['reason']
                ])
            writer.writerow([])

        if data['comparison'] and data['comparison'].get('anomalies'):
            writer.writerow(["异常点检测"])
            writer.writerow(["类型", "描述", "快照1", "快照2", "严重程度", "得分"])
            for anomaly in data['comparison']['anomalies']:
                writer.writerow([
                    anomaly['type'],
                    anomaly['description'],
                    anomaly['snapshot1'],
                    anomaly['snapshot2'],
                    anomaly['severity'],
                    f"{anomaly['score']:.4f}"
                ])
            writer.writerow([])

        if data['statistics'] and data['statistics'].get('per_snapshot'):
            writer.writerow(["详细统计"])
            writer.writerow([
                "快照名称", "论文数", "实体数", "节点数", "边数",
                "知识盲区数", "平均中心性", "平均盲区得分"
            ])
            for stats in data['statistics']['per_snapshot']:
                writer.writerow([
                    stats['name'],
                    stats['papers'],
                    stats['entities'],
                    stats['nodes'],
                    stats['edges'],
                    stats['gaps'],
                    f"{stats['avg_centrality']:.6f}",
                    f"{stats['avg_gap_score']:.6f}"
                ])

        return output.getvalue()

    def get_report(self, report_id: str) -> Optional[ReportResult]:
        if report_id in self.reports:
            return self.reports[report_id]['result']
        return None

    def list_reports(self) -> List[Dict[str, Any]]:
        return [
            {
                'report_id': report_id,
                'title': data['result'].title,
                'format': data['result'].format.value,
                'generated_at': data['created_at'].isoformat(),
                'file_size': data['result'].file_size
            }
            for report_id, data in self.reports.items()
        ]

    def delete_report(self, report_id: str) -> bool:
        if report_id in self.reports:
            del self.reports[report_id]
            logger.info(f"删除报告 (ID: {report_id})")
            return True
        return False


report_service = ReportService()
