from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime


class VisualizationMode(str, Enum):
    TWO_D = "2d"
    THREE_D = "3d"


class ComparisonDimension(str, Enum):
    NODE_COUNT = "node_count"
    EDGE_COUNT = "edge_count"
    GAP_COUNT = "gap_count"
    COMMUNITY_COUNT = "community_count"
    TOP_ENTITIES = "top_entities"
    CENTRALITY_DISTRIBUTION = "centrality_distribution"
    GAP_SCORE_DISTRIBUTION = "gap_score_distribution"


class NotificationChannel(str, Enum):
    SYSTEM_POPUP = "system_popup"
    WEBHOOK = "webhook"
    EMAIL = "email"


class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"


class DataSnapshot(BaseModel):
    id: Optional[str] = None
    name: str
    created_at: Optional[datetime] = None
    keywords: List[str]
    total_papers: int
    total_entities: int
    nodes: List['Node'] = []
    edges: List['Edge'] = []
    gap_pairs: List['GapPair'] = []
    papers: List['Paper'] = []
    metadata: Dict[str, Any] = {}


class ComparisonResult(BaseModel):
    snapshot_ids: List[str]
    snapshot_names: List[str]
    comparison_time: datetime
    dimensions: List[ComparisonDimension]
    node_comparison: Dict[str, Dict[str, Any]]
    edge_comparison: Dict[str, Dict[str, Any]]
    gap_comparison: Dict[str, Dict[str, Any]]
    anomalies: List['AnomalyPoint']
    summary: str


class AnomalyPoint(BaseModel):
    id: str
    type: str
    description: str
    snapshot1: str
    snapshot2: str
    severity: str
    score: float
    details: Dict[str, Any] = {}


class ThresholdConfig(BaseModel):
    id: Optional[str] = None
    name: str
    dimension: str
    operator: str
    value: float
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class NotificationConfig(BaseModel):
    id: Optional[str] = None
    name: str
    channels: List[NotificationChannel]
    webhook_url: Optional[str] = None
    email_recipients: List[str] = []
    is_active: bool = True
    created_at: Optional[datetime] = None


class Alert(BaseModel):
    id: Optional[str] = None
    threshold_id: str
    threshold_name: str
    snapshot_id: str
    snapshot_name: str
    triggered_at: datetime
    dimension: str
    expected_value: float
    actual_value: float
    deviation: float
    message: str
    is_read: bool = False
    channels: List[NotificationChannel] = []


class ReportRequest(BaseModel):
    snapshot_ids: List[str]
    format: ReportFormat
    include_charts: bool = True
    include_statistics: bool = True
    include_gaps: bool = True
    include_anomalies: bool = True
    title: Optional[str] = None
    description: Optional[str] = None


class ReportResult(BaseModel):
    report_id: str
    format: ReportFormat
    title: str
    generated_at: datetime
    file_size: int
    download_url: Optional[str] = None
    content: Optional[bytes] = None


class SearchRequest(BaseModel):
    keywords: List[str]
    max_papers: Optional[int] = 100
    years_back: Optional[int] = 5
    api_key: Optional[str] = None
    visualization_mode: Optional[VisualizationMode] = VisualizationMode.THREE_D


class Paper(BaseModel):
    paper_id: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    authors: List[str] = []
    venue: Optional[str] = None
    citations: int = 0
    url: Optional[str] = None


class Entity(BaseModel):
    name: str
    count: int
    papers: List[str] = []


class Node(BaseModel):
    id: str
    label: str
    size: int
    group: int
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    betweenness_centrality: Optional[float] = None
    constraint: Optional[float] = None
    effective_size: Optional[float] = None


class Edge(BaseModel):
    source: str
    target: str
    weight: int
    is_gap: bool = False


class GapPair(BaseModel):
    concept1: str
    concept2: str
    score: float
    reason: str
    prompt: str


class NetworkData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    gap_pairs: List[GapPair]
    papers: List[Paper]
    total_papers: int
    total_entities: int


class GapPromptRequest(BaseModel):
    concept1: str
    concept2: str
    keywords: List[str]
    papers: List[Paper]


class GapPromptResponse(BaseModel):
    prompt: str
    concept1: str
    concept2: str
    research_directions: List[str]


class ConfigResponse(BaseModel):
    has_api_key: bool
    max_papers_limit: int
    default_years_back: int
    scispacy_model: str
