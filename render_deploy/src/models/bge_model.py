"""BGE-M3模型封装"""

import numpy as np
from typing import List, Union, Optional
import torch
from loguru import logger

from ..config import settings, get_device


class BGEModel:
    """BGE-M3模型封装"""

    def __init__(self,
                 model_name: Optional[str] = None,
                 cache_dir: Optional[str] = None,
                 use_fp16: Optional[bool] = None,
                 device: Optional[str] = None):
        """
        初始化BGE-M3模型

        Args:
            model_name: 模型名称
            cache_dir: 缓存目录
            use_fp16: 是否使用半精度
            device: 设备 (cuda/mps/cpu)
        """
        self.model_name = model_name or settings.BGE_MODEL_NAME
        self.cache_dir = cache_dir or str(settings.model_cache_dir_abs)
        self.use_fp16 = use_fp16 if use_fp16 is not None else settings.USE_FP16
        self.device = device or get_device()

        logger.info(f"初始化BGE-M3模型...")
        logger.info(f"  模型: {self.model_name}")
        logger.info(f"  缓存: {self.cache_dir}")
        logger.info(f"  设备: {self.device}")
        logger.info(f"  FP16: {self.use_fp16}")

        self._load_model()

    def _load_model(self):
        """加载模型"""
        try:
            from FlagEmbedding import BGEM3FlagModel

            # 创建缓存目录
            import os
            os.makedirs(self.cache_dir, exist_ok=True)

            # 设置环境变量
            os.environ['HF_HOME'] = self.cache_dir
            os.environ['TRANSFORMERS_CACHE'] = self.cache_dir

            logger.info("正在加载模型 (首次运行需要下载，约600MB)...")

            self.model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16,
                device=self.device
            )

            logger.success("✓ BGE-M3模型加载完成")

            # 测试编码
            test_text = "测试文本"
            test_result = self.model.encode(
                test_text,
                max_length=128,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False
            )

            logger.info(f"  向量维度: {len(test_result['dense_vecs'])}")
            logger.success("✓ 模型测试通过")

        except ImportError as e:
            logger.error("FlagEmbedding库未安装")
            logger.error("请运行: pip install FlagEmbedding")
            raise

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def encode_single(self,
                     text: str,
                     max_length: Optional[int] = None) -> np.ndarray:
        """
        编码单个文本

        Args:
            text: 输入文本
            max_length: 最大长度

        Returns:
            向量表示 (1024维)
        """
        if not text or not text.strip():
            logger.warning("空文本，返回零向量")
            return np.zeros(1024)

        max_length = max_length or settings.MAX_LENGTH

        try:
            result = self.model.encode(
                text,
                max_length=max_length,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False
            )

            return result['dense_vecs']

        except Exception as e:
            logger.error(f"编码失败: {e}")
            return np.zeros(1024)

    def encode_batch(self,
                    texts: List[str],
                    max_length: Optional[int] = None,
                    batch_size: Optional[int] = None,
                    show_progress: bool = True) -> List[np.ndarray]:
        """
        批量编码文本

        Args:
            texts: 文本列表
            max_length: 最大长度
            batch_size: 批次大小
            show_progress: 是否显示进度

        Returns:
            向量列表
        """
        if not texts:
            return []

        max_length = max_length or settings.MAX_LENGTH
        batch_size = batch_size or settings.BATCH_SIZE

        logger.info(f"批量编码 {len(texts)} 个文本...")

        embeddings = []

        try:
            from tqdm import tqdm

            # 分批处理
            for i in tqdm(range(0, len(texts), batch_size),
                         desc="编码进度",
                         disable=not show_progress):
                batch = texts[i:i + batch_size]

                # 过滤空文本
                valid_batch = [t if t and t.strip() else "空" for t in batch]

                result = self.model.encode(
                    valid_batch,
                    max_length=max_length,
                    batch_size=len(valid_batch),
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False
                )

                embeddings.extend(result['dense_vecs'])

            logger.success(f"✓ 编码完成: {len(embeddings)} 个向量")
            return embeddings

        except Exception as e:
            logger.error(f"批量编码失败: {e}")
            return [np.zeros(1024) for _ in texts]

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度

        Args:
            text1, text2: 输入文本

        Returns:
            余弦相似度 (0-1)
        """
        emb1 = self.encode_single(text1)
        emb2 = self.encode_single(text2)

        # 余弦相似度
        similarity = np.dot(emb1, emb2) / (
            np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8
        )

        return float(similarity)

    def compute_similarities(self,
                           query: str,
                           texts: List[str]) -> List[float]:
        """
        计算查询与多个文本的相似度

        Args:
            query: 查询文本
            texts: 文本列表

        Returns:
            相似度列表
        """
        query_emb = self.encode_single(query)
        text_embs = self.encode_batch(texts, show_progress=False)

        similarities = []
        for text_emb in text_embs:
            sim = np.dot(query_emb, text_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(text_emb) + 1e-8
            )
            similarities.append(float(sim))

        return similarities


# 全局模型实例 (单例模式)
_global_model: Optional[BGEModel] = None


def get_bge_model() -> BGEModel:
    """
    获取全局BGE模型实例 (单例模式)

    Returns:
        BGE模型实例
    """
    global _global_model

    if _global_model is None:
        _global_model = BGEModel()

    return _global_model
