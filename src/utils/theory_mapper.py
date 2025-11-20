"""自动理论映射构建器

从数据库与Excel提取的理论名称中，自动聚类出标准名称及其变体映射，
写入 data/theory_mapping.yaml 供运行时加载使用。
"""

from typing import Dict, List, Set, Tuple
from pathlib import Path
import re
from collections import defaultdict, Counter

from loguru import logger
from fuzzywuzzy import fuzz

from ..config import settings
from ..data.database import Database


_CN_SUFFIXES = [
    "分析法", "分析模型", "分析", "模型", "理论", "矩阵", "策略", "战略", "方法", "体系", "框架", "模式"
]


def _normalize_text(s: str) -> str:
    s = (s or "").strip()
    # 标准化空白与符号
    s = re.sub(r"[\u3000\s]+", " ", s)
    s = s.replace("（", "(").replace("）", ")").replace("，", ",").replace("。", ".")
    return s


def _extract_english_acronym(s: str) -> str:
    # 提取连续英文字母组成的首要缩写（如 SWOT / PEST / BCG / BSC）
    tokens = re.findall(r"[A-Za-z]+", s)
    if not tokens:
        return ""
    # 选择长度2-6的最长（或第一个大写）
    upper_tokens = [t.upper() for t in tokens if 2 <= len(t) <= 6]
    # 如果存在全大写，优先
    for t in tokens:
        if t.isupper() and 2 <= len(t) <= 6:
            return t
    return upper_tokens[0] if upper_tokens else ""


def _strip_cn_suffixes(s: str) -> str:
    base = s
    for suf in _CN_SUFFIXES:
        if base.endswith(suf):
            base = base[: -len(suf)]
    return base


def _chinese_core(s: str) -> str:
    # 提取中文核心：去掉后缀、去掉非中英文与数字
    s = _normalize_text(s)
    s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s)
    s = _strip_cn_suffixes(s)
    return s


def _signature(name: str) -> Tuple[str, str]:
    """生成用于分组的签名：(英文缩写/英文核心, 中文核心)
    任一维度匹配即可归为同组，再结合模糊阈值二次合并。
    """
    s = _normalize_text(name)
    acronym = _extract_english_acronym(s)
    cn_core = _chinese_core(s)
    return (acronym, cn_core)


def _choose_canonical(variants: List[str]) -> str:
    # 选择规范名策略：优先中文字符多者；若并列，选择长度更长者；再按出现频率、字典序
    def score(v: str) -> Tuple[int, int, int, str]:
        cn_count = len(re.findall(r"[\u4e00-\u9fff]", v))
        return (cn_count, len(v), variants.count(v), v)

    return sorted(variants, key=score, reverse=True)[0]


def _pairwise_merge(groups: List[List[str]], ratio_threshold: int = 90) -> List[List[str]]:
    # 通过模糊匹配做二次合并，避免近似拼写分裂
    merged: List[List[str]] = []
    for g in groups:
        placed = False
        for mg in merged:
            # 任意一对达到阈值则合并
            if any(fuzz.ratio(a.lower(), b.lower()) >= ratio_threshold for a in g for b in mg):
                mg.extend(g)
                placed = True
                break
        if not placed:
            merged.append(list(g))
    return merged


def build_theory_mapping(db: Database, extra_theories: List[str] = None) -> Dict[str, List[str]]:
    """从数据库与额外来源（如Excel）自动生成 映射：标准名 -> 变体列表
    """
    names: List[str] = db.get_all_theory_names()
    if extra_theories:
        names.extend(extra_theories)
    names = [n for n in names if isinstance(n, str) and n.strip()]
    names = list(dict.fromkeys(names))  # 去重保持顺序

    # 1) 按签名粗分组
    buckets: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for n in names:
        buckets[_signature(n)].append(n)

    # 2) 对每个桶做模糊合并
    initial_groups = list(buckets.values())
    coarse_merged = _pairwise_merge(initial_groups, ratio_threshold=92)

    # 3) 生成映射
    mapping: Dict[str, List[str]] = {}
    for group in coarse_merged:
        group = list(dict.fromkeys(group))
        canonical = _choose_canonical(group)
        # 将规范名放首位
        variants_sorted = [canonical] + [v for v in group if v != canonical]
        mapping[canonical] = variants_sorted

    logger.info(f"自动映射生成完成：{len(mapping)} 个标准名称，{len(names)} 个原始名称")
    return mapping


def save_mapping_yaml(mapping: Dict[str, List[str]], path: str = None):
    out_path = Path(path or settings.THEORY_MAPPING_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "mappings": {k: list(v) for k, v in mapping.items()}
    }
    out_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=True), encoding='utf-8')
    logger.success(f"理论映射已写入: {out_path}")

