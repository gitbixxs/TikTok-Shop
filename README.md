# TikTok-Shop Automation Pipeline (`@bizpunk72`) — v2.0

Vollautomatisierte **1:1 TikTok Shop Affiliate Video-Klon- & Voiceover-Pipeline** auf Basis von **n8n**, **n8n Data Tables / Baserow**, **Apify**, **100 % Hugging Face Inference (`router.huggingface.co` + HF Multilingual TTS Spaces)**, deinem **FFmpeg-Microservice (`https://ffmpeg.mafrapi.eu`)** und der **Zernio TikTok Draft API**.

Das System setzt den **1:1 Szenen-Klon-Workflow** (Screenshot-Extraktion aus viralen TikTok-Shop-Referenzvideos → Multi-Image-Edit mit Produkt-Packshot via `flux-2/edit` → Image-to-Video Animation via `wan-i2v` → natürliches deutsches KI-Voiceover mit **Jonas** & **Mia** → kastenfreie mehrfarbige ASS-Untertitel → automatische TikTok-Search-SEO-Beschreibung aus den Original-Produktdaten) komplett serverseitig um.

---

## 1. Systemarchitektur (v2.0 — 100 % Hugging Face Inference)

```mermaid
flowchart LR
    A[Apify TikTok Outlier Scraper] --> B[TTS_01 Product & Outlier Radar]
    B --> C[(tts_products & tts_outlier_videos)]
    C --> D[TTS_02 Script, 8-Scene & SEO Architect]
    D -->|HF Qwen2.5-72B SEO Caption + 8 Keyframes| E[(tts_video_queue)]
    E --> F[TTS_03 1:1 Visual & Clip Factory]
    F -->|HF flux-2/edit + HF wan-i2v| G[8x 1:1 Produkt-Szenen & Video-Clips]
    G --> H[TTS_04 38s FFmpeg Render, HF TTS & Zernio]
    H -->|HF Chatterbox DE: Jonas / Mia| I[https://ffmpeg.mafrapi.eu]
    I -->|38s MP4 + 100% Voice + 10% BGM + ASS Subs| J[Zernio TikTok Draft API]
    J --> K[@bizpunk72 Creator Inbox + Warenkorb-Link]
```

---

## 2. Kern-Features (v2.0)

1. **Echter 1:1 Szenen-Nachbau mit deinem Produkt (`TTS_02` & `TTS_03`):**
   - Extrahiert automatisch **8 präzise Funktions-Keyframes** aus dem viralen Original-TikTok-Video (`/api/ffmpeg/extract-thumbnail`).
   - Übergibt pro Szene **`Bild 1` (Original-Szenen-Screenshot)** + **`Bild 2` (echter Produkt-Packshot)** an **Hugging Face Inference (`router.huggingface.co/fal-ai/fal-ai/flux-2/edit`)**, sodass Kamerawinkel, Handhaltung und alle Produktfunktionen 1:1 erhalten bleiben.
   - Animiert Schlüsselszenen über **Hugging Face Image-to-Video (`router.huggingface.co/fal-ai/fal-ai/wan-i2v`)**.
2. **Optimiertes 38-Sekunden-Timing & 8,5s Warenkorb-CTA:**
   - **Szenen 1–7:** Je **4,5 Sekunden** Standzeit für entspannte Lesbarkeit.
   - **Szene 8 (Warenkorb-CTA am Ende):** **~8,5 Sekunden** Standzeit für den Verweis auf den orangenen TikTok-Shop-Warenkorb unten links.
3. **Natürliches deutsches KI-Voiceover auf Hugging Face (`Jonas` & `Mia`):**
   - Nutzt `Chatterbox-Multilingual-TTS` (`language_id: "de"`) mit automatischem Satz-Splitting (`< 230 Zeichen` pro Aufruf, damit kein Satz abgeschnitten wird):
     - **Tech, Gadgets, Smart Home & Auto:** Männliche deutsche Stimme **„Jonas“** (`nl_m.flac`, `exaggeration: 0.72`, `cfg_weight: 0.05`).
     - **Beauty, Style, Skincare & Gesundheit:** Weibliche deutsche Stimme **„Mia“** (`sv_f.flac`, `exaggeration: 0.72`, `cfg_weight: 0.05`).
   - Audio-Mix über `/api/ffmpeg/scale-9x16` + `/api/ffmpeg/mix-audio-video`: **100 % Sprachlautstärke** im Vordergrund + **10 % Hintergrundmusik**.
4. **Kastenfreie, mehrfarbige fette Schrift (`/api/ffmpeg/add-subtitles`):**
   - `BorderStyle=1` (keine Hintergrundboxen), fette `DejaVu Sans` mit 6–8px schwarzer Kontur, `MarginL=120` / `MarginR=120` (kein Abschneiden am Rand) und Farbcodierung nach Rolle:
     - **Hook:** Goldgelb (`#FFD700`) + Weiß
     - **Produkt-Features:** Smaragdgrün (`#00FF66`) + Hellgrün
     - **Warenkorb-CTA:** TikTok-Shop-Orange (`#FF8800`) + Goldgelb
5. **Automatische TikTok-Search-SEO-Beschreibung & Hashtag-Matrix (`TTS_02`):**
   - Generiert aus der Original-Produktbeschreibung via Hugging Face LLM (`Qwen/Qwen2.5-72B-Instruct`) automatisch:
     - Search-Hook in Zeile 1 (erste 60 Zeichen)
     - 4 Feature-Bulletpoints (`•`) aus den Original-Specs
     - Warenkorb-CTA + `Suchbegriffe:`-Zeile (Long-Tail-Keywords) + 10er Hashtag-Matrix (`#tiktokshopde #tiktokmademebuyit #bizpunk72`).

---

## 3. Projektstruktur

```text
TikTok-Shop/
├── AGENTS.md                                  # Projekt-Regeln, Account-IDs, Stimmen- & SEO-Vorgaben
├── README.md                                  # Systemarchitektur, Features & Schnellstart
├── PROJECT_PLAN_AND_PLAYBOOK.md               # Operatives Playbook, 1:1 Klon-Ablauf & SEO-Vorlagen
├── .env.example                               # Template für lokale Umgebungsvariablen
├── .gitignore                                 # Schützt Secrets (.env) & große lokale Render-Dateien
├── config/
│   ├── niches_and_categories_de.json          # Produkt-Nischen & Seed-Produkte (Tech, Auto, Smart Home, Beauty)
│   ├── avatar_personas.json                   # Stimmen-Regeln (Jonas & Mia) & deutsche Avatar-Personas
│   └── prompt_templates.json                  # Prompts für 1:1 Szenen-Cloning & TikTok-Search-SEO
├── baserow_setup/
│   ├── tiktok_shop_baserow_schema.json        # Vollständiges Tabellen-Schema (5 Tabellen)
│   └── setup_baserow.ps1                      # PowerShell-Provisionierungsskript für Baserow
├── scripts/
│   ├── check_account_status.py                # Prüft live @bizpunk72 Follower-Stand & Shop-Status
│   ├── analyze_reference_video.py             # Analysiert ein TikTok/YouTube-Referenzvideo (Metadaten & Szenen)
│   └── test_render_pipeline.py                # Prüft Erreichbarkeit & Endpunkte auf https://ffmpeg.mafrapi.eu
└── n8n_workflows/
    ├── TTS_01_Product_And_Outlier_Radar.json  # Produkt- & Outlier-Video-Discovery (Live-ID: 3qVjo7qjfxxMGvdK)
    ├── TTS_02_Script_And_Scene_Architect.json # 8-Szenen-Architekt & HF SEO-Caption-Generator (Live-ID: aVcsOiTDQw0XPInh)
    ├── TTS_03_Visual_And_Clip_Factory.json    # HF Image-to-Image (flux-2/edit) & I2V (wan-i2v) (Live-ID: aLRjC7ZZ4MhqARJw)
    └── TTS_04_FFmpeg_Render_And_Zernio.json   # HF Voiceover (Jonas/Mia), 38s FFmpeg Render & Zernio Upload (Live-ID: 19n3oP2Q1wlT1Djc)
```

---

## 4. Schnellstart & Live-Kommandos

### 1. Live-Status von `@bizpunk72` prüfen
```bash
python scripts/check_account_status.py
```

### 2. Referenzvideo lokal analysieren
```bash
python scripts/analyze_reference_video.py --url "https://www.tiktok.com/@dgtltech_/video/7624069227430825229"
```

### 3. FFmpeg-Render-Service (`https://ffmpeg.mafrapi.eu`) testen
```bash
python scripts/test_render_pipeline.py
```
