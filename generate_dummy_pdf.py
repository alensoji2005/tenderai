import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def generate_dummy_boq(filepath):
    # Make sure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("Tender Document: OM-2026-0458", title_style))
    elements.append(Spacer(1, 12))
    
    # Intro
    elements.append(Paragraph("Technical Specifications and Bill of Quantities for the supply of Electrical Equipment.", normal_style))
    elements.append(Spacer(1, 12))
    
    # BOQ Table Data
    data = [
        ['S/N', 'Item Description', 'Quantity', 'Unit'],
        ['1', '11kV 500kVA Distribution Transformer', '15', 'Nos'],
        ['2', '33kV Current Transformer (CT)', '45', 'Nos'],
        ['3', 'High Voltage Insulators', '120', 'Sets'],
        ['4', 'Outdoor Ring Main Unit (RMU)', '5', 'Nos'],
    ]
    
    # Create Table
    t = Table(data, colWidths=[40, 250, 60, 60])
    
    # Add Style
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'), # Left align description
    ]))
    
    elements.append(t)
    
    # Build PDF
    doc.build(elements)
    print(f"Generated dummy PDF at: {filepath}")

if __name__ == "__main__":
    generate_dummy_boq("./documents/raw_pdfs/sample_tender.pdf")
