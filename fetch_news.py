import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from html import unescape

FEEDS = [
    # Türkiye gündemi
    (
        "BBC Türkçe",
        "Türkiye",
        "https://feeds.bbci.co.uk/turkce/rss.xml"
    ),
    (
        "TRT Haber",
        "Türkiye",
        "https://www.trthaber.com/sondakika.rss"
    ),
    (
        "DW Türkçe",
        "Dünya",
        "https://rss.dw.com/rdf/rss-tur-all"
    ),
    (
        "Anadolu Ajansı",
        "Dünya",
        "https://www.aa.com.tr/tr/rss/default?cat=guncel"
    ),
    # Dünya gündemi
    (
        "Al Jazeera",
        "Dünya",
        "https://www.aljazeera.com/xml/rss/all.xml"
    ),
    (
        "BBC World",
        "Dünya",
        "https://feeds.bbci.co.uk/news/world/rss.xml"
    ),

    # Savunma
    (
        "Google News - Savunma",
        "Savunma",
        "https://news.google.com/rss/search?q=defense+OR+military+technology&hl=tr&gl=TR&ceid=TR:tr"
    ),

    # Diplomasi ve siyaset
    (
        "Google News - Diplomasi",
        "Siyaset",
        "https://news.google.com/rss/search?q=diplomacy+OR+international+politics&hl=tr&gl=TR&ceid=TR:tr"
    ),

    # Türkiye ekonomisi
    (
        "Google News - Türkiye Ekonomisi",
        "Ekonomi",
        "https://news.google.com/rss/search?q=Türkiye+ekonomisi+OR+enflasyon+OR+faiz+kararı&hl=tr&gl=TR&ceid=TR:tr"
    ),

    # Dünya ekonomisi
    (
        "Google News - Dünya Ekonomisi",
        "Ekonomi",
        "https://news.google.com/rss/search?q=global+economy+OR+world+economy+OR+inflation&hl=tr&gl=TR&ceid=TR:tr"
    ),

    # Finansal piyasalar
    (
        "Google News - Piyasalar",
        "Piyasalar",
        "https://news.google.com/rss/search?q=Borsa+İstanbul+OR+altın+fiyatları+OR+dolar+OR+petrol+OR+stock+markets&hl=tr&gl=TR&ceid=TR:tr"
    ),
]


def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def parse_date(value):
    try:
        return (
            parsedate_to_datetime(value)
            .astimezone(timezone.utc)
            .strftime("%Y-%m-%d %H:%M UTC")
        )
    except Exception:
        return value or ""


items = []
seen = set()

for source, category, url in FEEDS:
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 ILTERIS"}
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            root = ET.fromstring(response.read(2000000))

        for node in root.findall(".//item")[:20]:
            title = clean(node.findtext("title"))
            link = (node.findtext("link") or "").strip()

            if not title or not link or link in seen:
                continue

            seen.add(link)

            items.append({
                "title": title[:240],
                                "image": (
                    next(
                        (
                            el.get("url", "")
                            for tag in (
                                "{http://search.yahoo.com/mrss/}content",
                                "{http://search.yahoo.com/mrss/}thumbnail",
                                "enclosure"
                            )
                            for el in node.findall(tag)
                            if el.get("url")
                            or el.get("type", "").startswith("image/")
                        ),
                        ""
                    )
                    or next(
                        (
                            re.search(
                                r'<img[^>]+src=["\']([^"\']+)["\']',
                                node.findtext("description") or "",
                                re.IGNORECASE
                            ).group(1)
                            for _ in [0]
                            if re.search(
                                r'<img[^>]+src=["\']([^"\']+)["\']',
                                node.findtext("description") or "",
                                re.IGNORECASE
                            )
                        ),
                        ""
                    )
                ),
                "link": link,
                "summary": clean(
                    node.findtext("description")
                )[:320],
                "source": source,
                "category": category,
                "published_at": parse_date(
                    node.findtext("pubDate")
                )
            })

    except Exception as error:
        print("Kaynak okunamadı:", source, error)


items.sort(
    key=lambda item: item["published_at"],
    reverse=True
)

Path("news.json").write_text(
    json.dumps(
        {
            "updated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
            "items": items[:60]
        },
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print("İLTERİS haber sayısı:", len(items[:60]))
