# TikTok-Shop Agent Rules (`@bizpunk72`)

## Mission & Project Scope

- **Project:** `TikTok-Shop` (`C:\Users\Administrator\Documents\GitHub\TikTok-Shop`)
- **Goal:** Automated faceless TikTok Shop Affiliate pipeline for the German market (`de-DE`), starting with **Tech Gadgets, AI Hardware, Smart Home, Car Accessories, and Everyday Problem Solvers** tailored to `@bizpunk72`'s existing audience, with modular expansion to **Beauty/Skincare** in Phase 2.
- **Core Methodology ("US/UK Outlier Clone -> DE TikTok Shop"):**
  1. Discover high-velocity TikTok Shop products (`tts_products`) and viral outlier videos (`>= 150,000` views, `tts_outlier_videos`).
  2. Adapt viral English/German scripts into the proven **"3 Flops / Expensive Alternatives vs. 1 Hero Product"** framework localized for German retail settings (MediaMarkt/Saturn aisle, Home-Office desk, car cockpit, dm store).
  3. Generate consistent AI Avatar + Product Packshot scene images and lip-synced/motion video clips via API (`fal.ai` / Hugging Face Router / Replicate).
  4. Render 9:16 vertical MP4s with hard cuts, karaoke subtitles, and background music via `https://ffmpeg.mafrapi.eu`.
  5. Upload directly to the TikTok Creator Inbox as a draft (`draft: true`, `postCreateTiktokOptionIsAiGenerated: true`) via Zernio (`accountId: 6a99599b77555aae01ce4ec4`), ready for 1-click TikTok Shop product cart linking inside the TikTok mobile app.

## Target TikTok Account (`@bizpunk72`)

- **Handle:** `@bizpunk72` (`BizPunk72`)
- **TikTok User ID:** `7587763422331175958`
- **Zernio Account ID:** `6a99599b77555aae01ce4ec4`
- **Region / Cluster:** `de` (`no1a` / `tiktokcdn-eu.com`)
- **Baseline Followers (2026-10-24):** `1,607` (1,500 TikTok Shop Creator threshold & payout verification completed!)
- **Active Mode:** `tiktok_shop_cart`
- **Check Command:** Run `python scripts/check_account_status.py` at any time to verify live follower count and status.

## Hugging Face Voiceover Rules (Florian & Seraphina)

All German voiceovers are generated via Hugging Face. **Tier 1 (Standard):** `innoai/Edge-TTS-Text-to-Speech` / `cpuai/Edge-TTS-Text-to-Speech` (CPU-based, no GPU quota, ~9s per full script, `rate: 6`, `pitch: 0`):
- **Tech, Gadgets, Smart Home & Car Accessories → Male Voice "Florian":** `de-DE-FlorianMultilingualNeural - de-DE (Male)`
- **Beauty, Style, Skincare & Health → Female Voice "Seraphina":** `de-DE-SeraphinaMultilingualNeural - de-DE (Female)`

**Tier 2 (Fallback):** `ResembleAI/Chatterbox-Multilingual-TTS` voice clones (`language_id: "de"`, reference `nl_m.flac` male / `sv_f.flac` female, `exaggeration: 0.72`, `cfg_weight: 0.05`, chunked `< 250` chars per call, strictly capped at ~18s per chunk so Gradio queue stalls never block the render).

**Hard guard:** If both tiers fail, `TTS_04` throws and aborts the render — a silent music-only video must never reach Zernio/TikTok.

## TikTok Search SEO Caption & Hashtag Rules (from Original Product Description)

Every video description (`caption_de`) is automatically generated via Hugging Face Inference (`Qwen/Qwen2.5-72B-Instruct` on `router.huggingface.co/v1/chat/completions`) directly from the **original product title, specifications, and reference video description**:
1. **Line 1 (Search-Hook within first 60 chars):** Primary German search keyword + core problem solved.
2. **Feature Bullet Block (`•`):** 4 concrete technical specs & functions extracted from the original product description.
3. **Cart CTA Line:** Direct pointer to the orange TikTok Shop cart at the bottom left.
4. **TikTok Search Keywords Line (`Suchbegriffe:`):** 4–5 comma-separated German long-tail search queries so TikTok indexes the video for high-intent shoppers.
5. **3-Tier Hashtag Matrix (8–10 tags):** 3 exact product tags + 3 problem/use-case tags + 2 TikTok Shop buyer tags (`#tiktokshopde #tiktokmademebuyit`) + `#bizpunk72`.

## Hard Constraints & Compliance

1. **Mandatory AI Content Disclosure:** Every TikTok draft uploaded via Zernio must include `isAiGenerated: true` / `postCreateTiktokOptionIsAiGenerated: true` to prevent TikTok Shop Creator violation points.
2. **Creator Inbox Draft Mode:** Always submit TikTok Shop videos with `draft: true` so the operator can attach the native TikTok Shop orange product cart link and trending commercial audio inside the TikTok app before publishing.
3. **No Medical / Unverifiable Cure Claims:** In scripts (especially for Beauty/Supplements in Phase 2), use personal/experiential phrasing (*"Nach 2 Wochen wirkt meine Haut..."*, *"Hat mein Kabelchaos sofort gelöst"*) rather than prohibited medical healing guarantees.
4. **Secrets Policy:** Never commit API keys, tokens, or passwords to git. Use `.env` locally and stored credentials inside n8n.
5. **Isolation from Legacy/Parallel Systems:** Do not re-activate decommissioned `EmotionPosts` workflows and do not modify active `SignalForge` (`KalonForge`) workflows.

## Live n8n & Data Infrastructure

- **FFmpeg Render Service:** `https://ffmpeg.mafrapi.eu` (Coolify UUID `r135f55kgojfe3ot59z49e67`, project `Anwendungen`)
- **n8n Folder:** `TikTok-Shop`
- **n8n Data Tables & Baserow Sync:**
  - `tts_products` — Winning TikTok Shop product catalog
  - `tts_outlier_videos` — Viral reference videos & scene breakdowns
  - `tts_avatars` — Master AI avatar personas & German retail backgrounds
  - `tts_video_queue` — Adapted German scripts, scene prompts, generated clips & render status
  - `tts_published_posts` — Zernio draft uploads, published TikTok URLs & GMV/order tracking
- **Workflows:**
  - `TTS_01_Product_And_Outlier_Radar` (`LS7wyhnaGW8nDfZl`) — Daily 07:00 Account Radar + Sunday 06:30 Weekly Apify 5-Trend Candidate Discovery (`status = candidate`) + Telegram 1-Click Inline Approval Callback (`✅ Freigeben`, `🏆 Winner`, `⏸️ Pausieren`)
  - `TTS_02_Script_And_Scene_Architect` (`YytySstcIa4ifAlQ`) — **3x täglich (07:30 / 13:00 / 19:00)** Script & SEO Architect with **"Test & Double-Down" Rule** (3–5 test videos per approved product with rotating hooks, auto-pause losers `< 1,000` views & `0` orders after 4 videos, unlimited scaling for `status = winner` or `>= 5,000` views / `>= 1` order) + Daily Telegram Briefing Card
  - `TTS_03_Visual_And_Clip_Factory` (`aLRjC7ZZ4MhqARJw`) — **3x täglich (08:00 / 13:30 / 19:30)** 1:1 Image-to-Image (`flux-2/edit`) + Image-to-Video (`wan-i2v`) via Hugging Face Inference
  - `TTS_04_FFmpeg_Render_And_Zernio` (`19n3oP2Q1wlT1Djc`) — **3x täglich (08:30 / 14:00 / 20:00)** HF German Voiceover (`Jonas` / `Mia`), 38s FFmpeg Render, Box-Free ASS Subtitles & Zernio Draft Upload
- **Output:** 3 Videos pro Tag (morgens, mittags, abends) — ca. 08:35, 14:05 und 20:05 Uhr im TikTok-Posteingang. Achtung: TikTok erlaubt max. 5 offene API-Drafts pro 24h — täglich veröffentlichen!
