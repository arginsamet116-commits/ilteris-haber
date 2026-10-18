
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from html import unescape

FEEDS = [
    # Mevcut haber kaynakları
    ("BBC Türkçe", "Türkiye", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    ("Al Jazeera", "Dünya", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("BBC World", "Dünya", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Google News - Savunma", "Savunma", "https://news.google.com/rss/search?q=defense+OR+military+technology&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google News - Diplomasi", "Siyaset", "https://news.google.com/rss/search?q=diplomacy+OR+international+politics&hl=tr&gl=TR&ceid=TR:tr"),

    # Türkiye ekonomisi
    ("Google News - Türkiye Ekonomisi", "Ekonomi", "https://news.google.com/rss/search?q=Türkiye+ekonomisi+OR+enflasyon+OR+faiz+kararı&hl=tr&gl=TR&ceid=TR:tr"),

    # Dünya ekonomisi
    ("Google News - Dünya Ekonomisi", "Ekonomi", "https://news.google.com/rss/search?q=global+economy+OR+world+economy+OR+inflation&hl=tr&gl=TR&ceid=TR:tr"),

    # Finansal piyasalar
    ("Google News - Piyasalar", "Piyasalar", "https://news.google.com/rss/search?q=Borsa+İstanbul+OR+altın+fiyatları+OR+dolar+OR+petrol+OR+stock+markets&hl=tr&gl=TR&ceid=TR:tr"),
]
