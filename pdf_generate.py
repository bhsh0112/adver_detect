import os
import re
import subprocess
from datetime import datetime

try:
    # 延迟导入，环境可能未安装
    import docx
    from docx import Document
except Exception:
    Document = None

# 字体注册放在使用 reportlab 的函数内部进行，避免未安装时在导入阶段报错

def load_data_from_folder(input_folder):
    """\
    @description 从由 `cut.py` 产出的目录中加载数据。
    @param {str} input_folder - `cut.py` 输出的目录路径。
    @returns {(list, str, str)} video_segments, summary_text, boxed_video_path
    @example
    - 包含裁剪的广告片段的文件夹
    - 包含摘要统计的 txt 文档
    - 叠加检测框的视频 mp4
    """
    video_segments = []
    summary_text = ""
    boxed_video_path = ""
    
    # Get base folder name without path
    folder_name = os.path.basename(input_folder.rstrip('/'))

    # Scan the folder for files (放宽命名约束，适配 cut.py 实际产物)
    if not os.path.exists(input_folder):
        print(f"Error: Input folder {input_folder} does not exist")
        return [], "", ""
    
    # Look for summary file: *_summary.txt（取最新修改时间的一份）
    try:
        txt_candidates = [
            f for f in os.listdir(input_folder)
            if f.endswith('_summary.txt') and os.path.isfile(os.path.join(input_folder, f))
        ]
        if txt_candidates:
            txt_candidates.sort(key=lambda n: os.path.getmtime(os.path.join(input_folder, n)), reverse=True)
            summary_path = os.path.join(input_folder, txt_candidates[0])
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_text = f.read()
    except Exception as e:
        print(f"Error reading summary file: {e}")

    # Look for segments folder: *_segments
    segments_path = None
    try:
        for f in os.listdir(input_folder):
            full = os.path.join(input_folder, f)
            if os.path.isdir(full) and f.endswith('_segments'):
                segments_path = full
                break
    except Exception:
        segments_path = None

    if segments_path and os.path.exists(segments_path):
        for video_file in os.listdir(segments_path):
            if video_file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                video_segments.append({
                    'filename': video_file,
                    'path': os.path.join(segments_path, video_file),
                    'size': os.path.getsize(os.path.join(segments_path, video_file))
                })
    
    # Look for boxed video file: *_visulize_*.mp4（取最新一份）
    try:
        vis_candidates = [
            f for f in os.listdir(input_folder)
            if f.endswith('.mp4') and '_visulize_' in f
        ]
        if vis_candidates:
            vis_candidates.sort(key=lambda n: os.path.getmtime(os.path.join(input_folder, n)), reverse=True)
            boxed_video_path = os.path.join(input_folder, vis_candidates[0])
    except Exception:
        boxed_video_path = ""
    
    # Sort video segments by filename for consistent ordering
    video_segments.sort(key=lambda x: x['filename'])
    
    return video_segments, summary_text, boxed_video_path


def parse_summary_stats(summary_text):
    """\
    @description 解析 `cut.py` 生成的摘要文本，提取统计信息与片段原始时间。
    @param {str} summary_text - 摘要文本内容。
    @returns {dict} 统计信息字典：
    {
      'total_duration_sec': float,
      'num_segments': int,
      'avg_each_duration_sec': float,
      'first_appeared_sec': float | None,
      'last_disappeared_sec': float | None,
      'time_ratio_percent': float | None
    }
    """
    if not summary_text:
        return {
            'total_duration_sec': 0.0,
            'num_segments': 0,
            'avg_each_duration_sec': 0.0,
            'first_appeared_sec': None,
            'last_disappeared_sec': None,
            'time_ratio_percent': None,
        }

    total_duration_sec = 0.0
    num_segments = 0
    first_appeared_sec = None
    last_disappeared_sec = None
    time_ratio_percent = None

    # 总出现时长
    m_total = re.search(r"^总出现时长:\s*([0-9.]+)秒", summary_text, re.M)
    if m_total:
        try:
            total_duration_sec = float(m_total.group(1))
        except Exception:
            total_duration_sec = 0.0

    # 片段数
    m_count = re.search(r"^检测到的片段数:\s*(\d+)", summary_text, re.M)
    if m_count:
        try:
            num_segments = int(m_count.group(1))
        except Exception:
            num_segments = 0

    # 原始起止时间（用于首次/末次时间点）
    original_times = []
    for match in re.finditer(r"原始时间:\s*([0-9.]+)s\s*-\s*([0-9.]+)s", summary_text):
        try:
            start_v = float(match.group(1))
            end_v = float(match.group(2))
            original_times.append((start_v, end_v))
        except Exception:
            continue
    if original_times:
        first_appeared_sec = min(s for s, _ in original_times)
        last_disappeared_sec = max(e for _, e in original_times)

    # 占比
    m_ratio = re.search(r"^目标出现时长占比:\s*([0-9.]+)%", summary_text, re.M)
    if m_ratio:
        try:
            time_ratio_percent = float(m_ratio.group(1))
        except Exception:
            time_ratio_percent = None

    avg_each_duration_sec = (total_duration_sec / num_segments) if num_segments > 0 else 0.0

    return {
        'total_duration_sec': total_duration_sec,
        'num_segments': num_segments,
        'avg_each_duration_sec': avg_each_duration_sec,
        'first_appeared_sec': first_appeared_sec,
        'last_disappeared_sec': last_disappeared_sec,
        'time_ratio_percent': time_ratio_percent,
    }


def _format_mm_ss(seconds_value):
    """\
    @description 将秒数格式化为 mm:ss 或 ss.s 格式，便于在模板中展示。
    @param {float|None} seconds_value
    @returns {str}
    """
    if seconds_value is None:
        return ""
    try:
        seconds_value = float(seconds_value)
    except Exception:
        return ""
    if seconds_value < 3600:
        minutes = int(seconds_value // 60)
        seconds = seconds_value - minutes * 60
        return f"{minutes:02d}:{seconds:04.1f}"
    else:
        hours = int(seconds_value // 3600)
        remainder = seconds_value - hours * 3600
        minutes = int(remainder // 60)
        seconds = remainder - minutes * 60
        return f"{hours:02d}:{minutes:02d}:{seconds:04.1f}"


def fill_docx_template(template_path, output_docx_path, stats):
    """\
    @description 使用统计数据填充 DOCX 模板中的表格。
    @param {str} template_path - 模板路径。
    @param {str} output_docx_path - 输出 DOCX 路径。
    @param {dict} stats - parse_summary_stats 的返回值。
    @returns {None}
    """
    if Document is None:
        raise RuntimeError("未安装 python-docx，请先安装：pip install python-docx")

    doc = Document(template_path)

    # 规范化工具
    def norm(text):
        return (text or "").replace("\u00A0", " ").replace("\xa0", " ").strip()

    # 将要填充的值（只填第一条数据行，模板中一般为“广告牌”那一行）
    total_duration = stats.get('total_duration_sec') or 0.0
    num_segments = stats.get('num_segments') or 0
    avg_each = stats.get('avg_each_duration_sec') or 0.0
    first_time = stats.get('first_appeared_sec')
    last_time = stats.get('last_disappeared_sec')
    time_ratio = stats.get('time_ratio_percent')

    # 遍历表格，依据表头识别需要填充的表
    for table in doc.tables:
        if not table.rows or not table.columns:
            continue
        try:
            header_cells = [norm(c.text) for c in table.rows[0].cells]
        except Exception:
            continue

        # 1.1 总露出时长
        if len(header_cells) >= 5 and header_cells[0] == '权益' and '总露出时长' in header_cells[1]:
            # 查找第一条数据行（通常左侧为“广告牌”）
            for r in range(1, len(table.rows)):
                first_col_text = norm(table.cell(r, 0).text)
                if first_col_text in ('广告牌', '产品', ''):
                    table.cell(r, 1).text = f"{total_duration:.1f}"
                    # 周期平均/差值暂缺
                    # table.cell(r, 2).text = ""
                    # table.cell(r, 3).text = ""
                    # 图例留空
                    # table.cell(r, 4).text = ""
                    break

        # 1.2 平均每次露出时长
        elif len(header_cells) >= 5 and header_cells[0] == '权益' and '平均每次时长' in header_cells[1]:
            for r in range(1, len(table.rows)):
                first_col_text = norm(table.cell(r, 0).text)
                if first_col_text in ('广告牌', '产品', ''):
                    table.cell(r, 1).text = f"{avg_each:.1f}"
                    break

        # 1.3 露出频次
        elif len(header_cells) >= 5 and header_cells[0] == '权益' and '露出频次' in header_cells[1]:
            for r in range(1, len(table.rows)):
                first_col_text = norm(table.cell(r, 0).text)
                if first_col_text in ('广告牌', '产品', ''):
                    table.cell(r, 1).text = str(num_segments)
                    break

        # 1.4 首末露出时间点（标题可能有意外空格，如“首次露出时 间点”）
        elif len(header_cells) >= 6 and header_cells[0] == '权益' and ('首次露出' in header_cells[1] or '首次露出时间点' in header_cells[1]):
            for r in range(1, len(table.rows)):
                first_col_text = norm(table.cell(r, 0).text)
                if first_col_text in ('广告牌', '产品', ''):
                    table.cell(r, 1).text = _format_mm_ss(first_time)
                    table.cell(r, 2).text = _format_mm_ss(last_time)
                    break

        # 1.5 露出类型分布
        elif len(header_cells) >= 6 and header_cells[0] == '权益' and '露出总时长' in header_cells[1]:
            for r in range(1, len(table.rows)):
                first_col_text = norm(table.cell(r, 0).text)
                if first_col_text in ('广告牌', '产品', ''):
                    table.cell(r, 1).text = f"{total_duration:.1f}"
                    if time_ratio is not None:
                        table.cell(r, 2).text = f"{time_ratio:.2f}%"
                    # 露出总次数
                    table.cell(r, 3).text = str(num_segments)
                    # 露出次数占比：该形式次数 / 总次数。
                    # 当前仅填本行（单一形式）时，按 100% 处理（有全局总数时可在 stats 中带入覆盖）。
                    count_ratio = None
                    if isinstance(stats, dict):
                        count_ratio = stats.get('count_ratio_percent')
                        if count_ratio is None and stats.get('total_counts_all_forms'):
                            try:
                                total_counts = float(stats.get('total_counts_all_forms'))
                                count_ratio = (num_segments / total_counts * 100.0) if total_counts > 0 else 0.0
                            except Exception:
                                count_ratio = None
                    if count_ratio is None:
                        count_ratio = 100.0 if num_segments > 0 else 0.0
                    table.cell(r, 4).text = f"{count_ratio:.2f}%"
                    break

    doc.save(output_docx_path)


def convert_docx_to_pdf(input_docx_path, output_pdf_path):
    """\
    @description 调用本地 LibreOffice 将 DOCX 转换为 PDF。
    @param {str} input_docx_path
    @param {str} output_pdf_path
    @returns {bool} 成功与否
    """
    # 优先尝试 soffice
    soffice_cmds = [
        ['soffice', '--headless', '--convert-to', 'pdf', '--outdir', os.path.dirname(output_pdf_path), input_docx_path],
        ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', os.path.dirname(output_pdf_path), input_docx_path],
    ]
    for cmd in soffice_cmds:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # 转换后文件名称通常以 .pdf 存放于 outdir，名称与 docx 同名
            generated_pdf = os.path.join(os.path.dirname(output_pdf_path), os.path.splitext(os.path.basename(input_docx_path))[0] + '.pdf')
            if os.path.exists(generated_pdf):
                # 重命名/移动到目标路径
                if os.path.abspath(generated_pdf) != os.path.abspath(output_pdf_path):
                    os.replace(generated_pdf, output_pdf_path)
                return True
        except Exception:
            continue
    return False

def generate_pdf_report(video_segments, summary_text, boxed_video_path, output_pdf_path, input_folder):
    """\
    @description 使用 ReportLab 生成 PDF 报告（旧版方案，保留以便回退）。
    @param {list} video_segments
    @param {str} summary_text
    @param {str} boxed_video_path
    @param {str} output_pdf_path
    @param {str} input_folder
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception as e:
        raise RuntimeError(
            "未安装 reportlab，请先安装：pip install reportlab"
        ) from e
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=36
    )
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles with Chinese font support
    try:
        pdfmetrics.registerFont(TTFont('黑体', 'STHeiti\ Medium.ttc'))
    except Exception:
        # 字体缺失时仍可继续
        pass
    # Theme colors
    primary_color = colors.HexColor('#1F4E79')
    secondary_color = colors.HexColor('#2E75B6')
    accent_color = colors.HexColor('#DDEBF7')

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName='微软雅黑',
        fontSize=24,
        textColor=primary_color,
        spaceAfter=14,
        leading=28,
        alignment=1  # Center
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontName='微软雅黑',
        fontSize=14,
        textColor=secondary_color,
        spaceAfter=10
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName='微软雅黑',
        fontSize=10,
        leading=16
    )
    
    # Create a style for table cells with word wrap
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='微软雅黑',
        fontSize=10,
        leading=14,
        wordWrap='CJK'  # Enable word wrap for CJK characters
    )
    
    # Title
    elements.append(Paragraph("视频广告分析报告", title_style))
    elements.append(HRFlowable(width='100%', thickness=1, color=primary_color))
    elements.append(Spacer(1, 0.25 * inch))
    
    # Date
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"生成时间: {current_date}", normal_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Source Information Section
    elements.append(Paragraph("源文件信息", subtitle_style))
    source_data = [
        ["输入文件夹", Paragraph(os.path.basename(input_folder), table_text_style)],
        ["完整路径", Paragraph(input_folder, table_text_style)],
        ["标记视频", Paragraph(os.path.basename(boxed_video_path) if boxed_video_path else "未找到", table_text_style)],
        ["广告片段总数", Paragraph(str(len(video_segments)), table_text_style)]
    ]
    source_table = Table(source_data, colWidths=[1.5 * inch, 4 * inch])
    source_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), '微软雅黑'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [accent_color, colors.white]),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    elements.append(source_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Advertisement Segments Section
    elements.append(Paragraph("广告片段列表", subtitle_style))
    if video_segments:
        ad_data = [["序号", "文件名", "文件大小(KB)", "相对路径"]]
        for i, segment in enumerate(video_segments, 1):
            file_size_kb = round(segment['size'] / 1024, 2)
            ad_data.append([
                Paragraph(str(i), table_text_style),
                Paragraph(segment['filename'], table_text_style),
                Paragraph(str(file_size_kb), table_text_style),
                Paragraph(os.path.relpath(segment['path'], input_folder), table_text_style)
            ])
        
        ad_table = Table(ad_data, colWidths=[0.8 * inch, 2.2 * inch, 1.2 * inch, 2.0 * inch])
        ad_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), '微软雅黑'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, accent_color]),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
        ]))
        elements.append(ad_table)
    else:
        elements.append(Paragraph("未找到广告片段", normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Summary Section
    elements.append(Paragraph("分析摘要", subtitle_style))
    if summary_text:
        # Split long summary text into paragraphs for better formatting
        summary_paragraphs = summary_text.split('\n\n')
        for para in summary_paragraphs:
            if para.strip():
                elements.append(Paragraph(para.strip(), normal_style))
                elements.append(Spacer(1, 0.1 * inch))
    else:
        elements.append(Paragraph("无摘要内容", normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Statistics Section
    elements.append(Paragraph("处理统计", subtitle_style))
    total_segments = len(video_segments)
    total_size_mb = sum(segment['size'] for segment in video_segments) / (1024 * 1024)
    avg_size_kb = (total_size_mb * 1024 / total_segments) if total_segments > 0 else 0
    
    stats_data = [
        ["广告片段总数", str(total_segments)],
        ["片段总大小", f"{total_size_mb:.2f} MB"],
        ["平均片段大小", f"{avg_size_kb:.2f} KB"],
        ["是否包含标记视频", "是" if boxed_video_path else "否"]
    ]
    stats_table = Table(stats_data, colWidths=[2.5 * inch, 2.5 * inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), '微软雅黑'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, accent_color]),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
    ]))
    elements.append(stats_table)
    
    # File Details Section (if there are many segments, show first 10)
    if total_segments > 10:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("File Details (First 10 segments)", subtitle_style))
        elements.append(Paragraph(f"Note: Showing first 10 of {total_segments} total segments", normal_style))
        
        detail_data = [["Filename", "Full Path"]]
        for segment in video_segments[:10]:
            detail_data.append([
                segment['filename'],
                segment['path']
            ])
        
        detail_table = Table(detail_data, colWidths=[2 * inch, 4 * inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(detail_table)
    
    # Page decorations: header banner and footer page number
    folder_name_for_header = os.path.basename(input_folder.rstrip('/'))

    def _draw_footer(canv, doc_obj):
        canv.saveState()
        canv.setFont('微软雅黑', 9)
        canv.setFillColor(colors.grey)
        page_num_text = f"第 {canv.getPageNumber()} 页"
        canv.drawRightString(doc_obj.pagesize[0] - doc_obj.rightMargin, 0.5 * inch, page_num_text)
        canv.restoreState()

    def _draw_first_page(canv, doc_obj):
        canv.saveState()
        # Header banner
        banner_height = 0.6 * inch
        banner_y = doc_obj.pagesize[1] - banner_height
        canv.setFillColor(primary_color)
        canv.rect(0, banner_y, doc_obj.pagesize[0], banner_height, stroke=0, fill=1)
        canv.setFillColor(colors.whitesmoke)
        canv.setFont('微软雅黑', 12)
        canv.drawString(doc_obj.leftMargin, banner_y + banner_height/2 - 4, f"分析项目：{folder_name_for_header}")
        # Footer
        _draw_footer(canv, doc_obj)
        canv.restoreState()

    def _draw_later_pages(canv, doc_obj):
        canv.saveState()
        # Thin header line
        line_y = doc_obj.pagesize[1] - doc_obj.topMargin + 6
        canv.setStrokeColor(accent_color)
        canv.setLineWidth(1)
        canv.line(doc_obj.leftMargin, line_y, doc_obj.pagesize[0] - doc_obj.rightMargin, line_y)
        # Footer
        _draw_footer(canv, doc_obj)
        canv.restoreState()

    # Build the PDF
    doc.build(elements, onFirstPage=_draw_first_page, onLaterPages=_draw_later_pages)
    print(f"PDF report generated successfully at {output_pdf_path}")


def generate_from_template(input_folder, output_directory=None, template_path=None):
    """\
    @description 基于模板填充并输出 PDF（优先方案）。
    @param {str} input_folder - `cut.py` 输出目录。
    @param {str|None} output_directory - 输出目录，可为空。
    @param {str|None} template_path - DOCX 模板路径，默认 `test/template.docx`。
    @returns {str} 输出的 PDF 路径
    """
    folder_name = os.path.basename(input_folder.rstrip('/'))
    base_output_dir = os.path.dirname(input_folder) if output_directory is None else output_directory
    os.makedirs(base_output_dir, exist_ok=True)

    template_path = template_path or os.path.join(os.path.dirname(__file__), 'test', 'template.docx')
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"未找到模板: {template_path}")

    video_segments, summary_text, _ = load_data_from_folder(input_folder)
    stats = parse_summary_stats(summary_text)

    # 生成 DOCX 并转换为 PDF
    output_docx = os.path.join(base_output_dir, f"{folder_name}_filled.docx")
    output_pdf = os.path.join(base_output_dir, f"{folder_name}_analysis_report.pdf")

    fill_docx_template(template_path, output_docx, stats)

    ok = convert_docx_to_pdf(output_docx, output_pdf)
    if not ok:
        print("警告: 未检测到 LibreOffice/soffice，将保留 DOCX 并回退到 ReportLab PDF 方案。")
        # 回退旧方案
        _, summary_text_fallback, boxed_video = load_data_from_folder(input_folder)
        generate_pdf_report(video_segments, summary_text_fallback, boxed_video, output_pdf, input_folder)

    return output_pdf

def main(input_folder, output_directory=None, prefer_template=True, template_path=None):
    """\
    @description 入口函数：优先用模板填充导出 PDF，若失败则回退 ReportLab。
    @param {str} input_folder
    @param {str|None} output_directory
    @param {bool} prefer_template - 是否优先使用 DOCX 模板。
    @param {str|None} template_path - 自定义模板路径。
    @returns {str} 生成的 PDF 路径
    """
    try:
        if prefer_template:
            if template_path is None:
                template_path = os.path.join(os.path.dirname(__file__), 'test', 'template.docx')
            if os.path.exists(template_path):
                return generate_from_template(input_folder, output_directory, template_path)
            else:
                print(f"未找到模板 {template_path}，将回退到 ReportLab PDF 方案。")
    except Exception as e:
        print(f"模板填充失败，回退 ReportLab 方案。原因: {e}")

    # 回退旧方案
    folder_name = os.path.basename(input_folder.rstrip('/'))
    pdf_filename = f"{folder_name}_analysis_report.pdf"
    if output_directory is None:
        output_pdf_path = os.path.join(os.path.dirname(input_folder), pdf_filename)
    else:
        os.makedirs(output_directory, exist_ok=True)
        output_pdf_path = os.path.join(output_directory, pdf_filename)

    video_segments, summary_text, boxed_video_path = load_data_from_folder(input_folder)
    generate_pdf_report(video_segments, summary_text, boxed_video_path, output_pdf_path, input_folder)
    return output_pdf_path

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_generate.py <input_folder> [output_directory] [--no-template] [--template /abs/path/to/template.docx]")
        print("Example: python pdf_generate.py ./yolo广告检测demo-产品文件夹")
        print("Example: python pdf_generate.py ./yolo广告检测demo-产品文件夹 ./reports")
        sys.exit(1)

    input_folder = sys.argv[1]
    output_directory = None
    prefer_template = True
    template_path = None

    # 简单解析可选参数
    if len(sys.argv) >= 3 and not sys.argv[2].startswith('--'):
        output_directory = sys.argv[2]
    # 其他 flags
    for i in range(2, len(sys.argv)):
        arg = sys.argv[i]
        if arg == '--no-template':
            prefer_template = False
        if arg == '--template' and i + 1 < len(sys.argv):
            template_path = sys.argv[i + 1]

    main(input_folder, output_directory, prefer_template=prefer_template, template_path=template_path)