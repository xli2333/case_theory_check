"""理论名称标准化工具（支持动态映射）"""

from typing import Dict, List
from pathlib import Path
import yaml

from ..config import settings


class TheoryNormalizer:
    """理论名称标准化器 - 支持内置与动态映射。

    - 动态映射文件默认路径：data/theory_mapping.yaml（由映射脚本生成）
    - 归一化时大小写不敏感
    """

    # 内置基础映射（兜底）
    BUILTIN_MAPPING: Dict[str, List[str]] = {
        "SWOT分析": ["SWOT分析", "SWOT Analysis", "swot分析", "SWOT", "swot"],
        "波特五力模型": ["波特五力", "波特五力模型", "波特五力分析", "五力模型", "Porter's Five Forces"],
        "4P营销理论": ["4P", "4P营销", "4P理论", "4Ps", "营销4P"],
        "蓝海战略": ["蓝海战略", "蓝海理论", "蓝海策略", "Blue Ocean Strategy"],
        "PEST分析": ["PEST", "PEST分析", "PEST模型", "PEST Analysis"],
        "价值链分析": ["价值链", "价值链分析", "波特价值链", "价值链理论"],
        "BCG矩阵": ["BCG", "BCG矩阵", "BCG分析", "Boston Matrix"],
        "平衡计分卡": ["BSC", "平衡计分卡", "Balanced Scorecard"],
        "商业模式画布": ["BMC", "商业模式画布", "Business Model Canvas", "商业画布"],
        "精益创业": ["精益创业", "Lean Startup", "精益创新"],
        "长尾理论": ["长尾", "长尾理论", "长尾效应", "Long Tail"],
    }

    _dynamic_mapping: Dict[str, List[str]] = {}
    _reverse_mapping: Dict[str, str] = None  # 变体（lower）-> 标准

    @classmethod
    def _load_dynamic_mapping_if_exists(cls):
        path = Path(settings.THEORY_MAPPING_PATH)
        if not path.exists():
            cls._dynamic_mapping = {}
            return
        try:
            data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
            mappings = data.get('mappings', data)
            cleaned: Dict[str, List[str]] = {}
            if isinstance(mappings, dict):
                for k, v in mappings.items():
                    if isinstance(k, str) and isinstance(v, list):
                        cleaned[k] = [str(x) for x in v if isinstance(x, (str, int, float))]
            cls._dynamic_mapping = cleaned
        except Exception:
            cls._dynamic_mapping = {}

    @classmethod
    def load_dynamic_mapping(cls, path: str = None):
        try:
            if path:
                p = Path(path)
                data = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
                mappings = data.get('mappings', data)
                cleaned: Dict[str, List[str]] = {}
                if isinstance(mappings, dict):
                    for k, v in mappings.items():
                        if isinstance(k, str) and isinstance(v, list):
                            cleaned[k] = [str(x) for x in v if isinstance(x, (str, int, float))]
                TheoryNormalizer._dynamic_mapping = cleaned
            else:
                cls._load_dynamic_mapping_if_exists()
        except Exception:
            cls._dynamic_mapping = {}
        finally:
            cls._reverse_mapping = None

    @classmethod
    def _build_reverse_mapping(cls):
        if cls._reverse_mapping is not None:
            return
        cls._load_dynamic_mapping_if_exists()
        reverse: Dict[str, str] = {}
        # 动态映射优先
        for std, variants in cls._dynamic_mapping.items():
            for v in variants + [std]:
                reverse[str(v).lower().strip()] = std
        # 再补充内置映射
        for std, variants in cls.BUILTIN_MAPPING.items():
            for v in variants + [std]:
                key = str(v).lower().strip()
                reverse.setdefault(key, std)
        cls._reverse_mapping = reverse

    @classmethod
    def normalize(cls, theory_name: str) -> str:
        cls._build_reverse_mapping()
        return cls._reverse_mapping.get(str(theory_name).lower().strip(), theory_name)

    @classmethod
    def normalize_list(cls, theory_list: List[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for t in theory_list or []:
            n = cls.normalize(t)
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result

    @classmethod
    def get_all_variants(cls, standard_name: str) -> List[str]:
        cls._build_reverse_mapping()
        if standard_name in cls._dynamic_mapping:
            return cls._dynamic_mapping.get(standard_name, []) + [standard_name]
        return cls.BUILTIN_MAPPING.get(standard_name, []) + [standard_name]

    @classmethod
    def is_variant_of(cls, theory_name: str, standard_name: str) -> bool:
        return cls.normalize(theory_name) == standard_name

    @classmethod
    def get_standard_names(cls) -> List[str]:
        cls._build_reverse_mapping()
        names = set(cls.BUILTIN_MAPPING.keys()) | set(cls._dynamic_mapping.keys())
        return sorted(names)

    @classmethod
    def add_mapping(cls, standard_name: str, variants: List[str]):
        cls._dynamic_mapping[standard_name] = variants
        cls._reverse_mapping = None

    @classmethod
    def get_mapping_stats(cls) -> Dict:
        cls._build_reverse_mapping()
        return {
            "standard_names_count": len(cls.get_standard_names()),
            "total_variants_count": len(cls._reverse_mapping),
            "dynamic": len(cls._dynamic_mapping) > 0
        }

