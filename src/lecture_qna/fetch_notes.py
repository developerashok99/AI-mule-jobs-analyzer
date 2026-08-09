"""Pulls MuleSoft lecture note chapters from the user's Notes GitHub repo."""
import requests

from src.config import NOTES_REPO, NOTES_PATH, GITHUB_TOKEN

API_BASE = "https://api.github.com"


def _headers():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def list_chapters():
    """Returns [{name, path, sha, download_url}] for every .md chapter file, sorted by filename."""
    url = f"{API_BASE}/repos/{NOTES_REPO}/contents/{NOTES_PATH}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    items = resp.json()
    chapters = [
        item for item in items
        if item["type"] == "file" and item["name"].lower().endswith(".md")
    ]
    chapters.sort(key=lambda item: item["name"])
    return chapters


def fetch_chapter_text(download_url):
    resp = requests.get(download_url, timeout=30)
    resp.raise_for_status()
    return resp.text
