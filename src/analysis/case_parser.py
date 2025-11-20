"""新案例解析器"""

from typing import Dict, List, Optional
import re
from loguru import logger


class CaseParser:
    """新案例解析器 - 从文本中提取案例信息"""

    @staticmethod
    def parse_text(text: str) -> Dict:
        """
        解析纯文本案例

        Args:
            text: 案例文本

        Returns:
            解析后的案例数据
        """
        logger.info("解析文本案例...")

        case_data = {
            'name': '',
            'abstract': '',
            'keywords': '',
            'theories': [],
            'full_text': text,
            'subject': '',
            'industry': '',
            'author': ''
        }

        # 简单实现: 提取前500字作为摘要
        case_data['abstract'] = text[:500] if len(text) > 500 else text

        # TODO: 可以添加更智能的解析逻辑
        # - 识别标题
        # - 提取关键词
        # - 识别理论引用

        logger.info(f"  文本长度: {len(text)} 字符")

        return case_data

    @staticmethod
    def extract_theories_from_text(text: str, known_theories: List[str]) -> List[str]:
        """
        从文本中提取理论 (基于已知理论列表匹配)

        Args:
            text: 案例文本
            known_theories: 已知理论列表

        Returns:
            识别出的理论列表
        """
        logger.info("提取文本中的理论...")

        identified_theories = []

        for theory in known_theories:
            # 精确匹配
            if theory in text:
                identified_theories.append(theory)

        logger.info(f"  识别出 {len(identified_theories)} 个理论")

        return identified_theories
