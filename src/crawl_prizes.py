"""
Module to crawl prize values for each Vietlott draw and save to data/<product>_prizes.jsonl
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

import click
import pendulum
import requests
from bs4 import BeautifulSoup
from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

PRODUCT_URL_MAP = {
    "power655": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655?id={id}&nocatche=1",
    "power645": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645?id={id}&nocatche=1",
    "3d": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3d?id={id}&nocatche=1",
    "3d_pro": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3dpro?id={id}&nocatche=1",
    "power535": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535?id={id}&nocatche=1",
}


def parse_prize_table(html_text: str) -> List[Dict[str, str]]:
    """
    Parse HTML content to extract prize information tables.
    Handles single or multiple tables (e.g., Max 3D has 3D Basic & 3D+ tables).
    """
    soup = BeautifulSoup(html_text, "lxml")
    tables = soup.find_all("table")
    prize_list = []

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        for r in rows:
            tds = r.find_all("td")
            if not tds:
                continue

            cols = [td.text.strip().replace("\n", " ") for td in tds]
            if len(cols) >= 4:
                prize_name = cols[0]
                winners_count = cols[2]
                prize_value = cols[3]
                prize_list.append(
                    {
                        "prize_name": prize_name,
                        "winners_count": winners_count,
                        "prize_value": prize_value,
                    }
                )
    return prize_list


def fetch_draw_prizes(product: str, draw_id: str) -> List[Dict[str, str]]:
    """
    Fetch prize details for a specific product and draw ID.
    """
    url_template = PRODUCT_URL_MAP.get(product)
    if not url_template:
        return []

    url = url_template.format(id=draw_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return parse_prize_table(res.text)
        else:
            logger.warning(f"Fetch failed product={product} id={draw_id} status={res.status_code}")
    except Exception as e:
        logger.error(f"Error fetching product={product} id={draw_id}: {e}")

    return []


def crawl_product_prizes(product: str, max_workers: int = 5, limit: Optional[int] = None):
    """
    Crawl prize data for all draws of a given product.
    Reads from data/<product>.jsonl and writes to data/<product>_prizes.jsonl
    """
    input_file = DATA_DIR / f"{product}.jsonl"
    output_file = DATA_DIR / f"{product}_prizes.jsonl"

    if not input_file.exists():
        logger.error(f"Input data file does not exist: {input_file}")
        return

    # Load existing crawled IDs for incremental update
    existing_ids = set()
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        existing_ids.add(data.get("id"))
                    except json.JSONDecodeError:
                        continue

    logger.info(f"Product {product}: found {len(existing_ids)} existing prize records.")

    # Read target draws
    draws_to_crawl = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            draw_id = item.get("id")
            if draw_id and draw_id not in existing_ids:
                draws_to_crawl.append(item)

    if limit:
        draws_to_crawl = draws_to_crawl[:limit]

    logger.info(f"Product {product}: {len(draws_to_crawl)} draws remaining to crawl.")
    if not draws_to_crawl:
        logger.info(f"Product {product} is already up to date.")
        return

    # Open output file in append mode
    with open(output_file, "a", encoding="utf-8") as out_f, ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_draw = {executor.submit(fetch_draw_prizes, product, draw["id"]): draw for draw in draws_to_crawl}

        count = 0
        for future in as_completed(future_to_draw):
            draw = future_to_draw[future]
            try:
                prizes = future.result()
                if prizes:
                    record = {
                        "date": draw.get("date"),
                        "id": draw.get("id"),
                        "prizes": prizes,
                        "process_time": pendulum.now().to_iso8601_string(),
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_f.flush()
                    count += 1
                    if count % 50 == 0:
                        logger.info(f"Product {product}: Progress {count}/{len(draws_to_crawl)}")
            except Exception as e:
                logger.error(f"Failed processing draw {draw.get('id')}: {e}")

    logger.info(f"Finished crawling prizes for {product}. Added {count} new records to {output_file.name}.")
    if count > 0:
        from sort_prizes import sort_prize_file

        sort_prize_file(output_file)


@click.command()
@click.option(
    "--product",
    type=click.Choice(list(PRODUCT_URL_MAP.keys()) + ["all"]),
    default="all",
    help="Product to crawl prize values for",
)
@click.option("--workers", default=5, type=int, help="Number of concurrent workers")
@click.option("--limit", default=None, type=int, help="Limit number of draws to crawl (for testing)")
def main(product: str, workers: int, limit: Optional[int]):
    """
    Crawl prize data for each Vietlott draw and save to data/<product>_prizes.jsonl
    """
    products = list(PRODUCT_URL_MAP.keys()) if product == "all" else [product]
    for p in products:
        logger.info(f"Starting prize crawl for product: {p}")
        crawl_product_prizes(product=p, max_workers=workers, limit=limit)


if __name__ == "__main__":
    main()
