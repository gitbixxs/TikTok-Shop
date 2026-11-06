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

## German Voiceover Rules (Florian & Luisa)

**Edge-TTS voices run on our own Coolify endpoint** — `POST https://ffmpeg.mafrapi.eu/api/tts/edge` (`ffmpeg-service`, AI-Mate repo) executes the `edge-tts` CLI directly against Microsoft neural TTS: **no Hugging Face Space, no queue, no token, ~1s** for a full script. Chatterbox still uses HF with `Authorization: Bearer $env.HF_TOKEN` (unlocks ZeroGPU).

- **Tech, Gadgets, Smart Home & Car Accessories → Male Voice "Florian" (Tier 1):** own endpoint, body `{text, voice: "de-DE-FlorianMultilingualNeural"}` → returns `{voice_url}` MP3 under `/temp/`. The public HF mirrors (`innoai`/`cpuai`) were abandoned — saturated queues produced `no-audio` on every attempt; the private `BizPunk/Edge-TTS-Prod` space 404s without token repo access.
- **Beauty, Style, Skincare & Health → Female Voice "Luisa" (Tier 1, real voice clone):** `ResembleAI/Chatterbox-Multilingual-TTS`, `language_id: "de"`, `exaggeration: 0.72`, `temperature: 0.8`, `cfg_weight: 0.05`, chunked `< 250` chars. Reference MP3 (`https://files.catbox.moe/b76w25.mp3`) is fetched by the `Fetch Luisa Ref MP3` HTTP node and uploaded by the `Upload Luisa Ref To HF` HTTP node via `POST /gradio_api/upload` (multipart `formBinaryData`, field `files`) → returns a server-side `/tmp/gradio/...` path, which the code node passes as `FileData {path, url, orig_name, mime_type, meta:{_type:"gradio.FileData"}}` to `generate_tts_audio`. Remote URLs/data-URIs in FileData are NOT accepted — the file must exist server-side.
- **Fallbacks (female):** Edge-TTS `de-AT-IngridNeural` (pitch `+5Hz`) via own endpoint → Chatterbox built-in `sv_f`. **Fallback (male):** Chatterbox built-in `nl_m` via `on_language_change`.
- `tts_provider_used` reports `ffmpeg-edge-tts-de:florian|ingrid_at+5hz`, `hf-chatterbox-clone-luisa-de`, or `hf-chatterbox-multilingual-de:nl_m|sv_f`; `tts_debug` logs per-tier failures.
- All `fetch`/`upload` helper HTTP nodes run `executeOnce` + `retryOnFail` + `onError: continueRegularOutput` so per-item fan-out and transient failures can never crash the runner.

**Hard guard:** If every tier fails, `TTS_04` throws and aborts the render — a silent music-only video must never reach Zernio/TikTok.

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
  - `TTS_01_Product_And_Outlier_Radar` (`LS7wyhnaGW8nDfZl`) — Daily 07:00 Account Radar + Sunday 06:30 **two-stage radar per spec** (`international bewiesen → DE verfügbar`): Stage 1 `Apify US Bestseller Search (country=US)` scrapes **3 batches à 10 EN keywords à 10 products** (max coverage via `devcake/tiktok-shop-data-scraper`; category-URL browse was tested and rejected — thin unsorted yield) → `Score US Winners & Build DE Match Query` (top 8 by sold_count + impulse-price band; derives concrete **brand+type DE queries** like `ugreen halterung` via EN→DE map + EN `enKw` per winner) → **`Build Outlier Video Queries` → `Apify US Outlier Video Scrape (clockworks)`** (`clockworks/tiktok-scraper`, `searchSection=/video`, `MOST_LIKED`, **one input item containing at most 8 unique searchQueries**, 2 videos per query, `executeOnce=true`, no node retries, downloads to `bizpunk72-ref-videos`, US proxy) → `Map Outlier Videos To Winners` (**exact searchQuery association**, caption evidence, >=150,000 views, downloaded MP4 required; no pairedItem/brand fallback) → `Build Reference URL Requests` → `Resolve Public Reference URLs` (existing Apify credential, keys endpoint) → `Attach Public Reference URLs` (**signed recordPublicUrl required**, no API token in stored URLs) → Stage 2 `Apify DE Match Search (country=DE)` finds the matching DE listings → `Map` scores DE results (`sold_count`, €8–35 band, packshot; existing `product_id`s/`product_key`s excluded; `problem_solved` = category phrase, `key_specs` = real description; **HARD RULE: candidates without a matched reference video are dropped entirely**) → **up to 5** results → `Verify DE Product And Reference Compatibility` (HF Qwen checks DE title/specs, US title and actual video caption; ambiguous or incompatible demonstrations are rejected; inference/JSON errors stop the workflow) → `status = candidate` + `Insert Outlier Reference Into tts_outlier_videos` (`source_url` = downloaded mp4, `matched_product_key`, `hook_text` = video caption, `transcript_raw` = subtitles — the real 1:1 clone reference!) + Telegram 1-Click Approval showing US sales proof + DE PDP link/packshot. **Catalog hygiene:** `If` router sends `stale_pause` items to `Auto-Pause Stale Candidates` (candidates >14 d without approval → `paused`).
  - `TTS_02_Script_And_Scene_Architect` (`YytySstcIa4ifAlQ`) — **3x täglich (07:30 / 13:00 / 19:00)** Script & SEO Architect with **"Test & Double-Down" Rule** (3–5 test videos per approved product with rotating hooks, auto-pause losers `< 1,000` views & `0` orders after 4 videos, unlimited scaling for `status = winner` or `>= 5,000` views / `>= 1` order) + Daily Telegram Briefing Card. **HARD GATE:** a queue row is only created when a real reference video exists (`matchedOutlier.source_video_stream_url` | `.mp4`-like `source_url` | `refStreamByProduct`) — no free-invented videos. `problemShort` never puts the product title into the problem slot (title-overlap guard + category fallbacks); the Qwen script call adapts `matchedOutlier.hook_text`/`transcript_raw` and must never frame OUR product as the annoyance.
  - `TTS_03_Visual_And_Clip_Factory` (`aLRjC7ZZ4MhqARJw`) — **3x täglich (08:00 / 13:30 / 19:30)** **Reference-conditioned product editing** via `flux-2/edit` (HF Router): per scene a reference-video frame (`extract-thumbnail` @ `ref_timestamp`) and the DE packshot are passed to the model with instructions to preserve the person, hands, pose, background, lighting and camera angle while replacing the product. This is a generative edit, NOT a guarantee of pixel-identical preservation or artifact-free anatomy; visual comparison is still required before claiming a faithful clone. Fallback: packshot-anchored i2i edit → `flux/schnell` t2i → `wan-i2v` motion clip. **QUALITY GATE:** `render_status = blocked_no_reference` (never `ready_for_ffmpeg`) when zero scenes had a real reference frame — invented-only videos cannot ship.
  - `TTS_04_FFmpeg_Render_And_Zernio` (`19n3oP2Q1wlT1Djc`) — **3x täglich (08:30 / 14:00 / 20:00)** German Voiceover (`Florian` via own edge-tts endpoint / `Luisa` Chatterbox clone), 38s FFmpeg Render, Box-Free ASS Subtitles & Zernio Draft Upload
- **Output target:** 3 Videos pro Tag (morgens, mittags, abends), subject to candidate approvals and quality gates. No output is expected when no valid product/reference match exists. Creator Inbox drafts only; no automatic publication.

## Verification and Known Gaps (2026-11-06)

- Run `node scripts/test_radar_guards.cjs` for offline JS syntax, batch cardinality/dedupe/caps, DE keyword derivation, video evidence/view/URL gates, signed URL resolution, compatibility response validation, item linking and approved/winner filtering. Uses fixtures; no external API calls.
- Execution `14032` was canceled after ~35 minutes. Apify history shows 64 sequential video runs, including identical queries at positions 1 and 9. The workflow graph has no cycle; the precise runtime cause of the repeated eight-query list is not established. The multi-item video boundary was replaced with one bounded batch rather than attributing the duration to slow downloads.
- Execution `14033`: success in ~121 seconds, exactly one video batch run, five inserts/cards. Those five matches were incompatible (e.g. cleaning brush -> ceiling light) and product rows **81–85 were paused** by execution `14034`; do not approve their old Telegram cards.
- Execution `14035`: success in ~100 seconds. Signed URL lookup succeeded, and both resolved MP4 URLs returned HTTP 200/video/mp4 without an API token. The compatibility gate rejected all proposed products; **zero new candidates** is the correct result for this run, not an end-to-end video success.
- Radar saves node progress (`saveExecutionProgress=true`) so running/failed executions can be inspected without guessing the active scraper.
- TTS_02 `Load Products` now loads only `approved`/`winner` rows, preventing its legacy fallback selector from processing `candidate`/`paused` products. The fallback inside the selector still needs review for exhausted approved-product test quotas.
- **Coverage gap:** three keyword batches are configured, but the US bestseller node still has `executeOnce=true`; recent runs show only one US actor run. Do not claim all 30 keywords were executed until this is corrected and verified.
- **Reference analysis gap:** scraped captions are not spoken transcripts. Current runs had empty transcripts; subtitle download/ASR and actual scene-boundary analysis remain unverified. Fixed scene timestamps can exceed short reference durations.
- **Visual gate gap:** TTS_03 currently checks whether ANY frame was extracted, not whether EVERY scene was successfully product-edited. Packshot/t2i fallback branches and last-row fallback selection remain. This is insufficient to certify a faithful clone.
- **Open user requirement:** complete TTS_02 -> TTS_03 -> TTS_04 test with ONE genuinely matched product, then inspect German narration, person/composition preservation, product identity and anatomy. Blocked until a compatible candidate exists; do not manufacture approval or call a reference-less output a clone.
