"""综合评分算法（含创新度评分阈值配置）"""

from typing import Dict, List
import numpy as np
from loguru import logger

from ..config import settings


class ComprehensiveScorer:
    """综合评分器 - 多维度加权合成"""

    def __init__(self):
        self.weights = {
            'theory_overlap': settings.THEORY_OVERLAP_WEIGHT,
            'semantic_similarity': settings.SEMANTIC_SIMILARITY_WEIGHT,
            'keyword_similarity': settings.KEYWORD_SIMILARITY_WEIGHT,
            'domain_similarity': settings.DOMAIN_SIMILARITY_WEIGHT,
        }
        logger.debug(f"综合评分器权重: {self.weights}")

    def compute_comprehensive_score(self,
                                    new_case: Dict,
                                    matched_case: Dict,
                                    exact_matches: Dict,
                                    semantic_score: float) -> Dict:
        # 1) 理论重叠
        new_theories = set(new_case.get('theories', []) or [])
        matched_theories_list = matched_case.get('theories', '')
        if isinstance(matched_theories_list, str):
            matched_theories = set(matched_theories_list.split(',')) if matched_theories_list else set()
        else:
            matched_theories = set(matched_theories_list or [])
        theory_overlap = (len(new_theories & matched_theories) / len(new_theories)) if new_theories else 0.0

        # 2) 语义相似
        semantic_similarity = float(semantic_score or 0.0)

        # 3) 关键词相似（Jaccard）
        keyword_similarity = self._calculate_keyword_similarity(
            new_case.get('keywords', ''), matched_case.get('keywords', '')
        )

        # 4) 领域相似（学科/行业）
        domain_similarity = self._calculate_domain_similarity(new_case, matched_case)

        # 5) 加权合成
        final_score = (
            theory_overlap * self.weights['theory_overlap'] +
            semantic_similarity * self.weights['semantic_similarity'] +
            keyword_similarity * self.weights['keyword_similarity'] +
            domain_similarity * self.weights['domain_similarity']
        )

        return {
            'final_score': final_score,
            'theory_overlap': theory_overlap,
            'semantic_similarity': semantic_similarity,
            'keyword_similarity': keyword_similarity,
            'domain_similarity': domain_similarity,
            'matched_theories': list(new_theories & matched_theories),
        }

    def _calculate_keyword_similarity(self, keywords1: str, keywords2: str) -> float:
        if not keywords1 or not keywords2:
            return 0.0
        def split_kw(s: str) -> List[str]:
            s = (s or '').replace('；', ',').replace(';', ',').replace('，', ',')
            return [k.strip() for k in s.split(',') if k and k.strip()]
        kw1 = set(split_kw(keywords1))
        kw2 = set(split_kw(keywords2))
        if not kw1 or not kw2:
            return 0.0
        inter = len(kw1 & kw2)
        union = len(kw1 | kw2)
        return inter / union if union > 0 else 0.0

    def _calculate_domain_similarity(self, case1: Dict, case2: Dict) -> float:
        score = 0.0
        if case1.get('industry') and case2.get('industry') and case1['industry'] == case2['industry']:
            score += 0.5
        if case1.get('subject') and case2.get('subject') and case1['subject'] == case2['subject']:
            score += 0.5
        return score

    def calculate_innovation_score(self, new_case: Dict, exact_matches: Dict) -> Dict:
        """按出现频次阈值（可配置）计算创新度"""
        theories = new_case.get('theories', []) or []
        if not theories:
            return {
                'innovation_score': 0,
                'novel_theories': [],
                'common_theories': [],
                'high_frequency_theories': [],
                'novel_ratio': 0,
                'common_ratio': 0,
                'high_freq_ratio': 0,
            }

        novel: List[str] = []
        common: List[str] = []
        high_freq: List[str] = []

        for t in theories:
            c = (exact_matches.get(t, {}) or {}).get('match_count', 0)
            if c <= settings.NOVEL_MAX_USAGE:
                novel.append(t)
            elif c < settings.HIGH_FREQ_MIN_USAGE:
                common.append(t)
            else:
                high_freq.append(t)

        total = len(theories)
        score = (
            (len(novel) / total) * 100 * 1.0 +
            (len(common) / total) * 100 * 0.5 +
            (len(high_freq) / total) * 100 * 0.2
        ) if total > 0 else 0.0

        return {
            'innovation_score': round(score, 1),
            'novel_theories': novel,
            'common_theories': common,
            'high_frequency_theories': high_freq,
            'novel_ratio': len(novel) / total if total else 0,
            'common_ratio': len(common) / total if total else 0,
            'high_freq_ratio': len(high_freq) / total if total else 0,
        }

    def rank_similar_cases(self,
                           new_case: Dict,
                           semantic_matches: List[Dict],
                           exact_matches: Dict,
                           top_k: int = 10) -> List[Dict]:
        logger.info("计算综合评分并排序...")
        scored = []
        for match in semantic_matches:
            metadata = match.get('metadata', {})
            sem = float(match.get('similarity', 0))
            scores = self.compute_comprehensive_score(new_case, metadata, exact_matches, sem)
            scored.append({'case_id': match.get('case_id'), 'metadata': metadata, 'scores': scores})
        scored.sort(key=lambda x: x['scores']['final_score'], reverse=True)
        top = scored[:top_k]
        logger.success(f"综合排序完成，Top-{len(top)}")
        return top
