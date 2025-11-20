"""Markdown转PDF工具 - 使用ReportLab直接生成"""

import re
from pathlib import Path
from io import BytesIO
from loguru import logger
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class PDFConverter:
    """Markdown转PDF转换器 - 使用ReportLab"""

    _fonts_registered = False

    @staticmethod
    def _register_fonts():
        """注册中文字体"""
        if PDFConverter._fonts_registered:
            return

        try:
            # 获取项目根目录下的font文件夹
            project_root = Path(__file__).parent.parent.parent
            font_dir = project_root / "font"

            # 注册雅黑字体
            yahei_font = font_dir / "yahei.ttf"
            yahei_bold_font = font_dir / "yahei_bold.ttf"

            if yahei_font.exists():
                pdfmetrics.registerFont(TTFont('YaHei', str(yahei_font)))
                logger.info(f"已注册字体: YaHei from {yahei_font}")

                # 注册粗体
                if yahei_bold_font.exists():
                    pdfmetrics.registerFont(TTFont('YaHei-Bold', str(yahei_bold_font)))
                    logger.info(f"已注册粗体: YaHei-Bold from {yahei_bold_font}")

                PDFConverter._fonts_registered = True
            else:
                logger.warning(f"字体文件不存在: {yahei_font}")
        except Exception as e:
            logger.error(f"注册字体失败: {e}")

    @staticmethod
    def _create_styles():
        """创建PDF样式"""
        styles = getSampleStyleSheet()

        # 标题1样式
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontName='YaHei-Bold',
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=20,
            spaceBefore=0,
            alignment=TA_LEFT
        ))

        # 标题2样式
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontName='YaHei-Bold',
            fontSize=18,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=15,
            spaceBefore=30,
            alignment=TA_LEFT
        ))

        # 标题3样式
        styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=styles['Heading3'],
            fontName='YaHei-Bold',
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=20,
            alignment=TA_LEFT
        ))

        # 标题4样式
        styles.add(ParagraphStyle(
            name='CustomHeading4',
            parent=styles['Heading4'],
            fontName='YaHei-Bold',
            fontSize=12,
            textColor=colors.HexColor('#555555'),
            spaceAfter=8,
            spaceBefore=15,
            alignment=TA_LEFT
        ))

        # 正文样式
        styles.add(ParagraphStyle(
            name='CustomBody',
            parent=styles['Normal'],
            fontName='YaHei',
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10,
            alignment=TA_JUSTIFY,
            leading=16
        ))

        # 粗体样式
        styles.add(ParagraphStyle(
            name='CustomBold',
            parent=styles['Normal'],
            fontName='YaHei-Bold',
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_LEFT
        ))

        return styles

    @staticmethod
    def _markdown_to_story(markdown_text: str, styles):
        """将Markdown文本转换为ReportLab的Story元素列表"""
        story = []
        lines = markdown_text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # H1标题
            if line.startswith('# '):
                text = line[2:].strip()
                story.append(Paragraph(text, styles['CustomTitle']))
                story.append(Spacer(1, 0.5*cm))

            # H2标题
            elif line.startswith('## '):
                text = line[3:].strip()
                story.append(Paragraph(text, styles['CustomHeading2']))

            # H3标题
            elif line.startswith('### '):
                text = line[4:].strip()
                story.append(Paragraph(text, styles['CustomHeading3']))

            # H4标题
            elif line.startswith('#### '):
                text = line[5:].strip()
                story.append(Paragraph(text, styles['CustomHeading4']))

            # 分隔线
            elif line.startswith('---'):
                story.append(Spacer(1, 0.3*cm))

            # 表格开始
            elif '|' in line and i + 1 < len(lines) and '|' in lines[i+1]:
                table_data = []
                # 收集表格行
                while i < len(lines) and '|' in lines[i]:
                    row = [cell.strip() for cell in lines[i].split('|') if cell.strip()]
                    if row and not all(c in '-:' for c in ''.join(row)):  # 跳过分隔行
                        table_data.append(row)
                    i += 1

                if table_data:
                    # 将表格数据转换为Paragraph对象以支持自动换行
                    wrapped_table_data = []
                    for row_idx, row in enumerate(table_data):
                        wrapped_row = []
                        for cell in row:
                            # 对每个单元格使用Paragraph包装，支持自动换行
                            if row_idx == 0:
                                # 表头使用粗体样式
                                p = Paragraph(cell, styles['CustomBold'])
                            else:
                                # 数据行使用普通样式
                                p = Paragraph(cell, styles['CustomBody'])
                            wrapped_row.append(p)
                        wrapped_table_data.append(wrapped_row)

                    # 计算列宽：智能分配宽度
                    num_cols = len(table_data[0]) if table_data else 0
                    if num_cols > 0:
                        # A4纸宽度减去左右边距(2cm*2)，剩余可用宽度
                        available_width = A4[0] - 4*cm

                        # 智能分配列宽：案例名称列较宽，其他列相对较窄
                        if num_cols == 5:  # 案例详情表格（名称、编号、年份、学科、行业）
                            col_widths = [
                                available_width * 0.30,  # 案例名称 30%
                                available_width * 0.20,  # 案例编号 20%
                                available_width * 0.15,  # 年份 15%
                                available_width * 0.20,  # 学科 20%
                                available_width * 0.15   # 行业 15%
                            ]
                        elif num_cols == 6:  # 完整案例表格（含作者/关键词）
                            col_widths = [
                                available_width * 0.25,  # 案例名称 25%
                                available_width * 0.15,  # 案例编号 15%
                                available_width * 0.10,  # 年份 10%
                                available_width * 0.15,  # 学科 15%
                                available_width * 0.15,  # 行业 15%
                                available_width * 0.20   # 其他 20%
                            ]
                        else:
                            # 其他情况平均分配
                            col_widths = [available_width / num_cols] * num_cols
                    else:
                        col_widths = None

                    # 创建表格，指定列宽
                    table = Table(wrapped_table_data, colWidths=col_widths)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # 垂直对齐方式
                        ('FONTNAME', (0, 0), (-1, 0), 'YaHei-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),  # 表头字体增大到10
                        ('FONTNAME', (0, 1), (-1, -1), 'YaHei'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),  # 数据行字体保持9
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),  # 增加内边距
                        ('TOPPADDING', (0, 0), (-1, -1), 10),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
                        ('WORDWRAP', (0, 0), (-1, -1), True)  # 启用自动换行
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.3*cm))
                continue

            # 列表项
            elif line.startswith('- ') or line.startswith('* ') or re.match(r'^\d+\. ', line):
                text = re.sub(r'^[-*]\s+|\d+\.\s+', '', line)
                # 处理粗体
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                story.append(Paragraph(f'• {text}', styles['CustomBody']))

            # 引用块
            elif line.startswith('>'):
                text = line[1:].strip()
                # 处理粗体
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                story.append(Paragraph(f'<i>{text}</i>', styles['CustomBody']))

            # 普通段落
            else:
                text = line
                # 处理粗体
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                story.append(Paragraph(text, styles['CustomBody']))

            i += 1

        return story

    @staticmethod
    def markdown_to_pdf(markdown_text: str, output_path: str = None) -> bytes:
        """
        将Markdown文本转换为PDF

        Args:
            markdown_text: Markdown格式的文本
            output_path: 输出PDF文件路径(可选)

        Returns:
            PDF文件的字节内容
        """
        try:
            # 注册中文字体
            PDFConverter._register_fonts()

            # 创建PDF文档
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )

            # 创建样式
            styles = PDFConverter._create_styles()

            # 转换Markdown为Story
            story = PDFConverter._markdown_to_story(markdown_text, styles)

            # 生成PDF
            doc.build(story)

            # 获取PDF字节
            pdf_bytes = buffer.getvalue()
            buffer.close()

            # 如果指定了输出路径,保存文件
            if output_path:
                Path(output_path).write_bytes(pdf_bytes)
                logger.info(f"PDF已保存到: {output_path}")

            return pdf_bytes

        except Exception as e:
            logger.error(f"Markdown转PDF失败: {e}")
            raise
