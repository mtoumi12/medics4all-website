"""
Medics4ALL Investor One-Pager Generator
========================================
Generates a print-ready single-page PDF for cold investor outreach.

Run:
    python scripts/generate_investor_onepager.py

Output:
    medics4all_investor_onepager.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

# ---------- Brand palette ----------
NAVY = HexColor("#0F1F44")
BLUE = HexColor("#1E40AF")
ORANGE = HexColor("#EA580C")
GOLD = HexColor("#CA8A04")
SLATE = HexColor("#475569")
GREEN = HexColor("#10B981")
LIGHT = HexColor("#F1F5F9")
INK = HexColor("#0F172A")
MUTED = HexColor("#64748B")

PAGE_W, PAGE_H = LETTER
MARGIN = 0.45 * inch

OUTPUT = Path(__file__).resolve().parents[1] / "medics4all_investor_onepager.pdf"
LOGO = Path(__file__).resolve().parents[1] / "logo-m4.png"


def _para(text: str, size: int = 9, color=INK, bold: bool = False, leading: float | None = None) -> Paragraph:
    style = ParagraphStyle(
        "p",
        parent=getSampleStyleSheet()["BodyText"],
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading or size * 1.25,
        textColor=color,
        spaceBefore=0,
        spaceAfter=0,
    )
    return Paragraph(text, style)


def draw_header(c: canvas.Canvas) -> float:
    """Navy header with logo + tagline. Returns the y-cursor below the header."""
    band_h = 0.95 * inch
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - band_h, PAGE_W, band_h, stroke=0, fill=1)

    # Logo (graceful fallback if missing)
    try:
        if LOGO.exists():
            c.drawImage(
                str(LOGO),
                MARGIN,
                PAGE_H - band_h + 0.18 * inch,
                width=0.6 * inch,
                height=0.6 * inch,
                mask="auto",
                preserveAspectRatio=True,
            )
    except Exception:
        pass

    # Wordmark
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(MARGIN + 0.75 * inch, PAGE_H - band_h + 0.55 * inch, "Medics4ALL")
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#A5B4FC"))
    c.drawString(
        MARGIN + 0.75 * inch,
        PAGE_H - band_h + 0.34 * inch,
        "AI Medical Scribing — Built Once. Monetized Three Ways.",
    )

    # Right-aligned status line
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - band_h + 0.55 * inch, "Pre-Seed · Raising $2.5M")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(HexColor("#A5B4FC"))
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - band_h + 0.36 * inch, "April 2026 · medics4all.com")

    return PAGE_H - band_h - 0.18 * inch


def draw_thesis(c: canvas.Canvas, y: float) -> float:
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, y, "The Thesis")
    y -= 0.20 * inch

    p = _para(
        "<b>DeepScribe for the 80% of the world that doesn't speak English.</b> "
        "We sell a modern English AI scribe to US/UK clinics, then layer a unique "
        "Arabic-dialect translation engine on top — owned by us, licensed to scribing "
        "companies and sold as enterprise compliance packs to MENA hospitals.",
        size=9.5,
        leading=12.5,
    )
    w, h = p.wrap(PAGE_W - 2 * MARGIN, 1 * inch)
    p.drawOn(c, MARGIN, y - h)
    return y - h - 0.16 * inch


def draw_skus(c: canvas.Canvas, y: float) -> float:
    """Three colored SKU cards laid out side-by-side."""
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, y, "Three SKUs · Three Buyers · One Foundation")
    y -= 0.20 * inch

    avail = PAGE_W - 2 * MARGIN
    gap = 0.10 * inch
    card_w = (avail - 2 * gap) / 3
    card_h = 1.55 * inch

    cards = [
        {
            "title": "TIER 1 — CORE",
            "color": BLUE,
            "subtitle": "English Medical Scribe",
            "price": "$199–$499 / provider / mo",
            "buyer": "US/UK/EU hospitals & clinics",
            "bullets": [
                "Real-time ASR + diarization",
                "SOAP / H&P note generation",
                "Epic · Cerner · Athena (FHIR)",
                "HIPAA + audit trail",
            ],
        },
        {
            "title": "TIER 2 — TRANSLATE",
            "color": ORANGE,
            "subtitle": "Multilingual Plug-in (API)",
            "price": "$0.05–0.15/min  ·  +$99/seat",
            "buyer": "Scribing co's + multilingual hospitals",
            "bullets": [
                "15+ Arabic dialects (Najdi, Hijazi…)",
                "FR · ES · Hausa · Mandarin (P2)",
                "Dialect auto-routing",
                "White-label / OEM API",
            ],
        },
        {
            "title": "TIER 3 — COMPLIANCE",
            "color": GOLD,
            "subtitle": "MENA / Gulf Pack",
            "price": "$50K–$250K / hospital / yr",
            "buyer": "Saudi · UAE · Egypt hospitals",
            "bullets": [
                "Bilingual EN+AR records",
                "CBAHI / JCI templates",
                "Local EHR adapters",
                "Arabic patient summaries",
            ],
        },
    ]

    for i, card in enumerate(cards):
        x = MARGIN + i * (card_w + gap)

        # Header band
        c.setFillColor(card["color"])
        c.rect(x, y - 0.42 * inch, card_w, 0.42 * inch, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(x + 0.10 * inch, y - 0.18 * inch, card["title"])
        c.setFont("Helvetica", 8.5)
        c.drawString(x + 0.10 * inch, y - 0.32 * inch, card["subtitle"])

        # Body
        body_y = y - 0.42 * inch
        c.setFillColor(LIGHT)
        c.rect(x, body_y - card_h + 0.42 * inch, card_w, card_h - 0.42 * inch, stroke=0, fill=1)

        # Price
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 0.10 * inch, body_y - 0.16 * inch, card["price"])

        # Buyer
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(x + 0.10 * inch, body_y - 0.30 * inch, card["buyer"])

        # Bullets
        c.setFillColor(INK)
        c.setFont("Helvetica", 8)
        for j, bullet in enumerate(card["bullets"]):
            c.drawString(x + 0.10 * inch, body_y - 0.50 * inch - j * 0.16 * inch, f"• {bullet}")

    return y - card_h - 0.18 * inch


def draw_market_traction(c: canvas.Canvas, y: float) -> float:
    """Two-column: Market & Traction left, Foundation/Moat right."""
    avail = PAGE_W - 2 * MARGIN
    col_w = (avail - 0.15 * inch) / 2

    # ----- LEFT COLUMN: Market + Why Now -----
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, y, "Market & Why Now")
    y_left = y - 0.20 * inch

    market_text = (
        "<b>$8.6B</b> US medical scribing market growing <b>23% CAGR</b>. "
        "<b>$2.1B</b> MENA digital health, mandated by Saudi Vision 2030 + CBAHI. "
        "Doctors spend <b>40%</b> of clinical time on documentation; physician "
        "burnout is a top-3 healthcare CEO priority. <b>26%</b> of US patient encounters "
        "involve a non-English primary speaker — a gap every incumbent ignores."
    )
    p = _para(market_text, size=8.5, leading=11)
    w, h = p.wrap(col_w, 2 * inch)
    p.drawOn(c, MARGIN, y_left - h)
    y_left -= h + 0.10 * inch

    # KPI strip
    kpi_h = 0.45 * inch
    kpi_w = (col_w - 0.16 * inch) / 3
    kpis = [("$8.6B", "US TAM"), ("23%", "CAGR"), ("26%", "Non-EN pts")]
    for i, (big, small) in enumerate(kpis):
        kx = MARGIN + i * (kpi_w + 0.08 * inch)
        c.setFillColor(NAVY)
        c.roundRect(kx, y_left - kpi_h, kpi_w, kpi_h, 4, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(kx + kpi_w / 2, y_left - 0.20 * inch, big)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(HexColor("#A5B4FC"))
        c.drawCentredString(kx + kpi_w / 2, y_left - 0.35 * inch, small)
    y_left -= kpi_h + 0.12 * inch

    # ----- RIGHT COLUMN: Moat + Traction -----
    rx = MARGIN + col_w + 0.15 * inch
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(rx, y, "Moat & Traction Plan")
    y_right = y - 0.20 * inch

    moat_lines = [
        ("Data", "SADA22 + proprietary medical-dialect corpus"),
        ("Knowledge", "Medical RAG: ICD-10, SNOMED, RxNorm + dialects"),
        ("Regulatory", "CBAHI/JCI — US incumbents won't bother for years"),
        ("Brand", "Arabic-first product, Arabic-speaking team in MENA"),
    ]
    label_col_w = 0.78 * inch
    for label, desc in moat_lines:
        c.setFillColor(BLUE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(rx, y_right, f"▸ {label}")
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        c.drawString(rx + label_col_w, y_right, desc)
        y_right -= 0.16 * inch

    y_right -= 0.05 * inch
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(rx, y_right, "Year-1 Plan: $310K ARR  ·  Year-3: $15.45M ARR")
    y_right -= 0.14 * inch
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.8)
    c.drawString(rx, y_right, "50 providers + 1 scribing-co partnership → 2,500 providers + 8 MENA hospitals")

    return min(y_left, y_right - 0.05 * inch) - 0.10 * inch


def draw_competition(c: canvas.Canvas, y: float) -> float:
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, y, "Competitive Position")
    y -= 0.20 * inch

    headers = ["Vendor", "Price/seat", "Multilingual", "Open API", "MENA/CBAHI"]
    rows = [
        ["Nuance DAX (MSFT)", "$600–1,200", "Limited", "No", "No"],
        ["Abridge", "$250–400", "Spanish", "No", "No"],
        ["DeepScribe", "$349–499", "No", "No", "No"],
        ["Suki", "$300", "No", "Partner", "No"],
        ["Nabla", "$119–199", "FR/ES/DE", "Partner", "No"],
        ["Medics4ALL", "$199–499", "Arabic+15 dialects", "Yes", "Yes"],
    ]

    avail = PAGE_W - 2 * MARGIN
    col_widths = [1.45 * inch, 1.15 * inch, 1.55 * inch, 1.0 * inch, avail - (1.45 + 1.15 + 1.55 + 1.0) * inch]
    row_h = 0.20 * inch

    # Header row
    c.setFillColor(NAVY)
    c.rect(MARGIN, y - row_h, avail, row_h, stroke=0, fill=1)
    cx = MARGIN
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    for i, h_text in enumerate(headers):
        c.drawString(cx + 0.08 * inch, y - row_h + 0.06 * inch, h_text)
        cx += col_widths[i]
    y -= row_h

    # Body rows
    for r_idx, row in enumerate(rows):
        is_us = row[0] == "Medics4ALL"
        if is_us:
            c.setFillColor(HexColor("#DBEAFE"))
            c.rect(MARGIN, y - row_h, avail, row_h, stroke=0, fill=1)
        elif r_idx % 2 == 0:
            c.setFillColor(LIGHT)
            c.rect(MARGIN, y - row_h, avail, row_h, stroke=0, fill=1)

        cx = MARGIN
        c.setFillColor(BLUE if is_us else INK)
        c.setFont("Helvetica-Bold" if is_us else "Helvetica", 8.5)
        for i, val in enumerate(row):
            c.drawString(cx + 0.08 * inch, y - row_h + 0.06 * inch, val)
            cx += col_widths[i]
        y -= row_h

    return y - 0.12 * inch


def draw_ask_team(c: canvas.Canvas, y: float) -> float:
    avail = PAGE_W - 2 * MARGIN
    col_w = (avail - 0.15 * inch) / 2

    # ----- LEFT: The Ask -----
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN, y, "The Ask — $2.5M Pre-Seed")
    y_left = y - 0.20 * inch

    use_of_funds = [
        ("ML / engineering team (5 FTE × 12 mo)", "$1.4M", BLUE),
        ("HIPAA + SOC2 compliance + Epic Orchard", "$0.25M", ORANGE),
        ("Foundation R&D (SADA22 fine-tune + Med RAG)", "$0.30M", GOLD),
        ("GTM (US clinics + 1 MENA design partner)", "$0.35M", GREEN),
        ("Buffer + legal + ops", "$0.20M", SLATE),
    ]
    bar_total_w = col_w - 0.10 * inch
    bar_max = 1.4
    for label, amt, color in use_of_funds:
        amt_val = float(amt.replace("$", "").replace("M", ""))
        bw = (amt_val / bar_max) * bar_total_w
        c.setFillColor(color)
        c.rect(MARGIN, y_left - 0.16 * inch, bw, 0.13 * inch, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica", 7.5)
        c.drawString(MARGIN, y_left - 0.025 * inch, label)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(MARGIN + col_w - 0.05 * inch, y_left - 0.025 * inch, amt)
        y_left -= 0.22 * inch

    # ----- RIGHT: Milestones from this round -----
    rx = MARGIN + col_w + 0.15 * inch
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(rx, y, "What This Buys (18 months)")
    y_right = y - 0.20 * inch

    milestones = [
        "Core MVP shipped to 3 design-partner clinics by month 9",
        "SOC 2 Type 1 + HIPAA-ready architecture",
        "Translate plug-in beta with first scribing-co API customer",
        "1 MENA flagship hospital pilot (CBAHI track)",
        "$300K+ ARR · clear Series A metrics",
    ]
    for m in milestones:
        c.setFillColor(GREEN)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(rx, y_right, "✓")
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        c.drawString(rx + 0.18 * inch, y_right, m)
        y_right -= 0.17 * inch

    return min(y_left, y_right) - 0.05 * inch


def draw_footer(c: canvas.Canvas) -> None:
    band_h = 0.50 * inch
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, band_h, stroke=0, fill=1)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(MARGIN, band_h - 0.20 * inch, "Contact")
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN + 0.55 * inch, band_h - 0.20 * inch, "founders@medics4all.com  ·  medics4all.com")

    c.setFillColor(HexColor("#A5B4FC"))
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawRightString(
        PAGE_W - MARGIN,
        band_h - 0.20 * inch,
        "Confidential — for discussion purposes only · v1.0 · April 2026",
    )

    # Tagline strip
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(
        PAGE_W / 2,
        band_h - 0.40 * inch,
        "Build Once. Monetize Three Ways.",
    )


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT), pagesize=LETTER)
    c.setTitle("Medics4ALL — Investor One-Pager")
    c.setAuthor("Medics4ALL")
    c.setSubject("Pre-Seed Investor Brief")
    c.setKeywords("AI medical scribe, multilingual, Arabic dialect, HIPAA, MENA")

    y = draw_header(c)
    y = draw_thesis(c, y)
    y = draw_skus(c, y)
    y = draw_market_traction(c, y)
    y = draw_competition(c, y)
    y = draw_ask_team(c, y)
    draw_footer(c)

    c.showPage()
    c.save()
    return OUTPUT


if __name__ == "__main__":
    out = build()
    print(f"OK · wrote {out}  ({out.stat().st_size / 1024:.1f} KB)")
