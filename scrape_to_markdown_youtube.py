import requests
import os
import html2text
from slugify import slugify

ARTICLE_ID = "360051014713"
API_URL = f"https://support.optisigns.com/api/v2/help_center/articles/{ARTICLE_ID}.json"
OUTPUT_DIR = "articles"

os.makedirs(OUTPUT_DIR, exist_ok=True)

converter = html2text.HTML2Text()
converter.ignore_links = False
converter.ignore_images = False
converter.body_width = 0

def fetch_article(article_id):
    resp = requests.get(API_URL)
    resp.raise_for_status()
    return resp.json()["article"]

def save_article(article):
    title = article["title"]
    html = article["body"]
    markdown = converter.handle(html)
    slug = slugify(title)
    filename = os.path.join(OUTPUT_DIR, f"{slug}-{ARTICLE_ID}.md")  # ✅ Include ID in filename
    article_url = f"https://support.optisigns.com/hc/en-us/articles/{ARTICLE_ID}"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(markdown)
        f.write(f"\n\n---\n\nArticle URL: {article_url}\n")

    print(f"✅ Saved: {filename}")


if __name__ == "__main__":
    article = fetch_article(ARTICLE_ID)
    save_article(article)
