#!/usr/bin/env python3
"""Generates BENUTZERHANDBUCH_TIKTOK_SHOP.pdf (v2.1) using ReportLab."""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Benutzerhandbuch: TikTok-Shop Automation Pipeline (@bizpunk72)",
        author="TikTok-Shop Automation System v2.1",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18.5,
        leading=23,
        textColor=colors.HexColor("#111827"),
        spaceAfter=5,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13.5,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=5,
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=7,
        spaceAfter=3.5,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.3,
        leading=13,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=4.5,
    )
    bullet_style = ParagraphStyle(
        "BulletItem",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=body_style,
        fontSize=8.5,
        leading=11.5,
        spaceAfter=0,
    )
    cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#111827"),
    )
    header_cell = ParagraphStyle(
        "TableHeader",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # Header
    story.append(Paragraph("Benutzerhandbuch: TikTok-Shop Automation Pipeline (@bizpunk72)", title_style))
    story.append(
        Paragraph(
            "Version 2.1 | 100 % Hugging Face Inference | Test & Double-Down Regel | Sonntags-Radar | Telegram 1-Click Approval",
            subtitle_style,
        )
    )

    # 1. Systemübersicht
    story.append(Paragraph("1. Systemübersicht & Architektur (v2.1)", h1_style))
    story.append(
        Paragraph(
            "Dieses Handbuch beschreibt den täglichen automatisierten Betrieb deiner TikTok-Shop-Affiliate-Pipeline "
            "für den Account <b>@bizpunk72</b>. Das System übernimmt vollautomatisch die Produkt- und Referenzvideo-Auswahl "
            "nach der <b>Test & Double-Down-Regel</b>, den 1:1 Szenen-Nachbau über Hugging Face Inference "
            "(<b>flux-2/edit</b> & <b>wan-i2v</b>), das deutsche KI-Voiceover (<b>Jonas</b> für Tech/Gadgets/Auto, "
            "<b>Mia</b> für Beauty/Style/Gesundheit), die TikTok-Search-SEO-Beschreibung sowie die <b>1-Klick-Steuerung per Telegram</b>.",
            body_style,
        )
    )

    # 2. Täglicher & Wöchentlicher Zeitplan
    story.append(Paragraph("2. Täglicher & Wöchentlicher Zeitplan (Daily & Sunday Schedule)", h1_style))
    sched_data = [
        [
            Paragraph("Zeitpunkt", header_cell),
            Paragraph("n8n Workflow (Live-ID)", header_cell),
            Paragraph("Was automatisch im Hintergrund passiert", header_cell),
        ],
        [
            Paragraph("<b>Sonntags<br/>06:30 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_01_Product_And_Outlier_Radar</b><br/>(LS7wyhnaGW8nDfZl)", cell_style),
            Paragraph(
                "<b>Wöchentliches Trend-Radar:</b> Sucht automatisch 5 neue virale TikTok-Shop-Trendprodukte, "
                "trägt sie mit <b>status = candidate</b> in <b>tts_products</b> ein und schickt dir für jedes Produkt "
                "eine <b>Telegram-Karte mit 1-Klick-Buttons</b> (Freigeben / Winner / Pausieren).",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>Täglich<br/>07:00 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_01_Product_And_Outlier_Radar</b><br/>(LS7wyhnaGW8nDfZl)", cell_style),
            Paragraph(
                "Prüft live den Status von @bizpunk72 (Follower, Commerce-Berechtigung) und verarbeitet jederzeit "
                "deine 1-Klick-Telegram-Buttons (Approve / Winner / Pause) in Echtzeit.",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>Täglich<br/>07:30 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_02_Script_And_Scene_Architect</b><br/>(YytySstcIa4ifAlQ)", cell_style),
            Paragraph(
                "Wählt nach der <b>Test & Double-Down-Regel</b> das heutige Produkt + neuen Hook-Winkel aus, "
                "generiert via Hugging Face LLM (Qwen2.5-72B) die SEO-optimierte deutsche Beschreibung aus den "
                "Original-Specs, legt das Video in <b>tts_video_queue</b> an und schickt dir das <b>Tages-Briefing per Telegram</b>.",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>Täglich<br/>08:00 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_03_Visual_And_Clip_Factory</b><br/>(aLRjC7ZZ4MhqARJw)", cell_style),
            Paragraph(
                "Extrahiert die 8 Original-Keyframes aus dem Referenzvideo, führt über Hugging Face Inference "
                "(<b>fal-ai/flux-2/edit</b>) das 1:1 Image-to-Image mit dem Produkt-Packshot durch (inkl. Retry-Logik) "
                "und animiert Szene 1 per Image-to-Video (<b>fal-ai/wan-i2v</b>).",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>Täglich<br/>08:30 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_04_FFmpeg_Render_And_Zernio</b><br/>(19n3oP2Q1wlT1Djc)", cell_style),
            Paragraph(
                "Generiert das deutsche Voiceover via Hugging Face (<b>Jonas</b> bei Tech/Auto, <b>Mia</b> bei Beauty/Gesundheit), "
                "schneidet das 38s-Video (inkl. ~8,5s Warenkorb-CTA), mischt Sprache (100 %) + BGM (10 %), "
                "brennt kastenfreie farbige ASS-Untertitel ein und lädt das MP4 via Zernio als Entwurf zu @bizpunk72 hoch.",
                cell_style,
            ),
        ],
    ]

    sched_table = Table(sched_data, colWidths=[24 * mm, 52 * mm, 98 * mm])
    sched_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )
    story.append(sched_table)
    story.append(Spacer(1, 6))

    # 3. Die Test & Double-Down-Regel + 1-Klick Telegram-Freigabe
    story.append(Paragraph("3. Die „Test & Double-Down“-Regel & 1-Klick-Steuerung per Telegram", h1_style))
    story.append(
        Paragraph(
            "In <b>TTS_02</b> ist unsere 3-stufige TikTok-Shop-Skalierungslogik fest einprogrammiert:",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>1. Test-Phase (3 bis 4 Videos pro Produkt mit wechselnden Hooks):</b> Jedes freigegebene Produkt "
            "(<b>status = approved</b>) erhält im Wechsel mit den anderen Produkten bis zu 4 Videos, wobei TTS_02 "
            "automatisch bei jedem Video einen neuen Hook-Winkel (Variation #1 bis #4) wählt.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>2. Verlierer automatisch aussortieren (status = paused):</b> Hat ein Produkt 4 Videos erreicht und "
            "in <b>tts_published_posts</b> weder >= 1.000 Views noch >= 1 Bestellung erzielt, stuft TTS_02 es automatisch "
            "als <b>paused</b> ein und verschwendet keine weiteren Videos daran.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>3. Gewinner endlos skalieren (status = winner):</b> Sobald ein Produkt >= 1 Bestellung oder >= 5.000 Views "
            "erreicht (oder du in Telegram auf <b>„🏆 Als WINNER skalieren“</b> tippst), läuft es ohne Limit weiter und "
            "erhält dauerhaft 2–3 neue Hook-Videos pro Woche!",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>4. 1-Klick-Freigabe über Telegram:</b> Sowohl bei den 5 neuen Sonntags-Vorschlägen als auch beim "
            "täglichen 07:30-Uhr-Briefing bekommst du eine Telegram-Nachricht mit 3 Buttons: "
            "<b>[✅ Freigeben (Approved)]</b>, <b>[🏆 Winner (Dauer-Skalierung)]</b> und <b>[⏸️ Pausieren (Skip)]</b>. "
            "Ein Tipp auf dem Handy aktualisiert sofort den Status in <b>tts_products</b>!",
            bullet_style,
        )
    )

    story.append(PageBreak())

    # 4. Produkt-Katalog (Aktive Produkte + Neue Sonntags-Kandidaten)
    story.append(Paragraph("4. Deine Produkte im TikTok-Shop-Schaufenster (Showcase-Liste)", h1_style))
    story.append(
        Paragraph(
            "Hier siehst du alle 11 aktuell in <b>tts_products</b> angelegten Produkte (5 aktive Start-Produkte + "
            "6 vorbereitete Trend-Kandidaten, die du jederzeit per 1-Klick in Telegram freigeben kannst):",
            body_style,
        )
    )

    prod_data = [
        [
            Paragraph("Product Key", header_cell),
            Paragraph("Produkt im TikTok Shop Marketplace", header_cell),
            Paragraph("Stimme", header_cell),
            Paragraph("Status", header_cell),
        ],
        [
            Paragraph("prod_magsafe_3in1_fold", cell_bold),
            Paragraph("<b>3-in-1 Faltbare Magnetische Ladestation & Handyhalter (15W)</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("approved (Aktiv)", cell_style),
        ],
        [
            Paragraph("prod_7in1_tech_cleaner", cell_bold),
            Paragraph("<b>7-in-1 / 8-in-1 Elektronik, Tastatur & AirPods Reinigungs-Set</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("approved (Aktiv)", cell_style),
        ],
        [
            Paragraph("prod_wireless_carplay_mini", cell_bold),
            Paragraph("<b>Ultra-Mini 5.8GHz Wireless CarPlay & Android Auto Stick</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("approved (Aktiv)", cell_style),
        ],
        [
            Paragraph("prod_retractable_car_charger_120w", cell_bold),
            Paragraph("<b>4-in-1 Einziehbares Auto-Schnellladegerät mit 2 Rollkabeln</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("approved (Aktiv)", cell_style),
        ],
        [
            Paragraph("prod_magnetic_led_motion_bar", cell_bold),
            Paragraph("<b>Magnetische Ultra-Slim LED-Schrankleiste mit Bewegungsmelder</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("approved (Aktiv)", cell_style),
        ],
        [
            Paragraph("prod_medicube_collagen_cream", cell_bold),
            Paragraph("<b>Medicube Collagen Jelly Cream (Glass Skin & Straffung)</b>", cell_style),
            Paragraph("Mia (W)", cell_style),
            Paragraph("candidate (Wartet auf Freigabe)", cell_style),
        ],
        [
            Paragraph("prod_vacuum_mag_car_holder", cell_bold),
            Paragraph("<b>Elektrischer Vakuum-Magnet Handyhalter (360° Auto & Spiegel)</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("candidate (Sonntags-Radar)", cell_style),
        ],
        [
            Paragraph("prod_mini_thermal_printer_bt", cell_bold),
            Paragraph("<b>Tintenloser Mini-Bluetooth-Etiketten- & Fotodrucker</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("candidate (Sonntags-Radar)", cell_style),
        ],
        [
            Paragraph("prod_electric_spin_scrubber_7in1", cell_bold),
            Paragraph("<b>Elektrische 7-in-1 Rotations-Reinigungsbürste mit Teleskopstiel</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("candidate (Sonntags-Radar)", cell_style),
        ],
        [
            Paragraph("prod_magsafe_slim_powerbank_10k", cell_bold),
            Paragraph("<b>Ultra-Slim 10.000mAh MagSafe Aluminium-Powerbank</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("candidate (Sonntags-Radar)", cell_style),
        ],
        [
            Paragraph("prod_biodance_collagen_mask_4er", cell_bold),
            Paragraph("<b>Biodance Bio-Collagen Real Deep Hydrogel Maske (Overnight)</b>", cell_style),
            Paragraph("Mia (W)", cell_style),
            Paragraph("candidate (Sonntags-Radar)", cell_style),
        ],
    ]

    prod_table = Table(prod_data, colWidths=[48 * mm, 68 * mm, 20 * mm, 38 * mm])
    prod_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    story.append(prod_table)
    story.append(Spacer(1, 8))

    # 5. Deine täglichen ToDos (5-Minuten-Routine)
    story.append(Paragraph("5. Deine täglichen ToDos (Deine 5-Minuten-Routine am Handy)", h1_style))
    story.append(
        Paragraph(
            "• <b>1. Morgens um 07:30 Uhr (Telegram-Nachricht checken – 10 Sek.):</b> Du siehst auf Telegram, "
            "welches Produkt und welcher Hook heute produziert wird. Bei Bedarf kannst du dort direkt auf "
            "<b>[🏆 Winner]</b> oder <b>[⏸️ Pausieren]</b> tippen.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>2. Morgens ab 08:35 Uhr (TikTok-App öffnen & Produkt verlinken – 2 Min.):</b> Öffne in der TikTok-App "
            "(<b>@bizpunk72</b>) -> <b>Posteingang -> Systembenachrichtigungen</b> -> tippe auf <i>„Dein Video ist bereit“</i> -> "
            "tippe auf <b>„+ Link hinzufügen -> Produkt“</b> -> wähle das Produkt aus deinem Schaufenster -> prüfe, "
            "dass <b>„KI-generierter Inhalt“</b> aktiv ist -> tippe auf <b>„Veröffentlichen“</b>!",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>3. Sonntags (Neue Trend-Kandidaten per 1-Klick in Telegram freigeben – 2 Min.):</b> Jeden Sonntag um 06:30 Uhr "
            "schickt dir TTS_01 neue Trend-Kandidaten auf Telegram. Füge deine Favoriten in der TikTok-App deinem "
            "Schaufenster hinzu und tippe in Telegram auf <b>[✅ Freigeben (Approved)]</b>!",
            bullet_style,
        )
    )

    doc.build(story)
    print(f"Successfully generated v2.1 PDF manual: {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == "__main__":
    out_pdf = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "BENUTZERHANDBUCH_TIKTOK_SHOP.pdf",
    )
    build_pdf(out_pdf)
