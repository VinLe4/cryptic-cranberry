import os
import re
import json
import hashlib
from datetime import datetime, timezone
from dotenv import load_dotenv
import boto3
from openai import OpenAI

load_dotenv()
client = OpenAI()

# === ENV CONFIG ===
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
ARTICLES_DIR = "articles"
TRACKING_PATH = "data/vector_files.json"

DO_BUCKET = os.getenv("DO_SPACES_BUCKET")
DO_REGION = os.getenv("DO_SPACES_REGION")
DO_KEY = os.getenv("DO_SPACES_KEY")
DO_SECRET = os.getenv("DO_SPACES_SECRET")

session = boto3.session.Session()
s3 = session.client(
    's3',
    region_name=DO_REGION,
    endpoint_url=f'https://{DO_REGION}.digitaloceanspaces.com',
    aws_access_key_id=DO_KEY,
    aws_secret_access_key=DO_SECRET
)

# === HELPERS ===
def load_tracking():
    return json.load(open(TRACKING_PATH)) if os.path.exists(TRACKING_PATH) else {}

def save_tracking(data):
    with open(TRACKING_PATH, "w") as f:
        json.dump(data, f, indent=2)

def compute_hash(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def extract_article_id(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"https://support\.optisigns\.com/hc/en-us/articles/(\d+)", content)
    return match.group(1) if match else None

def slug_to_title(slug):
    name = os.path.splitext(slug)[0]
    name = re.sub(r'-\d{9,}-part\d+', '', name)
    return name.replace("-", " ").replace("_", " ").title()

def upload_file(filepath):
    with open(filepath, "rb") as f:
        upload = client.files.create(file=f, purpose="assistants")
    return upload.id

def delete_from_vector_store(vector_file_id):
    try:
        client.vector_stores.files.delete(
            vector_store_id=VECTOR_STORE_ID,
            file_id=vector_file_id
        )
    except Exception:
        print(f"Failed to delete old vector file {vector_file_id}: {Exception}")

def attach_to_vector_store(file_id, filepath):
    filename = os.path.basename(filepath)
    title = slug_to_title(filename)
    article_id = extract_article_id(filepath)
    metadata = {"title": title}
    if article_id:
        metadata["source"] = f"https://support.optisigns.com/hc/en-us/articles/{article_id}"
    return client.vector_stores.files.create(
        vector_store_id=VECTOR_STORE_ID,
        file_id=file_id,
        attributes=metadata
    )

def upload_log_to_spaces(log_content: str):
    key = "logs/vector_upload.log"

    try:
        existing_obj = s3.get_object(Bucket=DO_BUCKET, Key=key)
        existing_log = existing_obj['Body'].read().decode('utf-8')
    except s3.exceptions.NoSuchKey:
        existing_log = ""

    updated_log = existing_log + "\n\n---\n\n" + log_content

    s3.put_object(
        Bucket=DO_BUCKET,
        Key=key,
        Body=updated_log.encode("utf-8"),
        ACL="public-read",
        ContentType="text/plain"
    )

    public_url = f"https://{DO_BUCKET}.{DO_REGION}.digitaloceanspaces.com/{key}"
    return public_url

# === MAIN ===
def upload_articles():
    print("Starting upload...")
    tracking = load_tracking()
    new_tracking = {}
    added, updated, skipped = 0, 0, 0
    detail_lines = []

    for filename in os.listdir(ARTICLES_DIR):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(ARTICLES_DIR, filename)
        file_hash = compute_hash(filepath)
        prev_entry = tracking.get(filename)

        if prev_entry and prev_entry.get("hash") == file_hash:
            skipped += 1
            new_tracking[filename] = prev_entry
            print("Item skipped")
            continue

        if prev_entry:
            delete_from_vector_store(prev_entry.get("file_id"))

        new_file_id = upload_file(filepath)
        attach_to_vector_store(new_file_id, filepath)

        new_tracking[filename] = {
            "hash": file_hash,
            "file_id": new_file_id
        }

        if prev_entry:
            updated += 1
            detail_lines.append(f"Updated: {filename}")
            print("Item updated")
        else:
            added += 1
            detail_lines.append(f"Added: {filename}")
            print("Item added")

    save_tracking(new_tracking)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Always log, even if added/updated == 0
    log_summary = (
        f"Timestamp: {timestamp}\n"
        f"Added: {added}\nUpdated: {updated}\nSkipped: {skipped}"
    )

    if detail_lines:
        log_summary += "\n\nDetails:\n" + "\n".join(detail_lines)

    public_log_url = upload_log_to_spaces(log_summary)

    print(f"Added: {added}, Updated: {updated}, Skipped: {skipped}")

if __name__ == "__main__":
    upload_articles()
