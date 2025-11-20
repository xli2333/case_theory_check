"""PDF文本提取模块"""

import pdfplumber
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger
from tqdm import tqdm


class PDFProcessor:
    """PDF文本提取器"""

    @staticmethod
    def extract_text(pdf_path: str, max_pages: Optional[int] = None) -> str:
        """
        提取PDF全文

        Args:
            pdf_path: PDF文件路径
            max_pages: 最大页数限制 (None表示全部)

        Returns:
            提取的文本内容
        """
        text_parts = []

        try:
            logger.info(f"开始提取PDF: {pdf_path}")
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"  PDF总页数: {total_pages}")
                pages_to_process = min(total_pages, max_pages) if max_pages else total_pages

                for i in range(pages_to_process):
                    page = pdf.pages[i]
                    page_text = page.extract_text()

                    if page_text:
                        text_parts.append(page_text)
                        logger.debug(f"  第{i+1}页提取: {len(page_text)}字符")
                    else:
                        logger.warning(f"  第{i+1}页提取失败")

            result = '\n'.join(text_parts)
            logger.info(f"PDF提取完成: 总共{len(result)}字符")
            return result

        except Exception as e:
            logger.error(f"提取PDF失败 {pdf_path}: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            return ""

    @staticmethod
    def extract_key_sections(pdf_path: str, max_length: int = 3000) -> Dict[str, str]:
        """
        提取PDF关键部分

        Args:
            pdf_path: PDF文件路径
            max_length: 最大字符数

        Returns:
            包含title, abstract, body的字典
        """
        full_text = PDFProcessor.extract_text(pdf_path)

        # 提取文件名作为标题
        title = Path(pdf_path).stem

        # 简单实现: 前500字作为摘要,前3000字作为关键内容
        # 实际项目中可以智能识别标题、摘要、正文等

        return {
            'title': title,
            'abstract': full_text[:500] if full_text else '',
            'body': full_text[:max_length] if full_text else '',
            'full_text': full_text,
            'length': len(full_text)
        }

    @staticmethod
    def extract_metadata(pdf_path: str) -> Dict[str, any]:
        """
        提取PDF元数据

        Args:
            pdf_path: PDF文件路径

        Returns:
            元数据字典
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata = pdf.metadata or {}

                return {
                    'title': metadata.get('Title', ''),
                    'author': metadata.get('Author', ''),
                    'subject': metadata.get('Subject', ''),
                    'creator': metadata.get('Creator', ''),
                    'producer': metadata.get('Producer', ''),
                    'creation_date': metadata.get('CreationDate', ''),
                    'total_pages': len(pdf.pages)
                }

        except Exception as e:
            logger.error(f"提取PDF元数据失败 {pdf_path}: {e}")
            return {}

    @staticmethod
    def process_case_folder(folder_path: str, pattern: str = '*.pdf') -> Dict[str, Dict[str, str]]:
        """
        处理案例文件夹中的所有PDF

        Args:
            folder_path: 文件夹路径
            pattern: 文件匹配模式

        Returns:
            {文件名: 提取内容}
        """
        folder = Path(folder_path)

        if not folder.exists():
            logger.warning(f"文件夹不存在: {folder_path}")
            return {}

        pdf_files = list(folder.glob(pattern))

        if not pdf_files:
            logger.warning(f"未找到PDF文件: {folder_path}")
            return {}

        logger.info(f"处理文件夹: {folder_path}, 发现 {len(pdf_files)} 个PDF")

        results = {}

        for pdf_file in tqdm(pdf_files, desc="处理PDF"):
            try:
                case_name = pdf_file.stem
                content = PDFProcessor.extract_key_sections(str(pdf_file))
                results[case_name] = content
                logger.debug(f"处理完成: {case_name} ({content['length']} 字符)")

            except Exception as e:
                logger.error(f"处理PDF失败 {pdf_file.name}: {e}")
                continue

        return results

    @staticmethod
    def batch_process_all_years(base_path: str = '.') -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        批量处理所有年份的案例PDF

        Args:
            base_path: 案例库根目录

        Returns:
            {年份: {案例名: 内容}}
        """
        base_path = Path(base_path)
        results = {}

        years = ['FDC-21', 'FDC-22', 'FDC-23', 'FDC-24', 'FDC-25']

        for year in years:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"处理 {year} 案例PDF")
            logger.info('=' * 60)

            # 查找案例原稿文件夹
            case_folders = [
                base_path / year / f'{year}案例统计原文',
                base_path / year / '案例统计原文',
                base_path / year / '案例原稿'
            ]

            case_folder = None
            for folder in case_folders:
                if folder.exists():
                    case_folder = folder
                    break

            if case_folder:
                year_results = PDFProcessor.process_case_folder(str(case_folder))
                results[year] = year_results
                logger.success(f"✓ {year}: 处理 {len(year_results)} 个案例PDF")
            else:
                logger.warning(f"! {year}: 未找到案例PDF文件夹")
                results[year] = {}

        # 总计
        total_cases = sum(len(cases) for cases in results.values())
        logger.info(f"\n总计处理 {total_cases} 个案例PDF")

        return results


class CaseTextExtractor:
    """案例文本提取器 (整合Excel和PDF)"""

    def __init__(self, db):
        """
        初始化提取器

        Args:
            db: 数据库实例
        """
        self.db = db

    def update_cases_with_pdf_text(self, pdf_results: Dict[str, Dict[str, Dict[str, str]]]):
        """
        用PDF文本更新案例数据库

        Args:
            pdf_results: 从batch_process_all_years获得的结果
        """
        logger.info("开始更新案例的PDF文本...")

        total_updated = 0

        for year, cases in pdf_results.items():
            logger.info(f"处理 {year}: {len(cases)} 个案例")

            for case_name, content in cases.items():
                try:
                    # 尝试通过案例名称或编号匹配
                    # 方法1: 通过年份和名称模糊匹配
                    all_cases = self.db.get_all_cases(year=year)

                    matched_case = None
                    for case in all_cases:
                        # 简单匹配: 案例名称包含在PDF文件名中
                        if case.name and (case.name in case_name or case_name in case.name):
                            matched_case = case
                            break

                    if matched_case:
                        # 更新数据库中的full_text字段
                        with self.db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE cases
                                SET full_text = ?, pdf_path = ?
                                WHERE id = ?
                            """, (content['full_text'], case_name + '.pdf', matched_case.id))

                        total_updated += 1
                        logger.debug(f"更新案例: {matched_case.name} (ID: {matched_case.id})")

                except Exception as e:
                    logger.warning(f"更新案例 {case_name} 失败: {e}")
                    continue

        logger.success(f"✓ 共更新 {total_updated} 个案例的PDF文本")

        return total_updated


def extract_and_save_all_pdfs(base_path: str = '.', db_path: Optional[str] = None) -> int:
    """
    便捷函数: 提取所有PDF并保存到数据库

    Args:
        base_path: 案例库根目录
        db_path: 数据库路径

    Returns:
        更新的案例数量
    """
    from .database import Database

    # 1. 批量提取PDF
    logger.info("步骤1: 批量提取PDF文本...")
    pdf_results = PDFProcessor.batch_process_all_years(base_path)

    # 2. 更新数据库
    logger.info("\n步骤2: 更新数据库...")
    db = Database(db_path)
    extractor = CaseTextExtractor(db)
    updated_count = extractor.update_cases_with_pdf_text(pdf_results)

    return updated_count
