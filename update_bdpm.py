import json
import subprocess
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# =========================
# CONFIG
# =========================

BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr"
PAGE_URL = f"{BASE_URL}/telechargement"

DATA_DIR = Path("data")
META_FILE = DATA_DIR / ".bdpm_meta.json"

EXPECTED_FILES = {
    "CIS_bdpm.txt",
    "CIS_CIP_bdpm.txt",
    "CIS_COMPO_bdpm.txt",
    "CIS_CPD_bdpm.txt",
    "CIS_GENER_bdpm.txt",
}

HEADERS = {
    "User-Agent": "ETL-BDPM/1.0 (GitHub Actions)"
}


# =========================
# HTTP SESSION (RETRY SAFE)
# =========================

def get_session():
    session = requests.Session()

    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


session = get_session()


# =========================
# HASH
# =========================

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# =========================
# META
# =========================

def get_local_signature():
    if not META_FILE.exists():
        return None

    try:
        return json.loads(META_FILE.read_text(encoding="utf-8")).get("signature")
    except Exception:
        return None


def save_signature(signature: str):
    DATA_DIR.mkdir(exist_ok=True)

    META_FILE.write_text(
        json.dumps(
            {
                "signature": signature,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


# =========================
# SCRAPING
# =========================

def get_bdpm_file_urls():
    r = session.get(PAGE_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    urls = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]

        for expected in EXPECTED_FILES:
            if expected.lower() in href.lower():
                urls[expected] = urljoin(BASE_URL, href)

    missing = EXPECTED_FILES - set(urls.keys())

    if missing:
        raise RuntimeError(f"Fichiers BDPM introuvables : {missing}")

    return urls


# =========================
# DOWNLOAD
# =========================

def download_and_compute(urls):
    DATA_DIR.mkdir(exist_ok=True)

    downloaded = {}
    hashes = []

    for name, url in sorted(urls.items()):
        print(f"⬇ Download: {name}")

        r = session.get(url, headers=HEADERS, timeout=300)
        r.raise_for_status()

        content = r.content
        downloaded[name] = content
        hashes.append(sha256_bytes(content))

    global_signature = sha256_bytes("".join(hashes).encode())

    return downloaded, global_signature


# =========================
# SAVE FILES
# =========================

def save_files(downloaded):
    DATA_DIR.mkdir(exist_ok=True)

    for name, content in downloaded.items():
        path = DATA_DIR / name
        path.write_bytes(content)


# =========================
# ETL STEP
# =========================

def run_etl():
    print("⚙ Building bdpm database...")

    db_script = Path("database.py")

    if not db_script.exists():
        raise FileNotFoundError("database.py not found in repo")

    subprocess.run([sys.executable, str(db_script)], check=True)


# =========================
# MAIN
# =========================

def main():
    print("📡 Fetching BDPM URLs...")

    urls = get_bdpm_file_urls()

    print("🔐 Download + signature...")

    downloaded, remote_sig = download_and_compute(urls)

    local_sig = get_local_signature()

    print("Remote:", remote_sig)
    print("Local :", local_sig)

    if remote_sig == local_sig:
        print("✔ BDPM already up to date")
        sys.exit(0)

    print("🆕 New version detected")

    save_files(downloaded)

    run_etl()

    save_signature(remote_sig)

    print("✅ BDPM update completed")


if __name__ == "__main__":
    main()