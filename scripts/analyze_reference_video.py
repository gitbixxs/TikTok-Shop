#!/usr/bin/env python3
"""
Reference Video Analyzer for the TikTok-Shop US-to-DE Outlier Cloning Pipeline.
Extracts metadata, captions/transcript (if available on YouTube/TikTok), and generates
a 6-scene breakdown template ready for TTS_02_Script_And_Scene_Architect.
"""
import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")


def extract_youtube_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else ""


def analyze_youtube(video_id: str) -> dict:
    body = json.dumps(
        {
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "20.10.38",
                    "androidSdkVersion": 30,
                    "hl": "de",
                    "gl": "DE",
                }
            },
            "videoId": video_id,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://www.youtube.com/youtubei/v1/player",
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip",
        },
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    details = resp.get("videoDetails", {})
    tracks = (
        resp.get("captions", {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks", [])
    )
    transcript_lines = []
    if tracks:
        xml_data = (
            urllib.request.urlopen(
                urllib.request.Request(
                    tracks[0]["baseUrl"],
                    headers={
                        "User-Agent": "com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip"
                    },
                ),
                timeout=20,
            )
            .read()
            .decode("utf-8", errors="ignore")
        )
        root = ET.fromstring(xml_data)
        for p in root.findall(".//p"):
            txt = "".join(p.itertext()).strip()
            if txt:
                transcript_lines.append(txt)

    full_transcript = " ".join(transcript_lines)
    return {
        "platform": "youtube",
        "video_id": video_id,
        "title": details.get("title", ""),
        "author": details.get("author", ""),
        "duration_sec": int(details.get("lengthSeconds", 0)),
        "views": int(details.get("viewCount", 0)),
        "transcript_raw": full_transcript[:4000],
        "recommended_scene_template": [
            {"scene_no": 1, "role": "hook", "duration_sec": 3.5},
            {"scene_no": 2, "role": "flop_1", "duration_sec": 3.0},
            {"scene_no": 3, "role": "flop_2", "duration_sec": 3.0},
            {"scene_no": 4, "role": "flop_3", "duration_sec": 3.0},
            {"scene_no": 5, "role": "hero_reveal", "duration_sec": 6.5},
            {"scene_no": 6, "role": "cta", "duration_sec": 4.0},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a viral reference video.")
    parser.add_argument("--url", required=True, help="YouTube or TikTok video URL")
    args = parser.parse_args()

    yt_id = extract_youtube_id(args.url)
    if yt_id:
        res = analyze_youtube(yt_id)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(
            json.dumps(
                {
                    "platform": "tiktok",
                    "source_url": args.url,
                    "note": "Use TTS_01_Product_And_Outlier_Radar (Apify) or pass transcript to TTS_02.",
                    "recommended_scene_template": [
                        {"scene_no": 1, "role": "hook", "duration_sec": 3.5},
                        {"scene_no": 2, "role": "flop_1", "duration_sec": 3.0},
                        {"scene_no": 3, "role": "flop_2", "duration_sec": 3.0},
                        {"scene_no": 4, "role": "flop_3", "duration_sec": 3.0},
                        {"scene_no": 5, "role": "hero_reveal", "duration_sec": 6.5},
                        {"scene_no": 6, "role": "cta", "duration_sec": 4.0},
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
