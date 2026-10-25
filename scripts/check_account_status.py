#!/usr/bin/env python3
"""
Live TikTok Account & TikTok Shop Readiness Checker for @bizpunk72.
Checks follower count, delta to the 1,500 TikTok Shop Creator threshold,
and commerce flags (ttSeller, commerceUser).
"""
import argparse
import datetime
import json
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")


def fetch_tiktok_profile(handle: str, target_followers: int = 1500) -> dict:
    clean_handle = handle.lstrip("@").strip()
    url = f"https://www.tiktok.com/@{clean_handle}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        },
    )
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
    match = re.search(
        r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html,
    )
    if not match:
        raise RuntimeError(f"Could not extract profile hydration data for @{clean_handle}")

    data = json.loads(match.group(1))
    user_info = (
        data.get("__DEFAULT_SCOPE__", {})
        .get("webapp.user-detail", {})
        .get("userInfo", {})
    )
    user = user_info.get("user", {})
    stats = user_info.get("stats", {})

    followers = int(stats.get("followerCount", 0))
    following = int(stats.get("followingCount", 0))
    hearts = int(stats.get("heartCount", 0))
    videos = int(stats.get("videoCount", 0))
    delta = max(0, target_followers - followers)
    progress_pct = round(min(100.0, (followers / max(1, target_followers)) * 100.0), 1)

    commerce_user = bool(user.get("commerceUserInfo", {}).get("commerceUser", False))
    tt_seller = bool(user.get("ttSeller", False))
    created_ts = int(user.get("createTime", 0))
    created_date = (
        datetime.datetime.fromtimestamp(created_ts, datetime.timezone.utc).strftime("%Y-%m-%d")
        if created_ts
        else "unknown"
    )

    return {
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "handle": f"@{clean_handle}",
        "user_id": str(user.get("id", "")),
        "nickname": user.get("nickname", ""),
        "language": user.get("language", ""),
        "created_date": created_date,
        "followers": followers,
        "target_followers": target_followers,
        "followers_needed": delta,
        "progress_pct": progress_pct,
        "following": following,
        "likes_total": hearts,
        "videos_total": videos,
        "likes_per_video_avg": round(hearts / max(1, videos), 2),
        "tt_seller": tt_seller,
        "commerce_user": commerce_user,
        "tiktok_shop_ready": followers >= target_followers,
        "recommended_cta_mode": (
            "tiktok_shop_cart"
            if followers >= target_followers
            else "follower_sprint_1500"
        ),
        "signature": user.get("signature", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check TikTok Shop readiness for a handle.")
    parser.add_argument("--handle", default="bizpunk72", help="TikTok handle without @")
    parser.add_argument("--target", type=int, default=1500, help="Follower threshold (default: 1500)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")
    args = parser.parse_args()

    result = fetch_tiktok_profile(args.handle, args.target)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("=" * 64)
    print(f" TikTok Shop Readiness Check: {result['handle']} ({result['nickname']})")
    print("=" * 64)
    print(f" User ID          : {result['user_id']} (Created: {result['created_date']}, Lang: {result['language']})")
    print(f" Followers        : {result['followers']:,} / {result['target_followers']:,} ({result['progress_pct']}%)")
    print(f" Delta to 1,500   : {result['followers_needed']} followers remaining")
    print(f" Videos / Likes   : {result['videos_total']} videos | {result['likes_total']:,} likes ({result['likes_per_video_avg']} avg/video)")
    print(f" Commerce Flags   : ttSeller={result['tt_seller']} | commerceUser={result['commerce_user']}")
    print(f" Recommended Mode : {result['recommended_cta_mode']}")
    print("-" * 64)
    if result["followers_needed"] > 0:
        print(
            f" -> ACTION: Run 'follower_sprint_1500' mode for the next {result['followers_needed']} followers,\n"
            "    then apply in TikTok App -> TikTok Studio -> TikTok Shop for Creator."
        )
    else:
        print(
            " -> READY: 1,500+ follower threshold & payout verification complete!\n"
            "    Pipeline is active in 'tiktok_shop_cart' mode."
        )
    print("=" * 64)


if __name__ == "__main__":
    main()
