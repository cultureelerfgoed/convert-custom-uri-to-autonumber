#!/usr/bin/env python3
"""
MaSS (RCE) metadata + image harvester

What it does
------------
1) Pulls the full site list from the MaSS API (`/api/v1/list/{language}`).
2) (Optionally) filters by year/type/text.
3) For each site, builds the public page URL using the `code` and tries common variants:
     • https://mass.cultureelerfgoed.nl/{code}
     • https://mass.cultureelerfgoed.nl/{code}-sa
   (The site often uses "-sa" variants; we try both.)
4) Scrapes the HTML for image URLs that look like `/photos/<size>/<digits>.jpg`.
5) Downloads the first match (configurable) and writes sidecar JSON + a CSV index.

Notes
-----
• The official API does not expose image URLs. Images live under `/photos/` and are referenced in page HTML.
• Respect the API guideline: max ~720 API calls/hour. This script uses *one* List call + optional Get calls,
  then fetches HTML pages (not counted as API calls, but still throttled for politeness).
• Licenses: the API response may include a `license` object. Always check terms before reuse.

Usage
-----
python mass_scraper.py \
  --out ./mass_out \
  --lang nl \
  --image-size s \
  --concurrency 4 \
  --throttle 0.5 \
  --filter-year 1758 \
  --filter-type wreck \
  --contains "Akerendam"

Minimal example (download everything, Dutch labels):
python mass_scraper.py --out ./mass_out --lang nl

"""
import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import requests

BASE = "https://mass.cultureelerfgoed.nl"
API_LIST_TMPL = BASE + "/api/v1/list/{language}"
API_GET_TMPL = BASE + "/api/v1/get/{language}/{id_or_code}"

HEADERS = {
    "User-Agent": "MaSSHarvester/1.0 (+github.com/example; contact: you@example.com)",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}

IMG_REGEX = re.compile(r"/photos/(?:s|m|l)/(\d{6,})\.jpg", re.IGNORECASE)

@dataclass
class Site:
    id: int
    code: str
    label: str
    type: str
    lat: Optional[float]
    lon: Optional[float]
    location: Optional[str]
    firstyear: Optional[int]
    firstyearend: Optional[int]
    lastyear: Optional[int]
    lastyearend: Optional[int]
    discovery: Optional[int]
    subtype: Optional[str]


def fetch_list(language: str) -> List[Site]:
    url = API_LIST_TMPL.format(language=language)
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    out: List[Site] = []
    for o in data:
        out.append(Site(
            id=o.get("id"),
            code=o.get("code"),
            label=o.get("label"),
            type=o.get("type"),
            lat=o.get("lat"),
            lon=o.get("lon"),
            location=o.get("location"),
            firstyear=o.get("firstyear"),
            firstyearend=o.get("firstyearend"),
            lastyear=o.get("lastyear"),
            lastyearend=o.get("lastyearend"),
            discovery=o.get("discovery"),
            subtype=o.get("subtype"),
        ))
    return out


def site_matches(s: Site, args: argparse.Namespace) -> bool:
    if args.filter_type and (s.type or "").lower() != args.filter_type.lower():
        return False
    if args.filter_year is not None:
        y = args.filter_year
        years = [s.firstyear, s.firstyearend, s.lastyear, s.lastyearend, s.discovery]
        if not any((isinstance(v, int) and v == y) for v in years):
            return False
    if args.contains:
        text = f"{s.code} {s.label} {s.location} {s.subtype}".lower()
        if args.contains.lower() not in text:
            return False
    return True


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def try_fetch(url: str, *, throttle: float) -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        # polite throttling between requests
        time.sleep(throttle)
        if resp.status_code == 200:
            return resp
        return None
    except requests.RequestException:
        return None


def page_urls_for_code(code: str) -> List[str]:
    return [
        f"{BASE}/{code}",
        f"{BASE}/{code}-sa",
    ]


def find_image_ids_in_html(html: str, preferred_size: str) -> List[Tuple[str, str]]:
    """Return list of tuples: (image_url, photo_id). Uses first match per size dir.
    preferred_size in {"s","m","l"}.
    """
    matches = IMG_REGEX.findall(html)
    seen = set()
    out = []
    for pid in matches:
        if pid in seen:
            continue
        seen.add(pid)
        out.append((f"{BASE}/photos/{preferred_size}/{pid}.jpg", pid))
    return out


def fetch_api_get(language: str, id_or_code: str, *, throttle: float) -> Optional[dict]:
    url = API_GET_TMPL.format(language=language, id_or_code=id_or_code)
    r = try_fetch(url, throttle=throttle)
    if r is None:
        return None
    try:
        return r.json()
    except Exception:
        return None


def process_site(s: Site, args: argparse.Namespace, csv_writer) -> None:
    # Prepare output paths
    site_dir = os.path.join(args.out, s.code or str(s.id))
    ensure_dir(site_dir)

    # 1) Save API JSON (detailed) for richer fields (license/body/etc.)
    api_detail = fetch_api_get(args.lang, s.code or str(s.id), throttle=args.throttle)
    if not api_detail:
        api_detail = fetch_api_get(args.lang, str(s.id), throttle=args.throttle)

    if api_detail:
        with open(os.path.join(site_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(api_detail, f, ensure_ascii=False, indent=2)

    # 2) Find a page that reveals an image
    html = None
    img_url = None
    img_id = None
    for url in page_urls_for_code(s.code):
        resp = try_fetch(url, throttle=args.throttle)
        if resp is None:
            continue
        html = resp.text
        candidates = find_image_ids_in_html(html, args.image_size)
        if candidates:
            img_url, img_id = candidates[0]
            break

    # 3) Download image if found
    saved_path = None
    if img_url:
        img_resp = try_fetch(img_url, throttle=args.throttle)
        if img_resp is not None and img_resp.content:
            ext = os.path.splitext(img_url)[1] or ".jpg"
            fname = f"{s.code or s.id}_{img_id}{ext}"
            saved_path = os.path.join(site_dir, fname)
            with open(saved_path, "wb") as f:
                f.write(img_resp.content)

    # 4) Write CSV row
    csv_writer.writerow({
        "id": s.id,
        "code": s.code,
        "label": s.label,
        "type": s.type,
        "location": s.location or "",
        "firstyear": s.firstyear if s.firstyear is not None else "",
        "firstyearend": s.firstyearend if s.firstyearend is not None else "",
        "lastyear": s.lastyear if s.lastyear is not None else "",
        "lastyearend": s.lastyearend if s.lastyearend is not None else "",
        "image_url": img_url or "",
        "image_id": img_id or "",
        "image_path": saved_path or "",
    })


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, help="Output directory for files")
    p.add_argument("--lang", default="nl", choices=["nl", "en"], help="API language")
    p.add_argument("--image-size", default="s", choices=["s", "m", "l"], help="Photo size directory to prefer")
    p.add_argument("--throttle", type=float, default=0.5, help="Seconds to sleep between HTTP requests")
    p.add_argument("--concurrency", type=int, default=1, help="(Reserved) Concurrency level; keep 1-4 to be polite")
    p.add_argument("--filter-type", default=None, help="Only process items with this exact type (e.g. 'wreck')")
    p.add_argument("--filter-year", type=int, default=None, help="Only process items where any known year equals this")
    p.add_argument("--contains", default=None, help="Only process items where code/label/location/subtype contains this text")
    p.add_argument("--limit", type=int, default=None, help="Only process the first N matching items (for testing)")
    args = p.parse_args()

    ensure_dir(args.out)

    print("Fetching list…", file=sys.stderr)
    sites = fetch_list(args.lang)

    # Filter
    filtered = [s for s in sites if site_matches(s, args)]
    if args.limit:
        filtered = filtered[: args.limit]

    # CSV index
    csv_path = os.path.join(args.out, "index.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fcsv:
        fieldnames = [
            "id","code","label","type","location","firstyear","firstyearend","lastyear","lastyearend",
            "image_url","image_id","image_path",
        ]
        writer = csv.DictWriter(fcsv, fieldnames=fieldnames)
        writer.writeheader()

        for i, s in enumerate(filtered, 1):
            print(f"[{i}/{len(filtered)}] {s.code}…", file=sys.stderr)
            try:
                process_site(s, args, writer)
            except Exception as e:
                print(f"  ! Error on {s.code}: {e}", file=sys.stderr)

    print(f"Done. CSV written to: {csv_path}")


if __name__ == "__main__":
    main()
