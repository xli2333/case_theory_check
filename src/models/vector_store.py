"""向量数据库封装 (ChromaDB)"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Optional, Any
import numpy as np
from loguru import logger

from ..config import settings


class VectorStore:
    """向量数据库封装 (ChromaDB)"""

    def __init__(self,
                 persist_directory: Optional[str] = None,
                 collection_name: str = "case_embeddings"):
        """
        初始化向量数据库

        Args:
            persist_directory: 持久化目录
            collection_name: 集合名称
        """
        self.persist_directory = persist_directory or str(settings.vector_db_path_abs)
        self.collection_name = collection_name

        # 创建目录
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        logger.info(f"初始化ChromaDB向量数据库...")
        logger.info(f"  路径: {self.persist_directory}")
        logger.info(f"  集合: {collection_name}")

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(name=collection_name)
            count = self.collection.count()
            logger.info(f"✓ 加载现有集合: {count} 个向量")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "案例语义向量索引"}
            )
            logger.info("✓ 创建新集合")

    def add_case(self,
                case_id: str,
                embedding: np.ndarray,
                case_text: str,
                metadata: Dict[str, Any]):
        """
        添加单个案例向量

        Args:
            case_id: 案例ID (唯一标识)
            embedding: 向量
            case_text: 案例文本
            metadata: 元数据
        """
        try:
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[case_text],
                metadatas=[metadata],
                ids=[case_id]
            )
            logger.debug(f"添加案例: {case_id}")

        except Exception as e:
            logger.error(f"添加案例失败 {case_id}: {e}")

    def add_cases_batch(self,
                       case_ids: List[str],
                       embeddings: List[np.ndarray],
                       case_texts: List[str],
                       metadatas: List[Dict[str, Any]]):
        """
        批量添加案例

        Args:
            case_ids: 案例ID列表
            embeddings: 向量列表
            case_texts: 文本列表
            metadatas: 元数据列表
        """
        if not case_ids:
            logger.warning("批量添加: 空列表")
            return

        logger.info(f"批量添加 {len(case_ids)} 个案例向量...")

        try:
            self.collection.add(
                embeddings=[emb.tolist() for emb in embeddings],
                documents=case_texts,
                metadatas=metadatas,
                ids=case_ids
            )
            logger.success(f"✓ 批量添加完成: {len(case_ids)} 个向量")

        except Exception as e:
            logger.error(f"批量添加失败: {e}")

    def upsert_case(self,
                   case_id: str,
                   embedding: np.ndarray,
                   case_text: str,
                   metadata: Dict[str, Any]):
        """
        更新或插入案例 (如果存在则更新,否则插入)

        Args:
            case_id: 案例ID
            embedding: 向量
            case_text: 案例文本
            metadata: 元数据
        """
        try:
            self.collection.upsert(
                embeddings=[embedding.tolist()],
                documents=[case_text],
                metadatas=[metadata],
                ids=[case_id]
            )
            logger.debug(f"Upsert案例: {case_id}")

        except Exception as e:
            logger.error(f"Upsert失败 {case_id}: {e}")

    def search_similar(self,
                      query_embedding: np.ndarray,
                      n_results: int = 10,
                      where: Optional[Dict] = None,
                      where_document: Optional[Dict] = None) -> Dict:
        """
        搜索相似案例

        Args:
            query_embedding: 查询向量
            n_results: 返回结果数
            where: 元数据过滤条件
            where_document: 文档内容过滤条件

        Returns:
            搜索结果
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                where=where,
                where_document=where_document
            )

            return results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {'ids': [[]], 'distances': [[]], 'metadatas': [[]], 'documents': [[]]}

    def get_by_id(self, case_id: str) -> Optional[Dict]:
        """
        根据ID获取案例

        Args:
            case_id: 案例ID

        Returns:
            案例数据
        """
        try:
            result = self.collection.get(
                ids=[case_id],
                include=['embeddings', 'documents', 'metadatas']
            )

            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'embedding': result['embeddings'][0] if result.get('embeddings') else None,
                    'document': result['documents'][0] if result.get('documents') else None,
                    'metadata': result['metadatas'][0] if result.get('metadatas') else None
                }

            return None

        except Exception as e:
            logger.error(f"获取案例失败 {case_id}: {e}")
            return None

    def delete_case(self, case_id: str):
        """删除案例"""
        try:
            self.collection.delete(ids=[case_id])
            logger.debug(f"删除案例: {case_id}")

        except Exception as e:
            logger.error(f"删除失败 {case_id}: {e}")

    def count(self) -> int:
        """获取向量数量"""
        try:
            return self.collection.count()
        except:
            return 0

    def clear(self):
        """清空集合"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "案例语义向量索引"}
            )
            logger.warning("⚠ 集合已清空")

        except Exception as e:
            logger.error(f"清空失败: {e}")

    def reset(self):
        """重置数据库 (危险操作!)"""
        try:
            self.client.reset()
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "案例语义向量索引"}
            )
            logger.warning("⚠⚠⚠ 数据库已重置")

        except Exception as e:
            logger.error(f"重置失败: {e}")


# 全局向量存储实例 (单例模式)
_global_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    获取全局向量存储实例 (单例模式)

    Returns:
        向量存储实例
    """
    global _global_vector_store

    if _global_vector_store is None:
        _global_vector_store = VectorStore()

    return _global_vector_store
