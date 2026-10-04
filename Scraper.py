import csv
import json
import logging
import random
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# -----------------------------
# Logging
# -----------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("ReusableScraper")


# -----------------------------
# Configuration
# -----------------------------

with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

URL = config["url"]
TIMEOUT = config.get("timeout", 20)
DELAY_MIN = config.get("delay_min", 2)
DELAY_MAX = config.get("delay_max", 5)
OUTPUT_FILE = config.get("output_file", "output/results.csv")


# -----------------------------
# Session
# -----------------------------

session = requests.Session()

retry_strategy = Retry(
    total=4,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True
)

adapter = HTTPAdapter(
    max_retries=retry_strategy
)

session.mount("https://", adapter)
session.mount("http://", adapter)


# -----------------------------
# Browser-like basic headers
# -----------------------------

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
})


# -----------------------------
# Polite delay
# -----------------------------

def polite_delay():
    delay = random.uniform(DELAY_MIN, DELAY_MAX)

    logger.info(
        "Waiting %.2f seconds before next request...",
        delay
    )

    time.sleep(delay)


# -----------------------------
# Fetch page
# -----------------------------

def fetch_page(url):
    try:
        logger.info("Requesting: %s", url)

        response = session.get(
            url,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        logger.info(
            "Success: HTTP %s",
            response.status_code
        )

        return response.text

    except requests.RequestException as error:
        logger.error(
            "Request failed: %s",
            error
        )

        return None


# -----------------------------
# Parse page
# -----------------------------

def parse_page(html):
    soup = BeautifulSoup(
        html,
        "lxml"
    )

    title = soup.title.get_text(
        strip=True
    ) if soup.title else ""

    headings = [
        h.get_text(" ", strip=True)
        for h in soup.find_all(["h1", "h2", "h3"])
    ]

    links = []

    for link in soup.find_all("a", href=True):
        links.append({
            "text": link.get_text(" ", strip=True),
            "url": link["href"]
        })

    return {
        "title": title,
        "headings": headings,
        "links": links
    }


# -----------------------------
# Save CSV
# -----------------------------

def save_results(data):
    Path(OUTPUT_FILE).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = []

    for heading in data["headings"]:
        rows.append({
            "type": "heading",
            "text": heading,
            "url": ""
        })

    for link in data["links"]:
        rows.append({
            "type": "link",
            "text": link["text"],
            "url": link["url"]
        })

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=["type", "text", "url"]
        )

        writer.writeheader()
        writer.writerows(rows)

    logger.info(
        "Saved %d records to %s",
        len(rows),
        OUTPUT_FILE
    )


# -----------------------------
# Main
# -----------------------------

def main():

    logger.info("Reusable scraper started")

    polite_delay()

    html = fetch_page(URL)

    if not html:
        logger.error("Could not retrieve page.")
        return

    data = parse_page(html)

    logger.info(
        "Page title: %s",
        data["title"]
    )

    logger.info(
        "Found %d headings and %d links",
        len(data["headings"]),
        len(data["links"])
    )

    save_results(data)

    logger.info("Scraping completed successfully.")


if __name__ == "__main__":
    main()
