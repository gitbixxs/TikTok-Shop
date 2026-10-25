#!/usr/bin/env python3
"""Generates BENUTZERHANDBUCH_TIKTOK_SHOP.pdf using ReportLab."""

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
        author="TikTok-Shop Automation System v2.0",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=24,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=14,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "BulletItem",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3.5,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=body_style,
        fontSize=8.8,
        leading=12,
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
            "Version 2.0 | 100 % Hugging Face Inference | 1:1 Video-Cloning | Stimmen: Jonas & Mia | TikTok Search SEO",
            subtitle_style,
        )
    )

    # 1. Systemübersicht
    story.append(Paragraph("1. Systemübersicht & Architektur", h1_style))
    story.append(
        Paragraph(
            "Dieses Handbuch beschreibt den täglichen automatisierten Betrieb deiner TikTok-Shop-Affiliate-Pipeline "
            "für den Account <b>@bizpunk72</b>. Das System übernimmt vollautomatisch die Produkt- und Referenzvideo-Auswahl, "
            "den 1:1 Szenen-Nachbau mit deinem Produkt über Hugging Face Inference (<b>flux-2/edit</b> & <b>wan-i2v</b>), "
            "das deutsche KI-Voiceover (<b>Jonas</b> für Tech/Gadgets/Auto, <b>Mia</b> für Beauty/Style/Gesundheit), "
            "die TikTok-Search-SEO-Beschreibung aus den Original-Produktdaten sowie das 38-Sekunden-FFmpeg-Rendering "
            "und den Upload als Entwurf in deinen TikTok-Posteingang.",
            body_style,
        )
    )

    # 2. Täglicher Zeitplan
    story.append(Paragraph("2. Wie die 4 Workflows täglich getaktet sind (Daily Schedule)", h1_style))
    story.append(
        Paragraph(
            "Alle 4 n8n-Workflows verfügen über fest abgestimmte tägliche Zeit-Trigger (Schedule Triggers), "
            "sodass jeden Morgen zwischen <b>07:00 Uhr und 08:35 Uhr</b> automatisch ein komplett fertiges "
            "38-Sekunden-Verkaufsvideo produziert wird und ab 08:35 Uhr in deiner TikTok-App bereitliegt:",
            body_style,
        )
    )

    sched_data = [
        [
            Paragraph("Uhrzeit", header_cell),
            Paragraph("n8n Workflow (ID)", header_cell),
            Paragraph("Was automatisch im Hintergrund passiert", header_cell),
        ],
        [
            Paragraph("<b>07:00 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_01_Product_And_Outlier_Radar</b><br/>(3qVjo7qjfxxMGvdK)", cell_style),
            Paragraph(
                "Prüft live den Status von @bizpunk72 (Follower, Commerce-Berechtigung) und gleicht alle "
                "freigegebenen Produkte (status = approved) in <b>tts_products</b> mit viralen Referenzvideos "
                "in <b>tts_outlier_videos</b> ab.",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>07:30 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_02_Script_And_Scene_Architect</b><br/>(aVcsOiTDQw0XPInh)", cell_style),
            Paragraph(
                "Wählt automatisch das nächste freigegebene Produkt aus <b>tts_products</b>, zerlegt das Referenzvideo "
                "in 8 Funktions-Szenen (7x 4,5s + 1x 6,5s = 38s), generiert via Hugging Face LLM "
                "(Qwen2.5-72B) die SEO-optimierte deutsche Beschreibung aus der Original-Produktbeschreibung "
                "und legt den Auftrag in <b>tts_video_queue</b> (render_status = queued).",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>08:00 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_03_Visual_And_Clip_Factory</b><br/>(aLRjC7ZZ4MhqARJw)", cell_style),
            Paragraph(
                "Extrahiert die 8 Original-Keyframes aus dem Referenzvideo, führt über Hugging Face Inference "
                "(<b>fal-ai/flux-2/edit</b>) das 1:1 Image-to-Image mit dem Produkt-Packshot durch (inkl. Retry-Logik) "
                "und animiert den Hook-Clip per Image-to-Video (<b>fal-ai/wan-i2v</b>). Setzt danach "
                "render_status = ready_for_ffmpeg.",
                cell_style,
            ),
        ],
        [
            Paragraph("<b>08:30 Uhr</b>", cell_bold),
            Paragraph("<b>TTS_04_FFmpeg_Render_And_Zernio</b><br/>(19n3oP2Q1wlT1Djc)", cell_style),
            Paragraph(
                "Generiert das deutsche Voiceover via Hugging Face (<b>Jonas</b> bei Tech/Auto, <b>Mia</b> bei Beauty/Gesundheit) "
                "in Satzblöcken < 230 Zeichen (kein Satzabbruch!), schneidet das 38s-Video (inkl. ~8,5s Warenkorb-CTA), "
                "mischt Sprache (100 %) + BGM (10 %), brennt kastenfreie farbige ASS-Untertitel ein und lädt das MP4 "
                "via Zernio (draft: true, is_ai_generated: true) in deine TikTok-App hoch.",
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
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(sched_table)
    story.append(Spacer(1, 8))

    # 3. Wie weiß ich, welche Produkte ich meinem TikTok-Shop-Schaufenster hinzufügen muss?
    story.append(Paragraph("3. Woher weiß ich, welche Produkte ich meinem TikTok-Shop hinzufügen muss?", h1_style))
    story.append(
        Paragraph(
            "Unsere Pipeline arbeitet nach einer klaren, vorhersehbaren Reihenfolge aus der Tabelle <b>tts_products</b>. "
            "Damit du beim Veröffentlichen eines Entwurfs in der TikTok-App das passende Produkt mit 1 Klick "
            "als orangenen Warenkorb anhängen kannst, müssen genau diese Produkte vorher in deinem "
            "<b>TikTok-Shop-Schaufenster (Showcase)</b> liegen:",
            body_style,
        )
    )

    prod_data = [
        [
            Paragraph("Prio / Tag", header_cell),
            Paragraph("Product Key", header_cell),
            Paragraph("Produkt im TikTok Shop Marketplace (Suchbegriff)", header_cell),
            Paragraph("Stimme", header_cell),
            Paragraph("Status", header_cell),
        ],
        [
            Paragraph("<b>Produkt 1</b>", cell_bold),
            Paragraph("prod_magsafe_3in1_fold", cell_style),
            Paragraph("<b>3-in-1 Faltbare Magnetische Ladestation & Handyhalter (15W)</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("Im Shop & Video fertig", cell_style),
        ],
        [
            Paragraph("<b>Produkt 2</b>", cell_bold),
            Paragraph("prod_7in1_tech_cleaner", cell_style),
            Paragraph("<b>7-in-1 / 8-in-1 Elektronik, Tastatur & AirPods Reinigungs-Set</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("Video fertig (jetzt im Shop hinzufügen!)", cell_style),
        ],
        [
            Paragraph("<b>Produkt 3</b>", cell_bold),
            Paragraph("prod_wireless_carplay_mini", cell_style),
            Paragraph("<b>Ultra-Mini 5.8GHz Wireless CarPlay & Android Auto Adapter Stick</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("Als Nächstes in Pipeline", cell_style),
        ],
        [
            Paragraph("<b>Produkt 4</b>", cell_bold),
            Paragraph("prod_retractable_car_charger_120w", cell_style),
            Paragraph("<b>4-in-1 Einziehbares Auto-Schnellladegerät mit 2 Rollkabeln</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("Freigegeben (approved)", cell_style),
        ],
        [
            Paragraph("<b>Produkt 5</b>", cell_bold),
            Paragraph("prod_magnetic_led_motion_bar", cell_style),
            Paragraph("<b>Magnetische Ultra-Slim LED-Schrankleiste mit Bewegungsmelder</b>", cell_style),
            Paragraph("Jonas (M)", cell_style),
            Paragraph("Freigegeben (approved)", cell_style),
        ],
        [
            Paragraph("<b>Produkt 6 (Phase 2)</b>", cell_bold),
            Paragraph("prod_medicube_collagen_cream", cell_style),
            Paragraph("<b>Medicube Collagen Jelly Cream (Skincare / Glass Skin)</b>", cell_style),
            Paragraph("Mia (W)", cell_style),
            Paragraph("Kandidat (Beauty)", cell_style),
        ],
    ]

    prod_table = Table(prod_data, colWidths=[22 * mm, 42 * mm, 64 * mm, 20 * mm, 26 * mm])
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
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(prod_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("So fügst du die Produkte in 2 Minuten deinem TikTok-Schaufenster hinzu:", h2_style))
    story.append(
        Paragraph(
            "• <b>Schritt 1:</b> Öffne die TikTok-App -> <b>Profil (@bizpunk72)</b> -> <b>TikTok Studio</b> -> "
            "<b>TikTok Shop für Creator</b> -> <b>Produkt-Marktplatz (Product Marketplace)</b>.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Schritt 2:</b> Gib den Produktnamen aus der obigen Tabelle in die Suche ein (achte auf <b>15–30 % Provision</b> "
            "und gute Shop-Bewertung >= 4,5 Sterne) und tippe auf <b>„Hinzufügen“ (Zum Schaufenster hinzufügen)</b>.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Schritt 3 (Eigenes Wunschprodukt hinzufügen):</b> Wenn du im TikTok-Marktplatz ein neues Trend-Produkt entdeckst, "
            "trage es einfach in n8n / Baserow in die Tabelle <b>tts_products</b> mit <b>status = approved</b> ein "
            "(oder sag kurz hier im Chat Bescheid). Beim nächsten Lauf um 07:30 Uhr baut TTS_02 automatisch das Video dazu!",
            bullet_style,
        )
    )

    story.append(PageBreak())

    # 4. Deine täglichen ToDos (5-Minuten-Routine)
    story.append(Paragraph("4. Deine täglichen ToDos (Deine 5-Minuten-Routine am Handy)", h1_style))
    story.append(
        Paragraph(
            "Da die komplette Skript-, Bild-, Video-, Voiceover-, SEO- und Schnitt-Arbeit jeden Morgen zwischen "
            "07:00 und 08:35 Uhr automatisch auf dem Server läuft, beschränkt sich deine tägliche Arbeit auf "
            "<b>3 kurze Schritte (ca. 3–5 Minuten pro Tag)</b>:",
            body_style,
        )
    )

    story.append(Paragraph("ToDo 1: Morgens ab 08:35 Uhr — TikTok-Posteingang öffnen & Entwurf prüfen (1 Min.)", h2_style))
    story.append(
        Paragraph(
            "• Öffne auf deinem Handy die <b>TikTok-App (@bizpunk72)</b>.<br/>"
            "• Tippe unten auf <b>Posteingang (Inbox)</b> -> <b>Systembenachrichtigungen (System Notifications)</b>.<br/>"
            "• Dort siehst du die Meldung: <i>„Dein Video ist bereit / Video von Drittanbieter-App hochgeladen“</i>.<br/>"
            "• <b>Wichtige TikTok-Regel (Max. 5 Entwürfe pro 24h):</b> TikTok erlaubt maximal 5 unveröffentlichte API-Entwürfe "
            "innerhalb von 24 Stunden. Veröffentliche deinen täglichen Entwurf daher immer zeitnah, damit für den "
            "nächsten Morgen wieder ein freier Slot im Posteingang bereitsteht!",
            bullet_style,
        )
    )

    story.append(Paragraph("ToDo 2: Produkt-Warenkorb anhängen & SEO-Beschreibung prüfen (2 Min.)", h2_style))
    story.append(
        Paragraph(
            "• Tippe im Vorschau-Bildschirm des Videos auf <b>„Weiter“</b>, bis du auf der Veröffentlichungs-Seite bist.<br/>"
            "• Prüfe kurz die <b>SEO-Beschreibung & Hashtags</b> (wird von Zernio automatisch mitgeliefert oder kann aus "
            "<b>tts_video_queue.caption_de</b> kopiert werden).<br/>"
            "• Tippe auf <b>„+ Link hinzufügen“ -> „Produkt“</b> und wähle das im Video gezeigte Produkt aus deinem "
            "TikTok-Shop-Schaufenster aus (z. B. <i>3-in-1 Magnet-Ladestation</i> oder <i>7-in-1 Reinigungs-Set</i>).<br/>"
            "• Gib einen kurzen, klaren Button-Titel ein (max. 30 Zeichen, z. B. <b>3-in-1 Magnet-Ladestation</b>).<br/>"
            "• Kontrolliere, dass der Schalter <b>„KI-generierter Inhalt“ (AI-generated content)</b> aktiv ist (Schutz vor "
            "TikTok-Shop-Verwarnungen!).<br/>"
            "• Tippe unten rechts auf <b>„Veröffentlichen“ (Post)</b>!",
            bullet_style,
        )
    )

    story.append(Paragraph("ToDo 3: Einmal pro Woche (oder bei Bedarf) — Nachschub in tts_products prüfen (2 Min.)", h2_style))
    story.append(
        Paragraph(
            "• Schau in n8n in die Data Table <b>tts_published_posts</b> / <b>tts_video_queue</b>, welches Produkt an der Reihe war.<br/>"
            "• Stelle sicher, dass das nächste Produkt aus <b>tts_products</b> bereits in deinem TikTok-Shop-Schaufenster liegt.<br/>"
            "• Wenn ein Video besonders viele Views oder Verkäufe erzielt, kannst du in <b>tts_video_queue</b> jederzeit eine "
            "zweite Hook-Variante zum selben Gewinner-Produkt anstoßen.",
            bullet_style,
        )
    )

    # 5. Technische Referenz & Stimmen-Regeln
    story.append(Paragraph("5. Technische Kurzreferenz (Workflows, Stimmen & SEO)", h1_style))
    ref_data = [
        [
            Paragraph("Komponente", header_cell),
            Paragraph("Einstellung / Wert", header_cell),
        ],
        [
            Paragraph("<b>n8n Instanz & Ordner</b>", cell_bold),
            Paragraph("https://n8n.mafrapi.eu (Ordner: TikTok-Shop, ID: pB3FFX2Z9VBTcmuv)", cell_style),
        ],
        [
            Paragraph("<b>FFmpeg Render-Server</b>", cell_bold),
            Paragraph("https://ffmpeg.mafrapi.eu (Coolify UUID: r135f55kgojfe3ot59z49e67)", cell_style),
        ],
        [
            Paragraph("<b>GitHub Repository</b>", cell_bold),
            Paragraph("https://github.com/gitbixxs/TikTok-Shop", cell_style),
        ],
        [
            Paragraph("<b>Stimme Tech / Gadgets / Auto</b>", cell_bold),
            Paragraph("Männlich: <b>Jonas</b> (HF Chatterbox Multilingual, language_id='de', nl_m.flac, exag=0.72)", cell_style),
        ],
        [
            Paragraph("<b>Stimme Beauty / Style / Gesundheit</b>", cell_bold),
            Paragraph("Weiblich: <b>Mia</b> (HF Chatterbox Multilingual, language_id='de', sv_f.flac, exag=0.72)", cell_style),
        ],
        [
            Paragraph("<b>Video-Timing (38,0s)</b>", cell_bold),
            Paragraph("Szenen 1–7: je 4,5 Sekunden | Szene 8 (Warenkorb-CTA): ~8,5 Sekunden Standzeit", cell_style),
        ],
        [
            Paragraph("<b>Untertitel-Styling</b>", cell_bold),
            Paragraph("Kastenfrei (BorderStyle=1), DejaVu Sans Bold, 120px Rand links/rechts, Gold/Grün/Orange", cell_style),
        ],
    ]
    ref_table = Table(ref_data, colWidths=[56 * mm, 118 * mm])
    ref_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(ref_table)

    doc.build(story)
    print(f"Successfully generated PDF manual: {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == "__main__":
    out_pdf = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "BENUTZERHANDBUCH_TIKTOK_SHOP.pdf",
    )
    build_pdf(out_pdf)
