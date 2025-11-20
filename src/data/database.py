"""数据库操作模块"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from ..config import settings
from .models import Case, Theory, CaseTheory


class Database:
    """数据库管理类"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        if db_path is None:
            db_path = str(settings.database_path_abs)

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接 (上下文管理器)"""
        conn = sqlite3.connect(self.db_path, timeout=60.0, isolation_level=None)  # 增加超时到60秒,自动提交
        conn.row_factory = sqlite3.Row  # 允许通过列名访问
        conn.execute("PRAGMA journal_mode=WAL")  # 使用WAL模式提高并发性能
        conn.execute("PRAGMA synchronous=NORMAL")  # 降低同步级别提高性能
        conn.execute("PRAGMA cache_size=10000")  # 增加缓存
        try:
            yield conn
            # isolation_level=None时不需要手动commit
        except Exception as e:
            # isolation_level=None时不需要rollback
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 案例表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT UNIQUE,
                    year TEXT,
                    author TEXT,
                    co_authors TEXT,
                    subject TEXT,
                    industry TEXT,
                    publish_date TEXT,
                    student_group TEXT,
                    keywords TEXT,
                    abstract TEXT,
                    course TEXT,
                    full_text TEXT,
                    pdf_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 理论表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS theories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    source TEXT,
                    author TEXT,
                    year INTEGER,
                    pdf_path TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 案例-理论关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS case_theories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL,
                    theory_id INTEGER NOT NULL,
                    question_number TEXT,
                    question_text TEXT,
                    question_type TEXT,
                    question_style TEXT,
                    context TEXT,
                    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                    FOREIGN KEY (theory_id) REFERENCES theories(id) ON DELETE CASCADE,
                    UNIQUE(case_id, theory_id, question_number)
                )
            """)

            # 理论使用统计表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS theory_statistics (
                    theory_id INTEGER PRIMARY KEY,
                    total_usage INTEGER DEFAULT 0,
                    last_used_year TEXT,
                    first_used_year TEXT,
                    FOREIGN KEY (theory_id) REFERENCES theories(id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_year ON cases(year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_subject ON cases(subject)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_code ON cases(code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_theory_name ON theories(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_theories_case ON case_theories(case_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_theories_theory ON case_theories(theory_id)")

    # ==================== 案例操作 ====================

    def save_case(self, case: Case) -> int:
        """
        保存案例

        Args:
            case: 案例对象

        Returns:
            案例ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO cases (
                    name, code, year, author, co_authors, subject, industry,
                    publish_date, student_group, keywords, abstract, course,
                    full_text, pdf_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case.name, case.code, case.year, case.author, case.co_authors,
                case.subject, case.industry, case.publish_date, case.student_group,
                case.keywords, case.abstract, case.course, case.full_text, case.pdf_path
            ))

            case_id = cursor.lastrowid

            # 保存理论关联
            for theory_name in case.theories:
                theory = self.get_theory_by_name(theory_name)
                if theory:
                    self.link_case_theory(case_id, theory.id)

            return case_id

    def get_case(self, case_id: int) -> Optional[Case]:
        """根据ID获取案例"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
            row = cursor.fetchone()

            if row:
                case_dict = dict(row)
                # 获取关联的理论
                theories = self.get_case_theories(case_id)
                case_dict['theories'] = [t.name for t in theories]
                return Case(**case_dict)

            return None

    def get_case_by_code(self, code: str) -> Optional[Case]:
        """根据编号获取案例"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cases WHERE code = ?", (code,))
            row = cursor.fetchone()

            if row:
                case_dict = dict(row)
                case_id = case_dict['id']
                theories = self.get_case_theories(case_id)
                case_dict['theories'] = [t.name for t in theories]
                return Case(**case_dict)

            return None

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        根据案例ID获取案例 (返回字典格式,用于API)

        Args:
            case_id: 案例ID

        Returns:
            案例字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
            row = cursor.fetchone()

            if row:
                case_dict = dict(row)
                # 获取关联的理论
                theories = self.get_case_theories(int(case_id))
                case_dict['theories'] = [t.name for t in theories]
                return case_dict

            return None

    def get_all_cases(self, year: Optional[str] = None) -> List[Case]:
        """
        获取所有案例

        Args:
            year: 可选的年份过滤

        Returns:
            案例列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if year:
                cursor.execute("SELECT * FROM cases WHERE year = ? ORDER BY id", (year,))
            else:
                cursor.execute("SELECT * FROM cases ORDER BY id")

            rows = cursor.fetchall()

            cases = []
            for row in rows:
                case_dict = dict(row)
                case_id = case_dict['id']
                theories = self.get_case_theories(case_id)
                case_dict['theories'] = [t.name for t in theories]
                cases.append(Case(**case_dict))

            return cases

    # ==================== 理论操作 ====================

    def save_theory(self, theory: Theory) -> int:
        """保存理论"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO theories (name, source, author, year, pdf_path, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                theory.name, theory.source, theory.author, theory.year,
                theory.pdf_path, theory.description
            ))

            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                # 如果已存在，返回现有ID
                cursor.execute("SELECT id FROM theories WHERE name = ?", (theory.name,))
                row = cursor.fetchone()
                return row['id'] if row else 0

    def get_theory(self, theory_id: int) -> Optional[Theory]:
        """根据ID获取理论"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM theories WHERE id = ?", (theory_id,))
            row = cursor.fetchone()

            if row:
                return Theory(**dict(row))

            return None

    def get_theory_by_name(self, name: str) -> Optional[Theory]:
        """根据名称获取理论"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM theories WHERE name = ?", (name,))
            row = cursor.fetchone()

            if row:
                return Theory(**dict(row))

            return None

    def get_all_theories(self) -> List[Theory]:
        """获取所有理论"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM theories ORDER BY name")
            rows = cursor.fetchall()

            return [Theory(**dict(row)) for row in rows]

    def get_all_theory_names(self) -> List[str]:
        """获取所有理论名称列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM theories ORDER BY name")
            rows = cursor.fetchall()

            return [row['name'] for row in rows]

    # ==================== 关联操作 ====================

    def link_case_theory(self, case_id: int, theory_id: int,
                        question_number: Optional[str] = None,
                        question_text: Optional[str] = None,
                        question_type: Optional[str] = None,
                        question_style: Optional[str] = None) -> int:
        """关联案例和理论"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO case_theories (
                    case_id, theory_id, question_number, question_text,
                    question_type, question_style
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (case_id, theory_id, question_number, question_text,
                  question_type, question_style))

            return cursor.lastrowid

    def get_case_theories(self, case_id: int) -> List[Theory]:
        """获取案例使用的所有理论"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM theories t
                JOIN case_theories ct ON t.id = ct.theory_id
                WHERE ct.case_id = ?
            """, (case_id,))

            rows = cursor.fetchall()
            return [Theory(**dict(row)) for row in rows]

    def get_cases_by_theory(self, theory_name: str) -> List[Dict[str, Any]]:
        """获取使用特定理论的所有案例"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.name, c.code, c.year, c.subject, c.industry
                FROM cases c
                JOIN case_theories ct ON c.id = ct.case_id
                JOIN theories t ON ct.theory_id = t.id
                WHERE t.name = ?
                ORDER BY c.year DESC, c.id
            """, (theory_name,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # ==================== 统计操作 ====================

    def update_theory_statistics(self):
        """更新理论使用统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO theory_statistics (theory_id, total_usage, last_used_year, first_used_year)
                SELECT
                    t.id,
                    COUNT(DISTINCT ct.case_id) as total_usage,
                    MAX(c.year) as last_used_year,
                    MIN(c.year) as first_used_year
                FROM theories t
                LEFT JOIN case_theories ct ON t.id = ct.theory_id
                LEFT JOIN cases c ON ct.case_id = c.id
                GROUP BY t.id
            """)

    def get_theory_usage_count(self, theory_name: str) -> int:
        """获取理论使用次数"""
        cases = self.get_cases_by_theory(theory_name)
        return len(cases)

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) as count FROM cases")
            stats['total_cases'] = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM theories")
            stats['total_theories'] = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM case_theories")
            stats['total_case_theory_relations'] = cursor.fetchone()['count']

            cursor.execute("SELECT DISTINCT year FROM cases WHERE year IS NOT NULL ORDER BY year")
            years = cursor.fetchall()
            stats['years_covered'] = [row['year'] for row in years]

            return stats

    def search_cases(self,
                    keyword: Optional[str] = None,
                    subject: Optional[str] = None,
                    industry: Optional[str] = None,
                    year: Optional[str] = None,
                    limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索案例

        Args:
            keyword: 关键词 (搜索name, keywords, abstract)
            subject: 学科领域
            industry: 行业
            year: 年份
            limit: 返回数量限制

        Returns:
            案例列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 构建SQL查询
            query = "SELECT * FROM cases WHERE 1=1"
            params = []

            if keyword:
                query += " AND (name LIKE ? OR keywords LIKE ? OR abstract LIKE ?)"
                keyword_pattern = f"%{keyword}%"
                params.extend([keyword_pattern, keyword_pattern, keyword_pattern])

            if subject:
                query += " AND subject = ?"
                params.append(subject)

            if industry:
                query += " AND industry = ?"
                params.append(industry)

            if year:
                query += " AND year = ?"
                params.append(year)

            query += " ORDER BY year DESC, id LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            cases = []
            for row in rows:
                case_dict = dict(row)
                case_id = case_dict['id']
                theories = self.get_case_theories(case_id)
                case_dict['theories'] = [t.name for t in theories]
                cases.append(case_dict)

            return cases
