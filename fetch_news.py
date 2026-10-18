import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from html import unescape
from urllib.parse import quote

# Her kaynak: ad, kategori, RSS adresi
FEEDS = [
    # EKONOMİ VE FİNANS
    (
        "Bloomberg HT",
        "Ekonomi ve Finans",
        "https://www.bloomberght.com/rss"
    ),
    (
        "Google News - Ekonomi",
        "Ekonomi ve Finans",
        "https://news.google.com/rss/search?q=" +
        quote("ekonomi OR enflasyon OR merkez bankası OR şirketler") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),
    (
        "Google News - Küresel Ekonomi",
        "Ekonomi ve Finans",
        "https://news.google.com/rss/search?q=" +
        quote("global economy OR inflation OR central bank OR business") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),

    # SAVUNMA
    (
        "Google News - Savunma",
        "Savunma",
        "https://news.google.com/rss/search?q=" +
        quote("savunma sanayii OR askerî teknoloji OR silahlı kuvvetler") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),
    (
        "Google News - Uluslararası Savunma",
        "Savunma",
        "https://news.google.com/rss/search?q=" +
        quote("defense technology OR military OR naval OR air force") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),

    # DÜNYA VE DİPLOMASİ
    (
        "BBC Türkçe",
        "Dünya ve Diplomasi",
        "https://feeds.bbci.co.uk/turkce/rss.xml"
    ),
    (
        "DW Türkçe",
        "Dünya ve Diplomasi",
        "https://rss.dw.com/rdf/rss-tur-all"
    ),
    (
        "Anadolu Ajansı",
        "Dünya ve Diplomasi",
        "https://www.aa.com.tr/tr/rss/default?cat=guncel"
    ),
    (
        "TRT Haber",
        "Dünya ve Diplomasi",
        "https://www.trthaber.com/sondakika.rss"
    ),
    (
        "BBC World",
        "Dünya ve Diplomasi",
        "https://feeds.bbci.co.uk/news/world/rss.xml"
    ),
    (
        "Al Jazeera",
        "Dünya ve Diplomasi",
        "https://www.aljazeera.com/xml/rss/all.xml"
    ),

    # PİYASALAR
    (
        "Google News - Piyasalar",
        "Piyasalar",
        "https://news.google.com/rss/search?q=" +
        quote("Borsa İstanbul OR altın fiyatları OR dolar OR petrol OR bitcoin") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),
    (
        "Google News - Küresel Piyasalar",
        "Piyasalar",
        "https://news.google.com/rss/search?q=" +
        quote("stock market OR gold price OR oil price OR currency markets") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),

    # TEKNOLOJİ VE BİLİM
    (
        "Google News - Teknoloji",
        "Teknoloji ve Bilim",
        "https://news.google.com/rss/search?q=" +
        quote("yapay zekâ OR teknoloji OR siber güvenlik OR uzay araştırmaları") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),
    (
        "Google News - Küresel Teknoloji",
        "Teknoloji ve Bilim",
        "https://news.google.com/rss/search?q=" +
        quote("artificial intelligence OR cybersecurity OR space technology") +
        "&hl=tr&gl=TR&ceid=TR:tr"
    ),
]

MAX_PER_FEED = 15
MAX_TOTAL = 100


def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def child_text(node, *names):
    for name in names:
        element = node.find(name)
        if element is not None and element.text:
            return element.text.strip()
    return ""


def parse_date(value):
    if not value:
        return ""

    try:
        date = parsedate_to_datetime(value)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    except (ValueError, TypeError, OverflowError):
        return ""


def get_image(node):
    # RSS medya alanları
    for tag in (
        "{http://search.yahoo.com/mrss/}thumbnail",
        "{http://search.yahoo.com/mrss/}content",
        "enclosure",
    ):
        for element in node.findall(tag):
            url = element.get("url", "")
            media_type = element.get("type", "")

            if url and (
                tag != "enclosure"
                or media_type.startswith("image/")
                or not media_type
            ):
                return unescape(url)

    # Bazı RSS akışlarında görsel açıklama HTML'inde bulunur.
    description = child_text(node, "description")
    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        description,
        re.IGNORECASE,
    )

    return unescape(match.group(1)) if match else ""


def get_link(node):
    link = child_text(node, "link")

    if link:
        return link

    # Atom biçimindeki akışları da destekle.
    for element in node:
        if element.tag.endswith("link"):
            href = element.get("href", "")
            if href:
                return href

    return ""


def get_entries(root):
    entries = root.findall(".//item")

    if entries:
        return entries

    return [
        element
        for element in root.iter()
        if element.tag.endswith("entry")
    ]


def get_title(node):
    return clean(child_text(node, "title"))


def get_summary(node):
    return clean(
        child_text(
            node,
            "description",
            "{http://www.w3.org/2005/Atom}summary",
            "{http://www.w3.org/2005/Atom}content",
        )
    )


def get_published(node):
    return child_text(
        node,
        "pubDate",
        "published",
        "updated",
        "{http://www.w3.org/2005/Atom}published",
        "{http://www.w3.org/2005/Atom}updated",
    )


items = []
seen = set()
successful_feeds = 0

for source, category, url in FEEDS:
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ILTERISNews/1.0)"
            },
        )

        with urllib.request.urlopen(request, timeout=25) as response:
            xml_data = response.read(3_000_000)

        root = ET.fromstring(xml_data)
        entries = get_entries(root)
        successful_feeds += 1

        source_count = 0

        for node in entries:
            if source_count >= MAX_PER_FEED:
                break

            title = get_title(node)
            link = get_link(node)

            if not title or not link:
                continue

            if link in seen:
                continue

            seen.add(link)

            items.append({
                "title": title[:240],
                "image": get_image(node),
                "link": link,
                "summary": get_summary(node)[:500],
                "source": source,
                "category": category,
                "published_at": parse_date(get_published(node)),
            })

            source_count += 1

        print(
            f"OK: {source} - {source_count} haber"
        )

    except Exception as error:
        print(f"Kaynak okunamadı: {source} - {error}")


# Tarihi olmayan haberleri listenin sonuna al.
items.sort(
    key=lambda item: item["published_at"],
    reverse=True,
)

output = {
    "updated_at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    ),
    "items": items[:MAX_TOTAL],
}

# Hiçbir kaynak çalışmazsa mevcut haber dosyasını boşaltma.
if successful_feeds == 0:
    raise RuntimeError(
        "Hiçbir RSS kaynağı okunamadı. Mevcut news.json korunuyor."
    )

Path("news.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("Başarılı kaynak sayısı:", successful_feeds)
print("Toplanan haber sayısı:", len(output["items"]))
    
