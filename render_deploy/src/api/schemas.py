"""API数据模型定义"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ==================== 请求模型 ====================

class CaseAnalysisRequest(BaseModel):
    """案例分析请求"""
    name: str = Field(..., description="案例名称")
    text: str = Field(..., description="案例文本内容")
    author: Optional[str] = Field(None, description="作者")
    subject: Optional[str] = Field(None, description="学科领域")
    industry: Optional[str] = Field(None, description="行业")
    keywords: Optional[str] = Field(None, description="关键词")
    theories: Optional[List[str]] = Field(None, description="理论列表 (可选,系统会自动识别)")
    primary_theories: Optional[List[str]] = Field(None, description="主要理论列表 (可选,用于突出显示)")


# ==================== 响应模型 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    database_connected: bool
    model_loaded: bool
    vector_store_ready: bool


class DatabaseStatsResponse(BaseModel):
    """数据库统计响应"""
    total_cases: int
    total_theories: int
    total_case_theory_relations: int
    years_covered: List[str]


class TheoryMatchDetail(BaseModel):
    """理论匹配详情"""
    theory_name: str
    match_count: int
    frequency_rank: str
    rank_emoji: str
    cases: List[Dict[str, Any]]


class SimilarCaseDetail(BaseModel):
    """相似案例详情"""
    case_id: str
    metadata: Dict[str, Any]
    scores: Dict[str, Any]


class InnovationScore(BaseModel):
    """创新度评分"""
    innovation_score: float
    novel_theories: List[str]
    common_theories: List[str]
    high_frequency_theories: List[str]
    novel_ratio: float
    common_ratio: float
    high_freq_ratio: float


class CaseAnalysisResponse(BaseModel):
    """案例分析响应"""
    case_name: str
    identified_theories: List[str]
    primary_theories: Optional[List[str]] = Field(None, description="主要理论列表")
    exact_matches: Dict[str, Any]
    fuzzy_matches: Dict[str, Any]
    similar_cases: List[Dict[str, Any]]
    innovation_score: Dict[str, Any]
    report_markdown: str


class TheoryQueryResponse(BaseModel):
    """理论查询响应"""
    theory_name: str
    usage_count: int
    frequency_rank: str
    rank_emoji: str
    cases: List[Dict[str, Any]]


class SimilarCasesResponse(BaseModel):
    """相似案例查询响应"""
    case_id: str
    case_name: str
    similar_cases: List[Dict[str, Any]]
