import os

from core.constants import ZERO
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from django.core.management.base import BaseCommand
from apps.seo.models import Domain, Page, Insight

import asyncio
import requests
from urllib.parse import urljoin, urlparse
from collections import deque, Counter
from bs4 import BeautifulSoup
import urllib.robotparser
import hashlib

from playwright.async_api import async_playwright
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from django.db.models import Q

from apps.seo.models import Domain, Page, Insight

import asyncio
import nltk
from nltk.corpus import stopwords

nltk.download("stopwords")
STOPWORDS = set(stopwords.words("english"))

# normalize url for prevention duplicates
def normalize_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

#extract keywords using nltk
def extract_keywords(text):
    words = [w.lower() for w in text.split() if w.isalpha()]
    words = [w for w in words if w not in STOPWORDS]

    total = len(words)
    freq = Counter(words)

    return [
        {"keyword": w, "density": round((c / total) * 100, 2) if total else 0}
        for w, c in freq.most_common(10)
    ]

# get hash for skip duplicate content
def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()



# session
def create_session():
    HEADERS = {"User-Agent": "SEO-Bot/Async-1.0"}

    session = requests.Session()
    session.headers.update(HEADERS)
    return session
