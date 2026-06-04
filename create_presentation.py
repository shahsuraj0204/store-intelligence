import subprocess
import sys
import os

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
except ModuleNotFoundError:
    print("Installing reportlab library for PDF generation...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def draw_slide_background(canvas, doc):
    canvas.saveState()
    # Dark blue-black background
    canvas.setFillColor(colors.HexColor("#0c0f16"))
    canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
    
    # Draw premium header/footer lines and branding
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(1)
    canvas.line(36, doc.pagesize[1] - 45, doc.pagesize[0] - 36, doc.pagesize[1] - 45) # Header border
    canvas.line(36, 45, doc.pagesize[0] - 36, 45) # Footer border
    
    # Header branding
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#a78bfa"))
    canvas.drawString(36, doc.pagesize[1] - 36, "APEX RETAIL | STORE INTELLIGENCE")
    
    # Footer branding & slide page numbers
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(36, 30, "Purplle Tech Challenge 2026 - Round 2 Submission")
    canvas.drawRightString(doc.pagesize[0] - 36, 30, f"Slide {canvas._pageNumber}")
    canvas.restoreState()

def build_deck():
    pdf_filename = "apex_retail_pitch_deck.pdf"
    # Document template in landscape mode
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=landscape(letter),
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Typography styles
    title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor("#ffffff"),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'SlideSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#94a3b8"),
        spaceAfter=30
    )
    
    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=20,
        textColor=colors.HexColor("#e2e8f0"),
        spaceAfter=10
    )
    
    bullet_style = ParagraphStyle(
        'SlideBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#cbd5e1"),
        leftIndent=20,
        firstLineIndent=-10,
        spaceAfter=12
    )

    purple_title_style = ParagraphStyle(
        'PurpleTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=48,
        leading=56,
        textColor=colors.HexColor("#a78bfa"),
        spaceAfter=10
    )
    
    story = []
    
    # Slide 1: Welcome & Overview
    story.append(Spacer(1, 40))
    story.append(Paragraph("APEX RETAIL", purple_title_style))
    story.append(Paragraph("AI Store Intelligence & Re-ID Shopper Journey Analytics", title_style))
    story.append(Paragraph("Built for the Purplle Tech Challenge 2026 | Round 2 Individual Submission", subtitle_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Author:</b> Suraj Shah (shahsuraj0204)", body_style))
    story.append(Paragraph("<b>Live Demo:</b> https://shahsuraj0204.github.io/store-intelligence/", body_style))
    story.append(Paragraph("<b>Core Pillars:</b> Edge Computer Vision • Cross-Camera Re-ID • POS Basket Analytics • AI Voice Copilot", body_style))
    story.append(PageBreak())
    
    # Slide 2: The Retail Problem
    story.append(Paragraph("Retail Visibility Bottlenecks", title_style))
    story.append(Paragraph("Traditional brick-and-mortar stores operate in a visual blindspot regarding customer behavior.", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("• <b>Blind Dwell Times:</b> High traffic aisles are seen, but shelf-level drop-offs and product affinities remain completely unknown.", bullet_style))
    story.append(Paragraph("• <b>Checkout Queue Abandonment:</b> Checkout queues spike rapidly without predictive notifications, resulting in lost sales and frustrated shoppers.", bullet_style))
    story.append(Paragraph("• <b>Static Store Layouts:</b> Product placements are determined by visual intuition rather than actual empirical correlation with customer paths.", bullet_style))
    story.append(PageBreak())
    
    # Slide 3: Technical Architecture
    story.append(Paragraph("Edge-to-Cloud System Flow", title_style))
    story.append(Paragraph("A lightweight, database-backed processing pipeline running efficiently on commodity hardware.", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("• <b>Edge CV Pipeline:</b> YOLOv8 object detection + ByteTrack frame-skipped inferences running on standard CPU feeds.", bullet_style))
    story.append(Paragraph("• <b>FastAPI REST & WebSockets:</b> Dynamic ingestion endpoints storage with SQLite, broadcasting updates asynchronously.", bullet_style))
    story.append(Paragraph("• <b>Interactive Web Dashboard:</b> Modern glassmorphism dark-themed dashboard showing live streams, conversion funnels, occupancy, and anomalies.", bullet_style))
    story.append(PageBreak())
    
    # Slide 4: Core Innovation 1: Spatial Re-ID
    story.append(Paragraph("Spatial Re-ID Journey Timeline", title_style))
    story.append(Paragraph("Tracing the exact movements of individual customer sessions across store cameras.", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("• <b>Stitched Pathways:</b> Resolves localized camera track IDs to a single global Visitor ID across non-overlapping feeds (Entrance -> Skincare -> Makeup -> Billing -> Exit).", bullet_style))
    story.append(Paragraph("• <b>Behavioral Telemetry:</b> Extracts precise dwell durations at shelves, billing queue wait times, and movement velocities.", bullet_style))
    story.append(Paragraph("• <b>Traffic Segmentation:</b> Identifies and filters employee tracks dynamically to ensure layout analysis is based purely on shopper behavior.", bullet_style))
    story.append(PageBreak())
    
    # Slide 5: Core Innovation 2: POS Correlation
    story.append(Paragraph("POS Basket Correlation A/B", title_style))
    story.append(Paragraph("Linking physical shopper paths directly with final transaction details.", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("• <b>POS Transaction Ingestion:</b> Analyzes transaction CSV files to extract buy-together product affinities (association rule mining).", bullet_style))
    story.append(Paragraph("• <b>Physical Flow Maps:</b> Tracks actual customer walk-through rates between related display racks (e.g., Haircare to Fragrance).", bullet_style))
    story.append(Paragraph("• <b>Placement Efficiency Index (PEI):</b> Automatically flags layout bottlenecks (e.g. shelves with high buy-together affinity but low physical shopper transitions) to guide physical relocations.", bullet_style))
    story.append(PageBreak())
    
    # Slide 6: Core Innovation 3: Voice Copilot
    story.append(Paragraph("Interactive Voice & Sound Copilot", title_style))
    story.append(Paragraph("An eyes-free, voice-assistant desk for multi-tasking store managers.", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("• <b>Web Audio Synthesizer:</b> Synthesizes clean sound chime pings and warning audio alerts directly inside the web browser.", bullet_style))
    story.append(Paragraph("• <b>TTS Notifications:</b> Automatically reads operational recommendations out loud (e.g., checkout queue build-ups) so managers can allocate staff instantly.", bullet_style))
    story.append(Paragraph("• <b>Auditory Alarms:</b> Plays real-time sirens when security breaches (unauthorized restricted office entries) are detected by the computer vision feed.", bullet_style))
    
    doc.build(story, onFirstPage=draw_slide_background, onLaterPages=draw_slide_background)
    print(f"Presentation deck successfully saved to {pdf_filename}!")

if __name__ == "__main__":
    build_deck()
