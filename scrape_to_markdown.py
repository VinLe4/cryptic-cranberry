import requests
import os
import html2text
from slugify import slugify

BASE_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
OUTPUT_DIR = "articles"
LIMIT = 31

os.makedirs(OUTPUT_DIR, exist_ok=True)
converter = html2text.HTML2Text()
converter.ignore_links = False
converter.ignore_images = False
converter.body_width = 0

def fetch_articles():
    all_articles = []
    url = BASE_URL

    while url and len(all_articles) < LIMIT:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        all_articles.extend(data['articles'])
        url = data.get('next_page')

    return all_articles[:LIMIT]

def clean_and_save(article):
    title = article['title']
    html = article['body']
    url = article['html_url']
    markdown = converter.handle(html)
    slug = slugify(title)
    article_id = str(article['id'])
    filepath = os.path.join(OUTPUT_DIR, f"{slug}-{article_id}.md")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(markdown)
        f.write(f"\n\n---\n\nArticle URL: {url}\n")

def scrape_articles():
    print("Fetching articles...")
    articles = fetch_articles()
    for article in articles:
        clean_and_save(article)

if __name__ == "__main__":
    scrape_articles()
