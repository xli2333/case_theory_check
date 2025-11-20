"""FastAPI主应用"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
from pathlib import Path
import tempfile
import shutil
from loguru import logger

from ..config import settings
from ..data.database import Database
from ..data.pdf_processor import PDFProcessor
from ..models.bge_model import get_bge_model
from ..models.vector_store import VectorStore
from ..analysis.exact_matcher import ExactMatcher
from ..analysis.semantic_matcher import SemanticMatcher
from ..analysis.scorer import ComprehensiveScorer
from ..analysis.case_parser import CaseParser
from ..analysis.report_generator import ReportGenerator
from ..analysis.excel_theory_matcher import ExcelTheoryMatcher
from ..utils.theory_query_helper import TheoryQueryHelper
from ..utils.theory_normalizer import TheoryNormalizer
from ..utils.theory_mapper import build_theory_mapping, save_mapping_yaml
from .schemas import (
    CaseAnalysisRequest,
    CaseAnalysisResponse,
    TheoryQueryResponse,
    SimilarCasesResponse,
    HealthResponse,
    DatabaseStatsResponse
)

# 初始化FastAPI应用
app = FastAPI(
    title="案例知识点匹配系统",
    description="基于BGE-M3的案例理论知识点重复度检测与分析系统",
    version="1.0.0"
)

# CORS中间件配置 (允许前端调用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局组件实例
db: Optional[Database] = None
bge_model = None
vector_store: Optional[VectorStore] = None
exact_matcher: Optional[ExactMatcher] = None
semantic_matcher: Optional[SemanticMatcher] = None
scorer: Optional[ComprehensiveScorer] = None
excel_matcher: Optional[ExcelTheoryMatcher] = None


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化组件"""
    global db, bge_model, vector_store, exact_matcher, semantic_matcher, scorer, excel_matcher

    logger.info("正在启动案例知识点匹配系统...")

    try:
        # 1. 初始化数据库
        logger.info("  [1/5] 初始化数据库...")
        db = Database(str(settings.database_path_abs))

        # 2. 加载BGE模型
        logger.info("  [2/5] 加载BGE-M3模型...")
        bge_model = get_bge_model()

        # 3. 初始化向量存储
        logger.info("  [3/5] 初始化向量数据库...")
        vector_store = VectorStore(
            persist_directory=str(settings.vector_db_path_abs),
            collection_name=settings.VECTOR_COLLECTION_NAME
        )

        # 4. 初始化匹配器
        logger.info("  [4/6] 初始化匹配引擎...")
        exact_matcher = ExactMatcher(db)
        semantic_matcher = SemanticMatcher(bge_model, vector_store)

        # 5. 初始化Excel理论匹配器
        logger.info("  [5/6] 初始化Excel理论匹配器...")
        excel_matcher = ExcelTheoryMatcher()

        # 6. 生成并加载理论映射（统一标准名称）
        try:
            mapping_path = settings.get_abs_path(settings.THEORY_MAPPING_PATH)
            if not mapping_path.exists():
                extra_theories = []
                try:
                    extra_theories = excel_matcher.get_all_excel_theories() if excel_matcher else []
                except Exception:
                    extra_theories = []
                mapping = build_theory_mapping(db, extra_theories)
                save_mapping_yaml(mapping)
                logger.info("已自动生成默认映射文件（首次启动）")
            TheoryNormalizer.load_dynamic_mapping()  # 从默认路径加载（无文件则回退内置表）
            logger.success("理论标准化映射已生效")
        except Exception as _e:
            logger.warning(f"理论映射处理失败，使用内置映射: {_e}")

        # 7. 初始化评分器
        logger.info("  [6/6] 初始化评分器...")
        scorer = ComprehensiveScorer()

        logger.success("✓ 系统启动完成!")

        # 打印数据库统计
        stats = db.get_database_stats()
        logger.info(f"  数据库: {stats['total_cases']} 个案例, {stats['total_theories']} 个理论")

        # 打印Excel理论统计（可选）
        if excel_matcher:
            try:
                excel_stats = excel_matcher.get_statistics()
                logger.info(f"  Excel理论: {excel_stats['total_unique_theories']} 个唯一理论")
            except Exception:
                pass

    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("正在关闭系统...")


# ==================== 健康检查 ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database_connected": db is not None,
        "model_loaded": bge_model is not None,
        "vector_store_ready": vector_store is not None
    }


@app.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats():
    """获取数据库统计信息"""
    if not db:
        raise HTTPException(status_code=503, detail="数据库未初始化")

    stats = db.get_database_stats()
    return stats


# ==================== 案例分析接口 ====================

@app.post("/analyze/text", response_model=CaseAnalysisResponse)
async def analyze_case_text(request: CaseAnalysisRequest):
    """
    分析文本格式的案例

    Args:
        request: 案例分析请求 (包含案例文本和元数据)

    Returns:
        分析报告
    """
    logger.info(f"收到文本分析请求: {request.name}")

    try:
        # 1. 解析案例
        case_data = CaseParser.parse_text(request.text)
        case_data['name'] = request.name
        if request.author:
            case_data['author'] = request.author
        if request.subject:
            case_data['subject'] = request.subject
        if request.industry:
            case_data['industry'] = request.industry
        if request.keywords:
            case_data['keywords'] = request.keywords

        # 2. 始终从文本中提取所有理论
        known_theories = db.get_all_theory_names()
        identified_theories = CaseParser.extract_theories_from_text(
            request.text, known_theories
        )

        logger.info(f"  从文本中识别出 {len(identified_theories)} 个理论")

        # 2.5 应用理论标准化 (自动去重和归并同义理论)
        original_count = len(identified_theories)
        identified_theories = TheoryNormalizer.normalize_list(identified_theories)
        if len(identified_theories) < original_count:
            logger.info(f"  理论标准化: {original_count} -> {len(identified_theories)} (去重 {original_count - len(identified_theories)} 个)")

        case_data['theories'] = identified_theories

        # 2.6 处理用户指定的主要理论（仅作为标记，不影响理论识别）
        primary_theories_input = []
        if request.theories:
            # 兼容旧版本：如果用户通过theories字段传入，视为主要理论
            primary_theories_input = request.theories
            logger.info(f"  用户通过theories字段指定主要理论: {len(primary_theories_input)} 个")
        elif hasattr(request, 'primary_theories') and request.primary_theories:
            # 新版本：使用专门的primary_theories字段
            primary_theories_input = request.primary_theories
            logger.info(f"  用户指定主要理论: {len(primary_theories_input)} 个")

        # 标准化主要理论
        primary_theories = []
        if primary_theories_input:
            primary_theories = TheoryNormalizer.normalize_list(primary_theories_input)
            logger.info(f"  主要理论标准化后: {primary_theories}")

        case_data['primary_theories'] = primary_theories

        # 3. 理论匹配(仅精确匹配)
        exact_matches, _ = exact_matcher.match_theories(case_data['theories'])

        # 使用精确匹配结果进行后续分析
        all_matches = exact_matches

        # 4. 语义相似度匹配
        semantic_matches = semantic_matcher.match_similar_cases(
            case_text=request.text,
            n_results=20,
            min_similarity=0.5
        )

        # 5. 综合评分排序
        comprehensive_scores = scorer.rank_similar_cases(
            new_case=case_data,
            semantic_matches=semantic_matches,
            exact_matches=all_matches,  # 使用合并后的匹配结果
            top_k=10
        )

        # 6. 计算创新度
        innovation_score = scorer.calculate_innovation_score(
            new_case=case_data,
            exact_matches=all_matches  # 使用合并后的匹配结果
        )

        # 7. 生成报告
        report_md = ReportGenerator.generate_report(
            new_case=case_data,
            exact_matches=exact_matches,
            comprehensive_scores=comprehensive_scores,
            innovation_score=innovation_score
        )

        logger.success(f"✓ 分析完成: {request.name}")

        return {
            "case_name": request.name,
            "identified_theories": case_data['theories'],
            "primary_theories": primary_theories if primary_theories else None,
            "exact_matches": exact_matches,
            "fuzzy_matches": {},  # 不再使用模糊匹配
            "similar_cases": comprehensive_scores,
            "innovation_score": innovation_score,
            "report_markdown": report_md
        }

    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.post("/analyze/upload", response_model=CaseAnalysisResponse)
async def analyze_case_upload(
    file: UploadFile = File(...),
    name: str = Form(...),
    author: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    industry: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    theories: Optional[str] = Form(None),  # 逗号分隔的理论列表
    primary_theories: Optional[str] = Form(None)  # 逗号分隔的主要理论列表
):
    """
    上传PDF文件并分析

    Args:
        file: PDF文件
        name: 案例名称
        author: 作者
        subject: 学科领域
        industry: 行业
        keywords: 关键词
        theories: 理论列表 (逗号分隔)

    Returns:
        分析报告
    """
    logger.info(f"收到文件上传分析请求: {name} ({file.filename})")

    # 检查文件类型
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持PDF文件")

    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        try:
            # 提取PDF文本
            logger.info("  提取PDF文本...")
            text = PDFProcessor.extract_text(tmp_path)

            logger.info(f"  PDF文本提取结果: 长度={len(text) if text else 0}")

            if not text:
                logger.error("  PDF文本提取失败: 返回空内容")
                raise HTTPException(status_code=400, detail="PDF文件无法解析，可能是扫描版或加密文件")

            if len(text.strip()) < 50:  # 放宽限制从100改为50
                logger.error(f"  PDF文本内容过短: {len(text.strip())}字符")
                raise HTTPException(status_code=400, detail=f"PDF文本内容过短({len(text.strip())}字符)，至少需要50字符")

            logger.info(f"  提取文本长度: {len(text)} 字符")

            # 解析理论列表
            theory_list = None
            if theories:
                theory_list = [t.strip() for t in theories.split(',') if t.strip()]

            # 解析主要理论列表
            primary_theory_list = None
            if primary_theories:
                primary_theory_list = [t.strip() for t in primary_theories.split(',') if t.strip()]

            # 调用文本分析接口
            request = CaseAnalysisRequest(
                name=name,
                text=text,
                author=author,
                subject=subject,
                industry=industry,
                keywords=keywords,
                theories=theory_list,
                primary_theories=primary_theory_list
            )

            return await analyze_case_text(request)

        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


# ==================== 理论查询接口 ====================

@app.get("/theories/", response_model=List[str])
async def list_all_theories():
    """获取所有理论列表(标准化去重后)"""
    if not db:
        raise HTTPException(status_code=503, detail="数据库未初始化")

    try:
        # 返回标准化后的理论列表
        theories = TheoryQueryHelper.get_normalized_theory_list(db)
        logger.info(f"返回 {len(theories)} 个标准化理论")
        return theories
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.get("/theories/{theory_name}/cases", response_model=TheoryQueryResponse)
async def get_cases_by_theory(theory_name: str):
    """
    查询使用某个理论的所有案例(自动合并相似理论)

    Args:
        theory_name: 理论名称(可以是标准名称或变体)

    Returns:
        使用该理论的案例列表及统计信息(包含所有变体的案例)
    """
    logger.info(f"查询理论: {theory_name}")

    if not db:
        raise HTTPException(status_code=503, detail="数据库未初始化")

    try:
        # 使用标准化查询助手,自动合并相似理论的结果
        result = TheoryQueryHelper.merge_theory_results(db, theory_name)

        logger.info(f"  标准化为: {result['theory_name']}")
        logger.info(f"  包含变体: {', '.join(result['variants'])}")
        logger.info(f"  找到 {result['usage_count']} 个案例 - {result['frequency_rank']}")

        return {
            "theory_name": result['theory_name'],
            "usage_count": result['usage_count'],
            "frequency_rank": result['frequency_rank'],
            "rank_emoji": result['rank_emoji'],
            "cases": result['cases']
        }

    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ==================== 相似案例查询接口 ====================

@app.get("/cases/{case_id}/similar", response_model=SimilarCasesResponse)
async def get_similar_cases(case_id: str, top_k: int = 10):
    """
    查找与指定案例相似的案例

    Args:
        case_id: 案例ID
        top_k: 返回前K个相似案例

    Returns:
        相似案例列表
    """
    logger.info(f"查询相似案例: {case_id} (top-{top_k})")

    if not db or not vector_store or not semantic_matcher:
        raise HTTPException(status_code=503, detail="系统未初始化")

    try:
        # 获取原案例
        case = db.get_case_by_id(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"案例不存在: {case_id}")

        # 获取案例文本
        case_text = case.get('full_text') or case.get('abstract', '')
        if not case_text:
            raise HTTPException(status_code=400, detail="案例无文本内容")

        # 语义匹配
        similar_cases = semantic_matcher.match_similar_cases(
            case_text=case_text,
            n_results=top_k,
            min_similarity=0.5
        )

        logger.success(f"✓ 找到 {len(similar_cases)} 个相似案例")

        return {
            "case_id": case_id,
            "case_name": case.get('name', 'N/A'),
            "similar_cases": similar_cases
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ==================== 案例检索接口 ====================

@app.get("/cases/search")
async def search_cases(
    keyword: Optional[str] = None,
    subject: Optional[str] = None,
    industry: Optional[str] = None,
    year: Optional[str] = None,
    limit: int = 20
):
    """
    搜索案例 (按关键词、学科、行业、年份等)

    Args:
        keyword: 关键词
        subject: 学科
        industry: 行业
        year: 年份
        limit: 返回数量限制

    Returns:
        案例列表
    """
    logger.info(f"搜索案例: keyword={keyword}, subject={subject}, industry={industry}, year={year}")

    if not db:
        raise HTTPException(status_code=503, detail="数据库未初始化")

    try:
        cases = db.search_cases(
            keyword=keyword,
            subject=subject,
            industry=industry,
            year=year,
            limit=limit
        )

        logger.info(f"  找到 {len(cases)} 个案例")

        return {
            "total": len(cases),
            "cases": cases
        }

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
