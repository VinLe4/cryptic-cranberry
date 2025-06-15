from scrape_to_markdown import scrape_articles
from upload_to_openai import upload_articles

def main():
    scrape_articles()
    upload_articles()

if __name__ == "__main__":
    main()