#!/usr/bin/env python3
"""
Greenery in-stock scraper.

Pages through the Greenery click-and-collect `main_products` feed for a
given store, keeps only items that are actually in stock, and writes
`instock.csv` with a single column (SKU = the feed's `cspcid`, which is
the 7-digit BCLDB SKU that matches the Glide Product Catalog).

Designed to run in GitHub Actions on a schedule. No auth required — the
feed is public JSON.
"""
import csv
import json
import sys
import time
import urllib.request
import urllib.error

# ── CONFIG ──
STORE_ID  = 14          # Greenery Penticton (your store)
PAGE_SIZE = 500
OUT_FILE  = "instock.csv"
BASE = "https://www.greenerycannabisboutique.ca/ht/api/objects/kiosk/main_products"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "en-CA,en;q=0.9",
    "Referer": "https://www.greenerycannabisboutique.ca/clickncollect/",
}

MAX_PAGES = 50   # safety cap (50 * 500 = 25,000 items)


def fetch_page(page):
    url = (f"{BASE}?on_hand=true&is_active=true&store_id={STORE_ID}"
           f"&page_size={PAGE_SIZE}&page={page}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def is_in_stock(item):
    """A 7-digit BCLDB SKU with positive on_hand and not flagged out_of_stock."""
    sku = (item.get("cspcid") or "").strip()
    if not (sku.isdigit() and len(sku) == 7):
        return None
    on_hand = item.get("on_hand")
    try:
        qty = float(on_hand) if on_hand is not None else 0
    except (ValueError, TypeError):
        qty = 0
    if qty <= 0:
        return None
    if item.get("out_of_stock") is True:
        return None
    return sku


def scrape():
    seen = set()
    ordered = []
    for page in range(MAX_PAGES):
        try:
            data = fetch_page(page)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} on page {page}: {e.reason}", file=sys.stderr)
            break
        except Exception as e:
            print(f"Error on page {page}: {e}", file=sys.stderr)
            break

        if not data:
            break

        for item in data:
            sku = is_in_stock(item)
            if sku and sku not in seen:
                seen.add(sku)
                ordered.append(sku)

        if len(data) < PAGE_SIZE:
            break          # last page
        time.sleep(0.5)    # be polite

    return ordered


def main():
    skus = scrape()
    if not skus:
        # Safety: don't overwrite a good CSV with an empty one if the
        # scrape failed. Exit non-zero so the Action surfaces the problem.
        print("No SKUs scraped — leaving existing CSV untouched.", file=sys.stderr)
        sys.exit(1)

    with open(OUT_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["SKU"])
        for s in skus:
            w.writerow([s])

    print(f"Wrote {len(skus)} in-stock SKUs to {OUT_FILE}")


if __name__ == "__main__":
    main()
