from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class VisualizationMode(str, Enum):
    TWO_D = "2d"
    THREE_D = "3d"


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
