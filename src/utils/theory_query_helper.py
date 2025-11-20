"""理论查询辅助工具 - 支持标准化理论查询"""

from typing import List, Dict
from .theory_normalizer import TheoryNormalizer
from ..config import settings


class TheoryQueryHelper:
    """理论查询辅助类 - 合并相似理论的查询结果"""

    @staticmethod
    def merge_theory_results(db, theory_name: str) -> Dict:
        """
        查询理论的所有变体并合并结果

        Args:
            db: 数据库实例
            theory_name: 理论名称(可以是标准名称或变体)

        Returns:
            合并后的查询结果
        """
        # 标准化理论名称
        standard_name = TheoryNormalizer.normalize(theory_name)

        # 获取所有变体
        variants = TheoryNormalizer.get_all_variants(standard_name)

        # 查询所有变体的案例
        all_cases = []
        seen_case_ids = set()

        for variant in variants:
            try:
                cases = db.get_cases_by_theory(variant)
                # 去重
                for case in cases:
                    case_id = case.get('id') or case.get('code') or case.get('name')
                    if case_id not in seen_case_ids:
                        seen_case_ids.add(case_id)
                        # 标记原始理论名称
                        case['matched_theory_name'] = variant
                        all_cases.append(case)
            except:
                # 如果某个变体不存在,跳过
                continue

        # 计算频率等级（阈值可配置）
        count = len(all_cases)
        if count >= settings.HIGH_FREQ_MIN_USAGE:
            frequency_rank = '经典理论'
            rank_emoji = '[经典]'
        elif count > settings.NOVEL_MAX_USAGE:
            frequency_rank = '常见理论'
            rank_emoji = '[常见]'
        else:
            frequency_rank = '新颖理论'
            rank_emoji = '[新颖]'

        return {
            "theory_name": standard_name,
            "variants": variants,
            "usage_count": count,
            "frequency_rank": frequency_rank,
            "rank_emoji": rank_emoji,
            "cases": all_cases
        }

    @staticmethod
    def get_normalized_theory_list(db) -> List[str]:
        """
        获取标准化后的理论列表

        Args:
            db: 数据库实例

        Returns:
            标准化去重后的理论列表
        """
        # 获取原始理论列表
        raw_theories = db.get_all_theory_names()

        # 标准化并去重
        normalized = TheoryNormalizer.normalize_list(raw_theories)

        return sorted(normalized)

    @staticmethod
    def search_theories(db, keyword: str) -> List[str]:
        """
        搜索理论(标准化后)

        Args:
            db: 数据库实例
            keyword: 搜索关键词

        Returns:
            匹配的标准化理论列表
        """
        normalized_theories = TheoryQueryHelper.get_normalized_theory_list(db)

        if not keyword:
            return normalized_theories

        keyword_lower = keyword.lower().strip()

        # 模糊匹配
        matches = [
            t for t in normalized_theories
            if keyword_lower in t.lower()
        ]

        return matches
