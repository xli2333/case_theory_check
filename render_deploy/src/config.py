"""配置管理模块"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import yaml


class Settings(BaseSettings):
    """系统配置"""

    # 基础路径
    BASE_DIR: Path = Path(__file__).parent.parent

    # 数据库配置
    DATABASE_PATH: str = Field(
        default="data/database/cases.db",
        description="SQLite数据库路径"
    )
    VECTOR_DB_PATH: str = Field(
        default="data/database/vectors",
        description="向量数据库路径"
    )

    # 模型配置
    MODEL_CACHE_DIR: str = Field(
        default="data/models",
        description="模型缓存目录"
    )
    BGE_MODEL_NAME: str = Field(
        default="BAAI/bge-m3",
        description="BGE模型名称"
    )
    USE_FP16: bool = Field(
        default=True,
        description="是否使用半精度"
    )
    MAX_LENGTH: int = Field(
        default=8192,
        description="最大文本长度"
    )
    BATCH_SIZE: int = Field(
        default=12,
        description="批处理大小"
    )
    DEVICE: str = Field(
        default="cpu",
        description="计算设备 (auto/cpu/cuda)"
    )

    # API配置
    API_HOST: str = Field(
        default="0.0.0.0",
        description="API主机"
    )
    API_PORT: int = Field(
        default=8000,
        description="API端口"
    )

    # Web配置
    WEB_HOST: str = Field(
        default="0.0.0.0",
        description="Web主机"
    )
    WEB_PORT: int = Field(
        default=8501,
        description="Web端口"
    )

    # 日志配置
    LOG_LEVEL: str = Field(
        default="INFO",
        description="日志级别"
    )
    LOG_FILE: str = Field(
        default="data/logs/app.log",
        description="日志文件路径"
    )

    # 匹配配置
    THEORY_OVERLAP_WEIGHT: float = 0.40
    SEMANTIC_SIMILARITY_WEIGHT: float = 0.30
    KEYWORD_SIMILARITY_WEIGHT: float = 0.20
    DOMAIN_SIMILARITY_WEIGHT: float = 0.10

    MIN_SEMANTIC_SIMILARITY: float = 0.5
    FUZZY_MATCH_THRESHOLD: int = 85
    TOP_K: int = 10
    VECTOR_COLLECTION_NAME: str = "case_embeddings"

    # 频率阈值配置（用于新颖/常用/高频分类）
    NOVEL_MAX_USAGE: int = Field(
        default=2,
        description="新颖理论的最大历史使用次数（含）"
    )
    HIGH_FREQ_MIN_USAGE: int = Field(
        default=5,
        description="高频理论的最小历史使用次数（含）"
    )

    # 理论映射文件（由自动映射器生成）
    THEORY_MAPPING_PATH: str = Field(
        default="data/theory_mapping.yaml",
        description="理论标准化映射文件路径"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_abs_path(self, relative_path: str) -> Path:
        """获取绝对路径"""
        path = Path(relative_path)
        if path.is_absolute():
            return path
        return self.BASE_DIR / path

    @property
    def database_path_abs(self) -> Path:
        """数据库绝对路径"""
        return self.get_abs_path(self.DATABASE_PATH)

    @property
    def vector_db_path_abs(self) -> Path:
        """向量数据库绝对路径"""
        return self.get_abs_path(self.VECTOR_DB_PATH)

    @property
    def model_cache_dir_abs(self) -> Path:
        """模型缓存目录绝对路径"""
        return self.get_abs_path(self.MODEL_CACHE_DIR)

    @property
    def log_file_abs(self) -> Path:
        """日志文件绝对路径"""
        return self.get_abs_path(self.LOG_FILE)


# 全局配置实例
settings = Settings()


def load_yaml_config(config_path: str = "config/config.yaml") -> dict:
    """
    从YAML文件加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    config_file = settings.get_abs_path(config_path)

    if not config_file.exists():
        return {}

    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def get_device() -> str:
    """
    自动检测最佳计算设备

    Returns:
        设备名称 (cuda/mps/cpu)
    """
    if settings.DEVICE != "auto":
        return settings.DEVICE

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"
    except ImportError:
        return "cpu"

# 从YAML配置覆盖部分阈值（若存在）
try:
    _yaml_cfg = load_yaml_config()
    _matching = _yaml_cfg.get('matching', {}) if isinstance(_yaml_cfg, dict) else {}
    _thresholds = _matching.get('thresholds', {}) if isinstance(_matching, dict) else {}

    if isinstance(_thresholds, dict):
        novel_max = _thresholds.get('novel_max')
        high_min = _thresholds.get('high_min')
        if isinstance(novel_max, int):
            settings.NOVEL_MAX_USAGE = novel_max
        if isinstance(high_min, int):
            settings.HIGH_FREQ_MIN_USAGE = high_min
except Exception:
    # 配置读取失败时忽略，使用默认值
    pass
