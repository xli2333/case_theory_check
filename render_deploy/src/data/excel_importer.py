"""Excel数据导入模块"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

from .database import Database
from .models import Case, Theory


class ExcelImporter:
    """Excel数据导入器"""

    def __init__(self, db: Database):
        """
        初始化导入器

        Args:
            db: 数据库实例
        """
        self.db = db

    def import_from_excel(self, excel_path: str, year: str) -> Dict[str, int]:
        """
        从Excel导入案例数据

        Args:
            excel_path: Excel文件路径
            year: 年份 (如 FDC-24)

        Returns:
            导入统计 {'cases': 案例数, 'theories': 理论数}
        """
        logger.info(f"开始导入 {year} 的数据: {excel_path}")

        try:
            # 读取Excel (第2行为表头)
            df = pd.read_excel(excel_path, header=1)
            logger.info(f"Excel文件读取成功,共 {len(df)} 行")

        except Exception as e:
            logger.error(f"读取Excel文件失败: {e}")
            raise

        cases_imported = 0
        theories_imported = 0
        current_case = None
        current_case_id = None

        for idx, row in df.iterrows():
            try:
                # 检查是否是新案例 (案例名称不为空)
                if pd.notna(row.get('案例名称')):
                    # 保存上一个案例
                    if current_case:
                        current_case_id = self.db.save_case(current_case)
                        cases_imported += 1
                        logger.debug(f"保存案例: {current_case.name} (ID: {current_case_id})")

                    # 创建新案例
                    current_case = Case(
                        name=str(row['案例名称']),
                        code=str(row['案例编号']) if pd.notna(row.get('案例编号')) else None,
                        year=year,
                        author=str(row['第一作者']) if pd.notna(row.get('第一作者')) else None,
                        co_authors=str(row['其他作者']) if pd.notna(row.get('其他作者')) else None,
                        subject=str(row['学科']) if pd.notna(row.get('学科')) else None,
                        industry=str(row['行业']) if pd.notna(row.get('行业')) else None,
                        publish_date=str(row['出版日期']) if pd.notna(row.get('出版日期')) else None,
                        student_group=str(row['适用学生群体']) if pd.notna(row.get('适用学生群体')) else None,
                        keywords=str(row['关键词']) if pd.notna(row.get('关键词')) else None,
                        abstract=str(row['摘要']) if pd.notna(row.get('摘要')) else None,
                        course=str(row['使用课程']) if pd.notna(row.get('使用课程')) else None,
                        theories=[]
                    )

                # 添加理论 (即使案例名称为空,也可能有理论)
                if current_case and pd.notna(row.get('文章引用理论名称')):
                    theory_name = str(row['文章引用理论名称']).strip()

                    if theory_name:
                        # 查找或创建理论
                        theory = self.db.get_theory_by_name(theory_name)

                        if not theory:
                            theory = Theory(
                                name=theory_name,
                                source=str(row['理论来源/参考文献']) if pd.notna(row.get('理论来源/参考文献')) else None,
                                author=str(row['学者+年份']) if pd.notna(row.get('学者+年份')) else None
                            )
                            theory_id = self.db.save_theory(theory)
                            theories_imported += 1
                            logger.debug(f"新增理论: {theory_name} (ID: {theory_id})")

                        # 添加到当前案例的理论列表
                        if theory_name not in current_case.theories:
                            current_case.theories.append(theory_name)

            except Exception as e:
                logger.warning(f"处理第 {idx + 1} 行时出错: {e}")
                continue

        # 保存最后一个案例
        if current_case:
            current_case_id = self.db.save_case(current_case)
            cases_imported += 1
            logger.debug(f"保存案例: {current_case.name} (ID: {current_case_id})")

        # 更新理论统计
        self.db.update_theory_statistics()

        logger.info(f"导入完成: {cases_imported} 个案例, {theories_imported} 个新理论")

        return {
            'cases': cases_imported,
            'theories': theories_imported
        }

    def import_all_years(self, base_path: str = '.') -> Dict[str, Dict[str, int]]:
        """
        批量导入所有年份的数据

        Args:
            base_path: 案例库根目录

        Returns:
            每个年份的导入统计
        """
        base_path = Path(base_path)
        results = {}

        years = ['FDC-21', 'FDC-22', 'FDC-23', 'FDC-24', 'FDC-25']

        for year in years:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"处理 {year}")
            logger.info('=' * 60)

            # 查找Excel文件
            excel_patterns = [
                f'{year}/**/*案例统计.xlsx',
                f'{year}/*案例统计.xlsx'
            ]

            excel_file = None
            for pattern in excel_patterns:
                files = list(base_path.glob(pattern))
                if files:
                    excel_file = files[0]
                    break

            if excel_file and excel_file.exists():
                try:
                    stats = self.import_from_excel(str(excel_file), year)
                    results[year] = stats
                    logger.success(f"✓ {year}: 导入 {stats['cases']} 个案例, {stats['theories']} 个新理论")
                except Exception as e:
                    logger.error(f"✗ {year}: 导入失败 - {e}")
                    results[year] = {'cases': 0, 'theories': 0, 'error': str(e)}
            else:
                logger.warning(f"! {year}: 未找到Excel文件")
                results[year] = {'cases': 0, 'theories': 0, 'error': 'File not found'}

        # 总计
        logger.info(f"\n{'=' * 60}")
        logger.info("导入汇总")
        logger.info('=' * 60)

        total_cases = sum(r.get('cases', 0) for r in results.values())
        total_theories = sum(r.get('theories', 0) for r in results.values())

        logger.info(f"总案例数: {total_cases}")
        logger.info(f"总新理论数: {total_theories}")

        # 数据库统计
        db_stats = self.db.get_database_stats()
        logger.info(f"\n数据库统计:")
        logger.info(f"  案例总数: {db_stats['total_cases']}")
        logger.info(f"  理论总数: {db_stats['total_theories']}")
        logger.info(f"  关联总数: {db_stats['total_links']}")
        logger.info(f"  年份跨度: {db_stats['total_years']} 个年份")

        return results


def import_excel_data(base_path: str = '.', db_path: Optional[str] = None) -> Dict[str, Dict[str, int]]:
    """
    便捷函数: 导入所有Excel数据

    Args:
        base_path: 案例库根目录
        db_path: 数据库路径 (可选)

    Returns:
        导入统计
    """
    db = Database(db_path)
    importer = ExcelImporter(db)
    return importer.import_all_years(base_path)
