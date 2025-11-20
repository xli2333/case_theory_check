"""语义相似度匹配引擎"""

from typing import List, Dict, Optional
import numpy as np
from loguru import logger

from ..models.bge_model import BGEModel
from ..models.vector_store import VectorStore
from ..data.models import Case


class SemanticMatcher:
    """语义相似度匹配引擎 - 基于BGE-M3的语义匹配"""

    def __init__(self,
                 bge_model: BGEModel,
                 vector_store: VectorStore):
        """
        初始化语义匹配器

        Args:
            bge_model: BGE模型实例
            vector_store: 向量存储实例
        """
        self.bge_model = bge_model
        self.vector_store = vector_store

    def match_similar_cases(self,
                           case_text: str,
                           n_results: int = 10,
                           min_similarity: float = 0.5) -> List[Dict]:
        """
        基于语义相似度匹配案例

        Args:
            case_text: 新案例文本
            n_results: 返回结果数
            min_similarity: 最小相似度阈值

        Returns:
            相似案例列表
        """
        logger.info(f"语义匹配: 搜索top-{n_results}相似案例...")

        # 1. 编码新案例
        query_embedding = self.bge_model.encode_single(case_text)

        # 2. 向量检索
        results = self.vector_store.search_similar(
            query_embedding,
            n_results=n_results * 2  # 多取一些,后续过滤
        )

        # 3. 解析和过滤结果
        similar_cases = []

        for i, (case_id, distance, metadata) in enumerate(zip(
            results['ids'][0],
            results['distances'][0],
            results['metadatas'][0]
        )):
            # ChromaDB返回的是L2距离,转换为相似度
            # 相似度 = 1 - (distance / 2)
            # 注: 对于归一化向量, L2距离在[0,2]之间
            similarity = 1 - (distance / 2)

            if similarity >= min_similarity:
                similar_cases.append({
                    'case_id': case_id,
                    'similarity': float(similarity),
                    'distance': float(distance),
                    'metadata': metadata,
                    'rank': i + 1
                })

        # 4. 按相似度排序
        similar_cases.sort(key=lambda x: x['similarity'], reverse=True)

        # 5. 取top-n
        similar_cases = similar_cases[:n_results]

        logger.success(f"✓ 找到 {len(similar_cases)} 个相似案例")

        for i, case in enumerate(similar_cases[:5], 1):
            logger.debug(f"  {i}. {case['metadata']['name']} (相似度: {case['similarity']:.3f})")

        return similar_cases

    def compute_case_similarity(self, case1_text: str, case2_text: str) -> float:
        """
        计算两个案例的语义相似度

        Args:
            case1_text: 案例1文本
            case2_text: 案例2文本

        Returns:
            相似度 (0-1)
        """
        similarity = self.bge_model.compute_similarity(case1_text, case2_text)
        return similarity
