"""
ExamAI - PDF Service
Handles PDF to image conversion and graded report PDF generation.
"""

import io
import fitz  # PyMuPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from config import DPI


def pdf_to_images(pdf_bytes: bytes) -> list[bytes]:
    """
    Convert each page of a PDF into a PNG image.
    
    Uses PyMuPDF to render pages at the configured DPI.
    Gemini will read these images directly with its vision model.
    
    Args:
        pdf_bytes: Raw PDF file bytes
    
    Returns:
        List of PNG image bytes, one per page
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    
    zoom = DPI / 72  # 72 is the default PDF DPI
    matrix = fitz.Matrix(zoom, zoom)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    
    doc.close()
    return images


def generate_report_pdf(grading_results: dict) -> bytes:
    """
    Generate a formatted PDF report from grading results.
    
    Creates a professional report showing:
    - Header with student info and overall score
    - Per-question breakdown with marks and reasoning
    - Summary footer
    
    Args:
        grading_results: Dictionary from gemini_service.grade_exam_sheet()
    
    Returns:
        PDF file as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor("#666666"),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#16213e"),
        spaceBefore=16,
        spaceAfter=8,
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=4,
        leading=14,
    )
    
    reasoning_style = ParagraphStyle(
        'Reasoning',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        leftIndent=12,
        spaceAfter=8,
        leading=12,
        fontName='Helvetica-Oblique',
    )
    
    # Build document elements
    elements = []
    
    # ── Title ──
    elements.append(Paragraph("📝 ExamAI — Grading Report", title_style))
    elements.append(Paragraph("AI-Powered Handwritten Exam Evaluation", subtitle_style))
    
    # ── Divider ──
    elements.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor("#e94560"),
        spaceAfter=16
    ))
    
    # ── Student Info & Summary ──
    student_name = grading_results.get("student_name", "Unknown")
    total_obtained = grading_results.get("total_marks_obtained", 0)
    total_possible = grading_results.get("total_marks_possible", 0)
    percentage = grading_results.get("percentage", 0)
    
    # Summary table
    summary_data = [
        ["Student Name", student_name],
        ["Total Marks", f"{total_obtained} / {total_possible}"],
        ["Percentage", f"{percentage:.1f}%"],
        ["Grade", _get_grade(percentage)],
    ]
    
    summary_table = Table(summary_data, colWidths=[120, 300])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f0f0f5")),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#16213e")),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # ── Per-Question Breakdown ──
    elements.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor("#cccccc"),
        spaceAfter=12
    ))
    elements.append(Paragraph("Question-wise Breakdown", heading_style))
    
    results = grading_results.get("results", [])
    
    # Question table header
    q_header = ["Q.No", "Max Marks", "Marks Obtained", "Status"]
    q_data = [q_header]
    
    for result in results:
        q_num = str(result.get("question_number", "?"))
        max_marks = result.get("max_marks", 0)
        marks_obtained = result.get("marks_obtained", 0)
        
        if marks_obtained >= max_marks:
            status = "✅ Full"
        elif marks_obtained > 0:
            status = "⚠️ Partial"
        else:
            status = "❌ Wrong"
        
        q_data.append([q_num, str(max_marks), str(marks_obtained), status])
    
    q_table = Table(q_data, colWidths=[60, 90, 110, 90])
    q_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f8fc")]),
    ]))
    
    elements.append(q_table)
    elements.append(Spacer(1, 20))
    
    # ── Detailed Reasoning ──
    elements.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor("#cccccc"),
        spaceAfter=12
    ))
    elements.append(Paragraph("Detailed Evaluation", heading_style))
    
    for result in results:
        q_num = result.get("question_number", "?")
        q_text = result.get("question_text", "")
        student_ans = result.get("student_answer_summary", "No answer provided")
        expected_ans = result.get("expected_answer_summary", "")
        marks = result.get("marks_obtained", 0)
        max_m = result.get("max_marks", 0)
        reasoning = result.get("reasoning", "")
        
        # Question header
        elements.append(Paragraph(
            f"<b>Question {q_num}</b> — {marks}/{max_m} marks",
            heading_style
        ))
        
        if q_text:
            elements.append(Paragraph(f"<i>{q_text}</i>", body_style))
        
        elements.append(Paragraph(
            f"<b>Student's Answer:</b> {_sanitize(student_ans)}",
            body_style
        ))
        elements.append(Paragraph(
            f"<b>Expected Answer:</b> {_sanitize(expected_ans)}",
            body_style
        ))
        elements.append(Paragraph(
            f"<b>Evaluation:</b> {_sanitize(reasoning)}",
            reasoning_style
        ))
        elements.append(Spacer(1, 8))
    
    # ── Overall Feedback ──
    overall_feedback = grading_results.get("overall_feedback", "")
    if overall_feedback:
        elements.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.HexColor("#cccccc"),
            spaceAfter=12
        ))
        elements.append(Paragraph("Overall Feedback", heading_style))
        elements.append(Paragraph(_sanitize(overall_feedback), body_style))
    
    # ── Footer ──
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor("#e94560"),
        spaceAfter=8
    ))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        "Generated by ExamAI — AI-Powered Exam Grading System | "
        "Powered by Google Gemini 3",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _get_grade(percentage: float) -> str:
    """Convert percentage to letter grade."""
    if percentage >= 90:
        return "A+ (Outstanding)"
    elif percentage >= 80:
        return "A (Excellent)"
    elif percentage >= 70:
        return "B+ (Very Good)"
    elif percentage >= 60:
        return "B (Good)"
    elif percentage >= 50:
        return "C (Average)"
    elif percentage >= 40:
        return "D (Below Average)"
    else:
        return "F (Needs Improvement)"


def _sanitize(text: str) -> str:
    """Sanitize text for ReportLab XML compatibility."""
    if not text:
        return ""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text
