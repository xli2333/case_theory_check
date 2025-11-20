"""数据模型定义"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Theory(BaseModel):
    """理论模型"""
    id: Optional[int] = None
    name: str = Field(..., description="理论名称")
    source: Optional[str] = Field(None, description="来源文献")
    author: Optional[str] = Field(None, description="理论提出者")
    year: Optional[int] = Field(None, description="年份")
    pdf_path: Optional[str] = Field(None, description="PDF文件路径")
    description: Optional[str] = Field(None, description="理论描述")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Case(BaseModel):
    """案例模型"""
    model_config = {'protected_namespaces': ()}
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    text: str
    code: Optional[str] = None

    class Config:
        from_attributes = True


class CaseTheory(BaseModel):
    """案例-理论关联模型"""
    id: Optional[int] = None
    case_id: int = Field(..., description="案例ID")
    theory_id: int = Field(..., description="理论ID")
    question_number: Optional[str] = Field(None, description="思考题编号")
    question_text: Optional[str] = Field(None, description="思考题内容")
    question_type: Optional[str] = Field(None, description="问题类型 (how/what/why)")
    question_style: Optional[str] = Field(None, description="问题风格 (close/open)")
    context: Optional[str] = Field(None, description="使用上下文")

    class Config:
        from_attributes = True


class MatchResult(BaseModel):
    """匹配结果模型"""
    case: Case
    similarity_score: float = Field(..., description="相似度分数")
    theory_overlap: float = Field(..., description="理论重叠度")
    semantic_similarity: float = Field(..., description="语义相似度")
    keyword_similarity: float = Field(..., description="关键词相似度")
    domain_similarity: float = Field(..., description="领域相似度")
    matched_theories: List[str] = Field(default_factory=list, description="匹配的理论")


class AnalysisReport(BaseModel):
    """分析报告模型"""
    case_name: str
    identified_theories: List[str]
    theory_matches: dict
    similar_cases: List[MatchResult]
    innovation_score: float
    recommendations: List[str]
    report_markdown: str
