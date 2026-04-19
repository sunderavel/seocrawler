import os

from core.constants import MAX_WORKER, SKIP_KEYWORDS, ZERO
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
from apps.seo.helper import normalize_url, extract_keywords, get_hash, create_session
from apps.seo.models import Domain, Page, Insight
from core.constants import MAX_PAGES, CONCURRENT_TASKS, BATCH_SIZE
import asyncio
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import re



# Fetches and parses the robots.txt file to determine disallowed paths
class RobotsHandler:
    def __init__(self, base):
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.set_url(urljoin(base, "/robots.txt"))
        self.rp.read()

    def allowed(self, url):
        return self.rp.can_fetch("*", url)


# Fetches and parses the sitemap.xml file. URLs found in the sitemap will be used to seed the initial crawling queue
def is_valid_sitemap(url: str) -> bool:
    url = url.lower()
    return not any(skip in url for skip in SKIP_KEYWORDS)


def parse_urlset(xml: str):
    soup = BeautifulSoup(xml, "xml")
    return [loc.text.strip() for loc in soup.find_all("loc")]


def parse_sitemapindex(xml: str):
    soup = BeautifulSoup(xml, "xml")
    return [loc.text.strip() for loc in soup.find_all("loc")]


def fetch(session, url):
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            return url, r.text
    except Exception:
        return url, None
    return url, None


def get_sitemap_urls(session, domain, max_workers=20):
    root = urljoin(domain, "/sitemap.xml")

    try:
        res = session.get(root, timeout=10)
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "xml")

        if soup.find("sitemapindex"):
            sitemap_urls = [
                loc.text.strip()
                for loc in soup.find_all("loc")
                if is_valid_sitemap(loc.text)
            ]
            urls = set()

            # Parallel fetch nested sitemaps
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = {
                    ex.submit(fetch, session, u): u
                    for u in sitemap_urls
                }

                for f in as_completed(futures):
                    _, xml = f.result()
                    if not xml:
                        continue

                    # Skip image/video XML quickly
                    if any(x in xml[:200].lower() for x in SKIP_KEYWORDS):
                        continue

                    urls.update(parse_urlset(xml))

            return list(urls)

        # direct urlset sitemap
        else:
            return parse_urlset(res.text)

    except Exception as e:
        print("Sitemap error:", e)
        return []

# A headless browser instance will be launched to render the page's HTML content, ensuring all dynamically loaded content is available
class Browser:
    async def start(self):
        self.p = await async_playwright().start()
        self.browser = await self.p.chromium.launch(headless=True)

    async def render(self, url):
        try:
            page = await self.browser.new_page()
            await page.goto(url, timeout=10000)
            await page.wait_for_load_state("networkidle")
            html = await page.content()
            await page.close()
            return html
        except:
            return None

    async def close(self):
        await self.browser.close()
        await self.p.stop()



# page crawler
async def crawl_page(url, domain, session, robots, seen_hash, browser):
    try:
        url = normalize_url(url)

        if not robots.allowed(url):
            return None

        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, session.get, url)

        html = res.text
        status = res.status_code

        if len(html) < 500:
            html = await browser.render(url)
            status = 200

        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ")

        h = get_hash(text)
        if h in seen_hash:
            return None
        seen_hash.add(h)

        title = soup.title.string.strip() if soup.title else None

        meta = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta.get("content") if meta else None

        h1 = [x.get_text(strip=True) for x in soup.find_all("h1")]
        h2 = [x.get_text(strip=True) for x in soup.find_all("h2")]
        h3 = [x.get_text(strip=True) for x in soup.find_all("h3")]

        p_count = len(soup.find_all("p"))
        img_count = len(soup.find_all("img"))

        internal_links = []
        external_links = 0

        for a in soup.find_all("a", href=True):
            link = normalize_url(urljoin(url, a["href"]))
            if domain in link:
                internal_links.append(link)
            else:
                external_links += 1

        return {
            "url": url,
            "status": status,
            "title": title,
            "meta": meta_desc,
            "h1": h1,
            "h2": h2,
            "h3": h3,
            "p": p_count,
            "img": img_count,
            "internal": internal_links,
            "external": external_links,
            "keywords": extract_keywords(text),
        }

    except Exception as e:
        print("Error:", url, e)
        return None


# main crawler
async def crawl(domain):
    try:
        session = create_session()
        robots = RobotsHandler(domain)
        browser = Browser()
        await browser.start()
        # check sitemap.xml
        sitemap_urls = get_sitemap_urls(session, domain)
        if sitemap_urls:
            print(f"📄 Loaded {len(sitemap_urls)} URLs from sitemap")
            queue = deque(sitemap_urls)
        else:
            print("⚠️ No sitemap, fallback to normal crawl")
            queue = deque([domain])
        visited = set()
        seen_hash = set()

        results = []
        sem = asyncio.Semaphore(CONCURRENT_TASKS)
        async def worker(u):
            async with sem:
                return await crawl_page(u, domain, session, robots, seen_hash, browser)
        tasks = []

        while queue and len(results) < MAX_PAGES:
            url = queue.popleft()
            if url in visited:
                continue

            visited.add(url)
            tasks.append(asyncio.create_task(worker(url)))

            if len(tasks) >= CONCURRENT_TASKS:
                done = await asyncio.gather(*tasks)
                tasks = []

                for d in done:
                    if not d:
                        continue

                    results.append(d)

                    for link in d["internal"]:
                        if link not in visited:
                            queue.append(link)

                    print(f"✅ Crawled ({len(results)}): {d['url']}")

        if tasks:
            done = await asyncio.gather(*tasks)
            results.extend([d for d in done if d])

        await browser.close()
        return results
    except:
        return []


# main command
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("domain", type=str)

    def handle(self, *args, **kwargs):
        domain_url = kwargs["domain"].rstrip("/")
        self.stdout.write(f"🚀 Crawling started: {domain_url}")

        domain_obj, _ = Domain.objects.get_or_create(domain_name=domain_url)

        # Run crawler
        results = asyncio.run(crawl(domain_url))

        if not results:
            self.stdout.write("⚠️ No results found")
            return

        # upsert pages safely
        pages_batch = []
        seen_urls = set()

        for data in results:
            url = data.get("url")
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            pages_batch.append(
                Page(
                    url=url,
                    domain=domain_obj,
                    status_code=data.get("status", 0),
                )
            )

        try:
            with transaction.atomic():
                Page.objects.bulk_create(
                    pages_batch,
                    batch_size=BATCH_SIZE,
                    ignore_conflicts=True,
                )
        except IntegrityError as e:
            self.stderr.write(f"❌ Page bulk_create failed: {e}")
            return

        # Build URL to ID map 
        urls = list(seen_urls)

        url_to_id = {
            obj.url: obj.id
            for obj in Page.objects.filter(url__in=urls).only("id", "url")
        }

        # 4. Avoid duplicate insights for existing pages
        existing_insight_page_ids = set(
            Insight.objects.filter(page_id__in=url_to_id.values())
            .values_list("page_id", flat=True)
        )

        # insights upsert
        insights_batch = []

        for data in results:
            try:
                page_id = url_to_id.get(data.get("url"))
                if not page_id:
                    continue

                if page_id in existing_insight_page_ids:
                    continue
                insights_batch.append(
                    Insight(
                        page_id=page_id,
                        title=data.get("title", ""),
                        meta_description=data.get("meta", ""),
                        h1=data.get("h1", ""),
                        h2=data.get("h2", ""),
                        h3=data.get("h3", ""),
                        p_count=data.get("p", 0),
                        image_count=data.get("img", 0),
                        internal_links=len(data.get("internal", [])),
                        external_links=data.get("external", 0),
                        keywords=data.get("keywords", []),
                    )
                )

                # Batch flush for prevents memory spike
                if len(insights_batch) >= BATCH_SIZE:
                    self._safe_bulk_insert_insights(insights_batch)
                    insights_batch = []

            except Exception as e:
                # isolate bad record, don’t kill pipeline
                self.stderr.write(f"⚠️ Skipping bad insight record: {e}")

        # final flush
        if insights_batch:
            self._safe_bulk_insert_insights(insights_batch)

        self.stdout.write("🎯 Crawling Complete 🚀")

    # safe insert
    def _safe_bulk_insert_insights(self, batch):
        try:
            with transaction.atomic():
                Insight.objects.bulk_create(
                    batch,
                    batch_size=BATCH_SIZE,
                )
        except IntegrityError as e:
            self.stderr.write(f"❌ Insight bulk insert failed: {e}")

            # fallback: insert one by one (last resort safety net)
            for obj in batch:
                try:
                    obj.save()
                except Exception as inner_e:
                    self.stderr.write(f"❌ Failed single insert: {inner_e}")