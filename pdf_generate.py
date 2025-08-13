import os
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Chinese font
# pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttf'))
pdfmetrics.registerFont(TTFont('微软雅黑', '微软雅黑.TTC'))

def load_data_from_folder(input_folder):
    """
    Load data from the folder containing cut.py outputs:
    - A folder with cropped advertisement video segments
    - A txt summary document
    - An mp4 video with advertisement boxes drawn
    """
    video_segments = []
    summary_text = ""
    boxed_video_path = ""
    
    # Get base folder name without path
    folder_name = os.path.basename(input_folder.rstrip('/'))
    
    # Expected file/folder names based on pattern
    summary_file = f"{folder_name}_summary.txt"
    segments_folder = f"{folder_name}_segments"
    boxed_video_pattern = f"{folder_name}_visulize_*.mp4"
    
    # Scan the folder for files
    if not os.path.exists(input_folder):
        print(f"Error: Input folder {input_folder} does not exist")
        return [], "", ""
    
    # Look for summary file
    summary_path = os.path.join(input_folder, summary_file)
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_text = f.read()
        except Exception as e:
            print(f"Error reading summary file {summary_file}: {e}")
    
    # Look for segments folder
    segments_path = os.path.join(input_folder, segments_folder)
    if os.path.exists(segments_path):
        for video_file in os.listdir(segments_path):
            if video_file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                video_segments.append({
                    'filename': video_file,
                    'path': os.path.join(segments_path, video_file),
                    'size': os.path.getsize(os.path.join(segments_path, video_file))
                })
    
    # Look for boxed video file
    for file in os.listdir(input_folder):
        if file.startswith(f"{folder_name}_visulize_") and file.lower().endswith('.mp4'):
            boxed_video_path = os.path.join(input_folder, file)
            break
    
    # Sort video segments by filename for consistent ordering
    video_segments.sort(key=lambda x: x['filename'])
    
    return video_segments, summary_text, boxed_video_path

def generate_pdf_report(video_segments, summary_text, boxed_video_path, output_pdf_path, input_folder):
    """
    Generate a PDF report summarizing the video advertisement analysis.
    """
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

def main(input_folder, output_directory=None):
    """
    Main function to load data from cut.py output folder and generate the PDF report.
    """
    # Get base folder name to generate PDF filename
    folder_name = os.path.basename(input_folder.rstrip('/'))
    pdf_filename = f"{folder_name}_analysis_report.pdf"
    
    if output_directory is None:
        # Generate PDF in the same directory as the input folder
        output_pdf_path = os.path.join(os.path.dirname(input_folder), pdf_filename)
    else:
        # Ensure output directory exists
        os.makedirs(output_directory, exist_ok=True)
        output_pdf_path = os.path.join(output_directory, pdf_filename)
    
    video_segments, summary_text, boxed_video_path = load_data_from_folder(input_folder)
    generate_pdf_report(video_segments, summary_text, boxed_video_path, output_pdf_path, input_folder)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_generate.py <input_folder> [output_directory]")
        print("Example: python pdf_generate.py ./yolo广告检测demo-产品文件夹")
        print("Example: python pdf_generate.py ./yolo广告检测demo-产品文件夹 ./reports")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    output_directory = sys.argv[2] if len(sys.argv) > 2 else None
    
    main(input_folder, output_directory)