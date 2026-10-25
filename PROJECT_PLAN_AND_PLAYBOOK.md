# Projektplan & Operatives Playbook: TikTok-Shop (`@bizpunk72`) — v2.0

Dieses Dokument beschreibt den kompletten operativen Ablauf und die technische Dokumentation unseres **TikTok-Shop Affiliate Systems (`@bizpunk72`)** für den deutschen Markt (`de-DE`).

---

## 1. Live-Status von `@bizpunk72` (Freigeschaltet für TikTok Shop!)

| Metrik / Attribut | Aktueller Live-Wert | Status |
| :--- | :--- | :--- |
| **TikTok Handle / ID** | `@bizpunk72` (`7587763422331175958`) | Etablierter deutscher AI- & Tech-Account |
| **Region & Cluster** | `DE` / EU (`no1a`) | Deutscher TikTok Shop freigeschaltet |
| **Follower-Stand** | **1.607+ Follower** *(Schwelle: 1.500)* | **100 % erfüllt (+107 über dem Limit)** |
| **Auszahlungsdaten** | Verifiziert | Bereit für Affiliate-Provisionen (20–30 %) |
| **Aktiver Pipeline-Modus** | **`tiktok_shop_cart`** | Direkter Verweis auf den orangenen Warenkorb unten links |
| **Zernio Account-ID** | `6a99599b77555aae01ce4ec4` | Automatischer Creator-Inbox-Draft-Upload (`draft: true`, `is_ai_generated: true`) |
| **Hugging Face Account** | `@BizPunk` (`PRO` aktiv) | Alle KI-Schritte laufen über Hugging Face Inference (`router.huggingface.co`) |

---

## 2. Der 1:1 Szenen-Klon-Workflow (38 Sekunden Gesamtlänge)

Statt generischer Text-zu-Bild-Slideshows baut unsere Pipeline erfolgreiche virale TikTok-Shop-Videos **1:1 mit unserem eigenen Produkt** nach:

| Schritt | Komponente | Technische Umsetzung |
| :--- | :--- | :--- |
| **1. Referenz-Analyse & 8 Keyframes** | `Apify` + `FFmpeg` (`/api/ffmpeg/extract-thumbnail`) | Lädt das virale Originalvideo herunter und extrahiert 8 präzise Funktions-Keyframes ohne störende englische Text-Overlays. |
| **2. 1:1 Image-to-Image mit Produkt-Packshot** | `TTS_03` (`router.huggingface.co/fal-ai/fal-ai/flux-2/edit`) | Übergibt `image_urls: [originalSceneScreenshot, productPackshot]` + Edit-Prompt. Kamerawinkel, Handhaltung und Produktfunktion bleiben 1:1 erhalten. |
| **3. Funktions-Animation (Image-to-Video)** | `TTS_03` (`router.huggingface.co/fal-ai/fal-ai/wan-i2v`) | Animiert das 1:1 Szenenbild als Start-Frame (`image_url`) zu einem flüssigen Bewegungs-Clip. |
| **4. Deutsches KI-Voiceover (`Jonas` & `Mia`)** | `TTS_04` (`Chatterbox-Multilingual-TTS`, `language_id: "de"`) | Automatische Aufteilung in Satzblöcke `< 230 Zeichen` (kein Satzabbruch!). **Tech/Gadgets/Auto = „Jonas“ (männlich)**, **Beauty/Style/Gesundheit = „Mia“ (weiblich)**. |
| **5. 38s Schnitt, Audio-Mix & kastenfreie Schrift** | `TTS_04` (`https://ffmpeg.mafrapi.eu`) | **Szenen 1–7 je 4,5s**, **Szene 8 (Warenkorb-CTA) ~8,5s**. Mischt Sprache (100 %) + BGM (10 %) und brennt kastenfreie, mehrfarbige ASS-Untertitel (`MarginL/R=120`) ein. |
| **6. TikTok-Search-SEO & Draft-Upload** | `TTS_02` + `TTS_04` (`Zernio API`) | Generiert aus der Original-Produktbeschreibung eine SEO-optimierte Caption + `Suchbegriffe:` + Hashtag-Matrix und lädt das Video als Entwurf in die TikTok-App hoch. |

---

## 3. Unsere Stimmen-Regeln auf Hugging Face (`Jonas` & `Mia`)

| Produkt-Kategorie | Gewählte Stimme | HF Multilingual TTS Parameter |
| :--- | :--- | :--- |
| **Tech, Gadgets, Smart Home & Auto-Zubehör** | **Männlich: „Jonas“** (jung, motivierend, souverän) | `language_id: "de"`, `reference_audio: nl_m.flac`, `exaggeration: 0.72`, `cfg_weight: 0.05` |
| **Beauty, Style, Skincare & Gesundheit** | **Weiblich: „Mia“** (jung, freundlich, begeisternd) | `language_id: "de"`, `reference_audio: sv_f.flac`, `exaggeration: 0.72`, `cfg_weight: 0.05` |

---

## 4. Produzierte Videos & Fertige TikTok-SEO-Beschreibungen

### Produkt 1: **3-in-1 Magnetische Falt-Ladestation & Handyhalter** (`prod_magsafe_3in1_fold`)
- **Referenzvideo:** `@dgtltech_` (`7624069227430825229`, 157.800 Views)
- **Zernio Post-ID (in deiner TikTok Inbox):** `6adddc5f7c360fafaceea986`
- **Cloud-Video-URL:** `https://media.zernio.com/temp/1792924763686_u6ctxvwd_tiktok_shop_38s_hf_voice.mp4`
- **SEO-optimierte Beschreibung & Hashtags:**
```text
3-in-1 Magnetische Ladestation & faltbarer Handyhalter: Schluss mit Kabelsalat auf dem Schreibtisch und auf Reisen!
• 3-in-1 Wireless Fast-Charge (15W): Lädt iPhone/Smartphone, Apple Watch & AirPods gleichzeitig über nur 1 USB-C-Kabel
• Starker Magnet-Halt & 90° drehbar: Perfekter Winkel im Hochformat zum Scrollen oder im Querformat für Filme
• Nachttisch Standby-Modus: Nutze dein Smartphone nachts im Querformat direkt als digitalen Wecker
• Ultrakompakt & faltbar: Klappt in Sekunden flach auf Taschenformat zusammen – ideal für Hotel & Handgepäck
Direkt unten links im orangenen Warenkorb verlinkt – sicher dir das Original, solange der Rabatt aktiv ist!
Suchbegriffe: 3 in 1 Magnetische Ladestation, faltbarer Handyhalter, MagSafe Reiseladegerät, iPhone Watch AirPods Ladestation, kabelloses Ladegerät 3 in 1
#3in1Ladestation #MagSafeCharger #Handyhalter #KabellosLaden #ReiseGadgets #SchreibtischSetup #TechGadgets #tiktokshopde #tiktokmademebuyit #bizpunk72
```

---

### Produkt 2: **7-in-1 / 8-in-1 Pro Elektronik, Tastatur & AirPods Reinigungs-Set** (`prod_7in1_tech_cleaner`)
- **Referenzvideo:** `@luxcleantechh` (`7608202200036199702`, 43.000 Views)
- **Zernio Post-ID (in deiner TikTok Inbox):** `6ade0649901c0ff33bed94b1`
- **Cloud-Video-URL:** `https://media.zernio.com/temp/1792937475460_hdqsugv4_tiktok_shop_38s_hf_voice.mp4`
- **Lokale Master-Datei (mit Jonas' Stimme):** `output/TikTok_Shop_7in1_Cleaner_Jonas_38s_FINAL.mp4`
- **SEO-optimierte Beschreibung & Hashtags:**
```text
AirPods leise oder Tastatur voller Staub? Reinige deine AirPods, Tastatur & dein Handy-Display perfekt mit dem 7-in-1 / 8-in-1 Pro Reinigungs-Set!
• Faltbarer Dual-Head Reinigungs-Pen: Metallspitze + hochdichte Mikro-Bürste für verstopfte Kopfhörer-Lautsprechergitter
• Weiches Beflockungs-Schwämmchen: Reinigt tief im Inneren des AirPods-Ladecases & am Ladeanschluss
• Ausfahrbare Tastatur-Bürste + Keycap-Puller: Zum einfachen Entfernen von Tastaturkappen & Staub zwischen den Tasten
• Integriertes Display-Spray + Mikrofaser-Pad: Für streifenfreie Bildschirme auf Smartphone, Tablet, Laptop & Kamera
Klicke unten links auf den orangenen Warenkorb, um es dir jetzt zu sichern!
Suchbegriffe: AirPods Reinigung, Tastatur Reinigungsset, Handy Display Reiniger, 7 in 1 Elektronik Reiniger, Kopfhörer sauber machen
#AirPodsReinigung #TastaturReinigung #DisplayReinigung #ElektronikReinigung #8in1ReinigungsPen #TechReinigung #GadgetCare #tiktokshopde #tiktokmademebuyit #bizpunk72
```

---

## 5. Checkliste für das Veröffentlichen in der TikTok-App (30 Sekunden pro Video)

1. Öffne die **TikTok-App** auf deinem Handy (`@bizpunk72`).
2. Gehe auf **Posteingang (Inbox) → Systembenachrichtigungen (System Notifications)** und tippe auf *„Dein Video ist bereit“*.
   *(Wichtig: TikTok erlaubt maximal 5 offene API-Entwürfe pro 24 Stunden. Veröffentliche vorhandene Entwürfe zeitnah, damit neue Slots frei werden).*
3. Tippe im Vorschau-Editor auf **„Weiter“**.
4. Füge (falls noch nicht übernommen) die **SEO-optimierte Beschreibung** oben ein.
5. Tippe auf **„+ Link hinzufügen“ → „Produkt“** und wähle das passende Produkt aus deinem TikTok-Shop-Schaufenster aus.
6. Prüfe, dass das Flag **„KI-generierter Inhalt“ (AI-generated content)** aktiviert ist, und tippe auf **„Veröffentlichen“**!
