"""分析报告生成器（Markdown）"""

from typing import Dict, List
from datetime import datetime
from loguru import logger


class ReportGenerator:
    """生成Markdown格式的分析报告"""

    @staticmethod
    def generate_report(new_case: Dict,
                        exact_matches: Dict,
                        comprehensive_scores: List[Dict],
                        innovation_score: Dict) -> str:
        logger.info("生成分析报告...")

        report: List[str] = []
        report.append("# 案例知识点匹配分析报告\n")
        report.append(f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("---\n")

        # 一、案例基本信息
        report.append("## 一、案例基本信息\n")
        report.append(f"- **案例名称**: {new_case.get('name', 'N/A')}")
        if new_case.get('code'):
            report.append(f"- **案例编号**: {new_case.get('code')}")
        if new_case.get('author'):
            report.append(f"- **作者**: {new_case.get('author')}")
        if new_case.get('subject'):
            report.append(f"- **学科领域**: {new_case.get('subject')}")
        if new_case.get('industry'):
            report.append(f"- **行业**: {new_case.get('industry')}")
        if new_case.get('keywords'):
            report.append(f"- **关键词**: {new_case.get('keywords')}")
        report.append("")

        # 二、识别的理论知识点
        theories = new_case.get('theories', [])
        primary_theories = new_case.get('primary_theories', []) or []
        report.append("## 二、识别的理论知识点\n")
        report.append(f"共识别出 **{len(theories)}** 个理论知识点:\n")

        if theories:
            # 如果有主要理论，分两部分显示
            if primary_theories:
                # 主要理论部分
                primary_exact = [t for t in theories if t in primary_theories and t in exact_matches]
                if primary_exact:
                    report.append(f"\n### 2.1 主要理论查重（{len(primary_exact)}项）\n")
                    for i, theory in enumerate(primary_exact, 1):
                        match_info = exact_matches.get(theory, {})
                        count = match_info.get('match_count', 0)
                        freq = match_info.get('frequency_rank', '未知')
                        report.append(f"{i}. **⭐ {theory}** - {freq} (数据库中使用{count}次)")

                # 其他理论部分
                other_exact = [t for t in theories if t not in primary_theories and t in exact_matches]
                if other_exact:
                    report.append(f"\n### 2.2 其他理论查重（{len(other_exact)}项）\n")
                    for i, theory in enumerate(other_exact, 1):
                        match_info = exact_matches.get(theory, {})
                        count = match_info.get('match_count', 0)
                        freq = match_info.get('frequency_rank', '未知')
                        report.append(f"{i}. **{theory}** - {freq} (数据库中使用{count}次)")
            else:
                # 没有主要理论时，按原样显示
                exact_count = len(exact_matches)
                if exact_count > 0:
                    report.append(f"\n### 2.1 数据库精确匹配（{exact_count}项）\n")
                    for i, theory in enumerate([t for t in theories if t in exact_matches], 1):
                        match_info = exact_matches.get(theory, {})
                        count = match_info.get('match_count', 0)
                        freq = match_info.get('frequency_rank', '未知')
                        report.append(f"{i}. **{theory}** - {freq} (数据库中使用{count}次)")
        else:
            report.append("未识别到理论知识点")

        report.append("")

        # 三、知识点重复度分析
        report.append("## 三、知识点重复度分析\n")
        report.append("### 3.1 整体创新度评分\n")
        innov = innovation_score
        report.append(f"**创新度总分**: {innov['innovation_score']}/100\n")

        report.append("**理论构成分析**:")
        report.append(f"- 新颖理论(≤2): {len(innov['novel_theories'])}项 ({innov['novel_ratio']*100:.0f}%)")
        report.append(f"- 常见理论(3-4): {len(innov['common_theories'])}项 ({innov['common_ratio']*100:.0f}%)")
        report.append(f"- 经典理论(≥5): {len(innov['high_frequency_theories'])}项 ({innov['high_freq_ratio']*100:.0f}%)\n")

        if theories and exact_matches:
            report.append("### 3.2 各理论使用详情\n")
            for theory in theories:
                match_data = exact_matches.get(theory, {})
                cases = match_data.get('cases', [])
                count = match_data.get('match_count', 0)
                freq = match_data.get('frequency_rank', '')

                report.append(f"#### {theory}\n")
                report.append(f"- **历史使用频次**: {count}次")
                report.append(f"- **频次等级**: {freq}")
                if cases:
                    report.append(f"- **使用案例** (最多列出5条):")
                    for i, case in enumerate(cases[:5], 1):
                        report.append(f"  {i}. {case.get('name', 'N/A')} ({case.get('year', 'N/A')})")
                report.append(f"- **建议**: {ReportGenerator._get_theory_recommendation(freq, count)}\n")

        # 四、相似案例排名
        report.append("## 四、相似案例排名\n")
        if comprehensive_scores:
            report.append("根据综合相似度排名 (Top 10):\n")
            report.append("| 排名 | 案例名称 | 年份 | 综合相似度 | 语义相似度 | 学科 |")
            report.append("|------|---------|------|-----------|----------|------|")
            for i, score_data in enumerate(comprehensive_scores[:10], 1):
                metadata = score_data['metadata']
                scores = score_data['scores']
                report.append(
                    f"| {i} | {metadata.get('name', 'N/A')} | "
                    f"{metadata.get('year', 'N/A')} | "
                    f"{scores['final_score']:.2f} | "
                    f"{scores['semantic_similarity']:.2f} | "
                    f"{metadata.get('subject', 'N/A')} |"
                )
        else:
            report.append("未找到相似案例")

        report.append("")

        # 五、优化建议
        report.append("## 五、优化建议\n")
        if innov['high_frequency_theories']:
            report.append("### 1. 经典理论优化建议\n")
            for theory in innov['high_frequency_theories']:
                report.append(f"- **{theory}**: 使用广泛，建议引入新理论或创新组合以提升新意")
            report.append("")

        if innov['novel_theories']:
            report.append("### 2. 新颖理论亮点\n")
            for theory in innov['novel_theories']:
                report.append(f"- **{theory}**: 新颖选择，体现课题的新意与探索性")
            report.append("")

        report.append("### 3. 理论组合建议\n")
        report.append(ReportGenerator._generate_combination_advice(theories))
        report.append("")

        logger.success("报告生成完成")
        return "\n".join(report)

    @staticmethod
    def _get_theory_recommendation(frequency_rank: str, count: int) -> str:
        if frequency_rank == '经典理论':
            return '理论使用广泛，建议引入新理论或创新组合以提升新意'
        elif frequency_rank == '常见理论':
            return '选择合理，可与新颖理论搭配以增强差异化'
        else:
            return '较新颖，注意论证充分并与经典理论形成呼应'

    @staticmethod
    def _generate_combination_advice(theories: List[str]) -> str:
        if not theories:
            return "- 建议增加理论分析以增强案例深度"
        elif len(theories) < 3:
            return "- 建议增加1-2个理论以增强分析深度和多维度视角"
        elif len(theories) > 8:
            return "- 理论数量较多，建议聚焦核心理论，避免分散"
        else:
            return "- 理论数量适中，组合较为合理"

