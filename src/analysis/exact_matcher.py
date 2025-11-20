"""精确匹配引擎（含标准化合并与模糊回退）"""

from typing import List, Dict, Optional, Tuple
from loguru import logger
import re

from ..data.database import Database
from ..utils.theory_query_helper import TheoryQueryHelper
from ..config import settings


class ExactMatcher:
    """精确匹配引擎 - 基于理论名称的标准化合并与模糊匹配"""

    def __init__(self, db: Database):
        self.db = db
        self._all_theories_cache: Optional[List[str]] = None

    def _get_all_theories(self) -> List[str]:
        if self._all_theories_cache is None:
            self._all_theories_cache = self.db.get_all_theory_names()
        return self._all_theories_cache

    def _fuzzy_match_theory(self, input_theory: str) -> Optional[str]:
        """在库中做模糊命中一个最可能的理论名称（用于回退）"""
        all_theories = self._get_all_theories()
        normalized_input = re.sub(r"\s+", " ", input_theory or "").strip()
        normalized_input = normalized_input.replace("（", "(").replace("）", ")")

        # 策略1：子串包含
        for t in all_theories:
            nd = re.sub(r"\s+", " ", t or "").strip()
            nd = nd.replace("（", "(").replace("）", ")")
            if normalized_input.lower() in nd.lower():
                return t

        # 策略2：中英文分段比对（完全等价）
        chinese_part = re.sub(r"[^\u4e00-\u9fff]", "", input_theory or "").strip()
        english_part = re.sub(r"[^a-zA-Z]", " ", input_theory or "").strip()
        english_part = re.sub(r"\s+", " ", english_part).strip()

        for t in all_theories:
            db_ch = re.sub(r"[^\u4e00-\u9fff]", "", t).strip()
            db_en = re.sub(r"[^a-zA-Z]", " ", t).strip()
            db_en = re.sub(r"\s+", " ", db_en).strip()
            if chinese_part and db_ch and chinese_part == db_ch:
                return t
            if english_part and db_en and english_part.lower() == db_en.lower():
                return t

        return None

    def match_theories(self, theories: List[str]) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
        """返回（标准化合并结果，模糊+标准化回退结果）"""
        logger.info(f"匹配 {len(theories)} 个理论...")

        exact_results: Dict[str, Dict] = {}
        fuzzy_results: Dict[str, Dict] = {}

        for theory in theories:
            # 1) 标准化聚合（统一变体）
            merged = TheoryQueryHelper.merge_theory_results(self.db, theory)
            usage_count = merged.get('usage_count', 0)
            matched_cases = merged.get('cases', [])

            if usage_count > 0:
                freq_rank, rank_emoji = self._get_frequency_info(usage_count)
                exact_results[theory] = {
                    'theory_name': merged.get('theory_name', theory),
                    'match_count': usage_count,
                    'frequency_rank': freq_rank,
                    'rank_emoji': rank_emoji,
                    'cases': matched_cases,
                    'match_type': 'normalized'
                }
                logger.debug(
                    f"  标准化: {theory} -> {merged.get('theory_name', theory)}: {usage_count} 次 - {freq_rank}"
                )
                continue

            # 2) 模糊到库内某名称，再做标准化聚合
            fuzzy_matched = self._fuzzy_match_theory(theory)
            if fuzzy_matched:
                merged2 = TheoryQueryHelper.merge_theory_results(self.db, fuzzy_matched)
                fuzzy_count = merged2.get('usage_count', 0)
                if fuzzy_count > 0:
                    freq_rank, rank_emoji = self._get_frequency_info(fuzzy_count)
                    fuzzy_results[theory] = {
                        'input_theory': theory,
                        'matched_theory': merged2.get('theory_name', fuzzy_matched),
                        'match_count': fuzzy_count,
                        'frequency_rank': freq_rank,
                        'rank_emoji': rank_emoji,
                        'cases': merged2.get('cases', []),
                        'match_type': 'fuzzy+normalized'
                    }
                    logger.debug(
                        f"  模糊: {theory} -> {merged2.get('theory_name', fuzzy_matched)}: {fuzzy_count} 次 - {freq_rank}"
                    )
                else:
                    logger.debug(f"  未匹配: {theory}")
            else:
                logger.debug(f"  未匹配: {theory}")

        logger.success(f"匹配完成: 标准化 {len(exact_results)} 项, 模糊 {len(fuzzy_results)} 项")
        return exact_results, fuzzy_results

    def _get_frequency_info(self, count: int) -> Tuple[str, str]:
        if count >= settings.HIGH_FREQ_MIN_USAGE:
            return '经典理论', '🔥'
        elif count > settings.NOVEL_MAX_USAGE:
            return '常见理论', '✅'
        else:
            return '新颖理论', '🆕'

    def get_frequency_distribution(self, theories: List[str]) -> Dict[str, int]:
        exact_results, fuzzy_results = self.match_theories(theories)
        distribution = {'novel': 0, 'common': 0, 'high_freq': 0}
        for result in {**exact_results, **fuzzy_results}.values():
            c = result['match_count']
            if c <= settings.NOVEL_MAX_USAGE:
                distribution['novel'] += 1
            elif c < settings.HIGH_FREQ_MIN_USAGE:
                distribution['common'] += 1
            else:
                distribution['high_freq'] += 1
        return distribution
