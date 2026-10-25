#!/usr/bin/env python3
"""
Health & Connectivity Check for the Coolify FFmpeg Microservice (https://ffmpeg.mafrapi.eu).
Verifies that the render endpoints required by TTS_04_FFmpeg_Render_And_Zernio are reachable.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")


def check_ffmpeg_service(base_url: str) -> dict:
    base = base_url.rstrip("/")
    endpoints = [
        "/api/ffmpeg/slideshow",
        "/api/ffmpeg/create-reel",
        "/api/ffmpeg/combine-avatar",
        "/api/ffmpeg/mix-music",
    ]
    results = {}
    for ep in endpoints:
        url = base + ep
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                results[ep] = {"status": resp.status, "reachable": True}
        except urllib.error.HTTPError as e:
            # HTTP 400 ("Missing required inputs") proves the Express route is live and responding
            results[ep] = {
                "status": e.code,
                "reachable": e.code in (200, 400, 422),
                "response": e.read().decode("utf-8", errors="ignore")[:120],
            }
        except Exception as e:
            results[ep] = {"status": None, "reachable": False, "error": str(e)}

    return {
        "ffmpeg_base_url": base,
        "all_endpoints_online": all(v.get("reachable") for v in results.values()),
        "endpoints": results,
    }


if __name__ == "__main__":
    url = os.environ.get("FFMPEG_BASE_URL", "https://ffmpeg.mafrapi.eu")
    report = check_ffmpeg_service(url)
    print(json.dumps(report, indent=2, ensure_ascii=False))
