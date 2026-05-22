import os
import time
import requests
from datetime import datetime, timedelta

ITUNES_BASE = "https://itunes.apple.com/search"

FEEDS = [
    {"url": "https://rss.marketingtools.apple.com/api/v2/us/music/most-played/50/songs.json", "label": "🇺🇸 US"},
    {"url": "https://rss.marketingtools.apple.com/api/v2/gb/music/most-played/50/songs.json", "label": "🇬🇧 UK"},
]

UK_GENRE_IDS = {"15", "18"}  # R&B/Soul=15, Hip-Hop/Rap=18
ONE_YEAR_AGO = datetime.now() - timedelta(days=365)
MAX_PER_ARTIST = 2


def fetch_feed(feed):
    for attempt in range(3):
        try:
            r = requests.get(feed["url"], timeout=15)
            r.raise_for_status()
            results = r.json().get("feed", {}).get("results", [])
            break
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  取得失敗 ({feed['label']}): {e}")
                return []

    tracks = []
    for item in results:
        genre_ids = {g.get("genreId") for g in item.get("genres", [])}
        if not genre_ids & UK_GENRE_IDS:
            continue
        release_str = item.get("releaseDate", "")
        try:
            release_date = datetime.strptime(release_str, "%Y-%m-%d")
        except ValueError:
            continue
        if release_date < ONE_YEAR_AGO:
            continue
        tracks.append({
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "artist": item.get("artistName", ""),
            "label": feed["label"],
            "release_date": release_date.strftime("%Y-%m-%d"),
            "apple_music_url": item.get("url", ""),
            "artwork_url": item.get("artworkUrl100", "").replace("100x100bb", "300x300bb"),
        })
    return tracks


def collect_tracks():
    seen = {}
    for feed in FEEDS:
        print(f"取得中: {feed['label']}")
        tracks = fetch_feed(feed)
        print(f"  → {len(tracks)} 曲（過去1年以内・Hip-Hop/R&B）")
        for t in tracks:
            tid = t["id"]
            if tid in seen:
                seen[tid]["label"] += f" / {t['label']}"
            else:
                seen[tid] = t

    artist_count = {}
    result = []
    for t in seen.values():
        k = t["artist"].lower()
        if artist_count.get(k, 0) < MAX_PER_ARTIST:
            artist_count[k] = artist_count.get(k, 0) + 1
            result.append(t)

    return result


def render_html(tracks):
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    cards = ""
    for t in tracks:
        artwork = t.get("artwork_url") or "https://placehold.co/300x300/1a1a1a/888?text=No+Image"
        apple_btn = (
            f'<a href="{t["apple_music_url"]}" target="_blank" class="btn">Apple Musicで聴く ♫</a>'
            if t.get("apple_music_url")
            else '<span class="no-link">リンクなし</span>'
        )
        cards += f"""
    <div class="card">
      <img src="{artwork}" alt="" loading="lazy">
      <div class="info">
        <div class="song">{t['name']}</div>
        <div class="artist">{t['artist']}</div>
        <div class="tag">{t['label']}</div>
        <div class="release">リリース: {t.get('release_date', '不明')}</div>
        {apple_btn}
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>今週のヒップホップ・R&amp;B・ソウル</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
      background: #0f0f0f;
      color: #fff;
      padding: 16px;
      max-width: 640px;
      margin: 0 auto;
    }}
    h1 {{ font-size: 1.15rem; font-weight: 700; margin-bottom: 4px; }}
    .updated {{ font-size: 0.72rem; color: #777; margin-bottom: 18px; }}
    .card {{
      display: flex;
      gap: 12px;
      background: #1c1c1e;
      border-radius: 14px;
      padding: 12px;
      margin-bottom: 10px;
    }}
    .card img {{
      width: 88px;
      height: 88px;
      border-radius: 8px;
      object-fit: cover;
      flex-shrink: 0;
      background: #333;
    }}
    .info {{ display: flex; flex-direction: column; gap: 3px; min-width: 0; }}
    .song {{
      font-size: 0.93rem;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .artist {{
      font-size: 0.8rem;
      color: #999;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .tag {{ font-size: 0.7rem; color: #fc3c44; line-height: 1.5; }}
    .release {{ font-size: 0.68rem; color: #555; }}
    .btn {{
      display: inline-block;
      margin-top: 5px;
      padding: 6px 13px;
      background: #fc3c44;
      color: #fff;
      border-radius: 20px;
      font-size: 0.72rem;
      font-weight: 700;
      text-decoration: none;
    }}
    .no-link {{ font-size: 0.68rem; color: #555; }}
  </style>
</head>
<body>
  <h1>今週のヒップホップ・R&amp;B・ソウル</h1>
  <div class="updated">更新: {now} ／ 全 {len(tracks)} 曲</div>
  {cards}
</body>
</html>"""


def main():
    print("=== 音楽リスト生成開始 ===")
    tracks = collect_tracks()
    print(f"\n合計 {len(tracks)} 曲")

    if not tracks:
        print("曲が取得できませんでした。")
        return

    html = render_html(tracks)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ 生成完了: {out}")


if __name__ == "__main__":
    main()
