import json
import subprocess
import sys
import hashlib
from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

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
    "User-Agent": "ETL-BDPM/1.0"
}


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

    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("signature")


def save_signature(signature: str):
    DATA_DIR.mkdir(exist_ok=True)

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "signature": signature,
                "updated_at": datetime.now(UTC).isoformat()
            },
            f,
            indent=2,
            ensure_ascii=False
        )


# =========================
# SCRAPING
# =========================

def get_bdpm_file_urls():
    r = requests.get(
        PAGE_URL,
        headers=HEADERS,
        timeout=30
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    urls = {}

    for link in soup.find_all("a", href=True):

        if not isinstance(link, Tag):
            continue

        href = str(link["href"])

        for expected in EXPECTED_FILES:
            if expected.lower() in href.lower():
                urls[expected] = urljoin(BASE_URL, href)

    missing = EXPECTED_FILES - set(urls.keys())

    if missing:
        raise RuntimeError(
            f"Fichiers BDPM introuvables : {missing}"
        )

    return urls


# =========================
# DOWNLOAD + HASH
# =========================

def download_and_compute(urls):

    DATA_DIR.mkdir(exist_ok=True)

    downloaded = {}
    hashes = []

    for name, url in sorted(urls.items()):

        print(f"⬇ Téléchargement : {name}")

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=300
        )
        r.raise_for_status()

        content = r.content

        downloaded[name] = content
        hashes.append(sha256_bytes(content))

    global_signature = sha256_bytes(
        "".join(hashes).encode()
    )

    return downloaded, global_signature


# =========================
# SAVE FILES
# =========================

def save_files(downloaded):

    for name, content in downloaded.items():

        with open(DATA_DIR / name, "wb") as f:
            f.write(content)


# =========================
# ETL
# =========================

def run_etl():

    print("⚙ Construction de bdpm.db...")

    subprocess.run(
        [sys.executable, "database.py"],
        check=True
    )


# =========================
# MAIN
# =========================

def main():

    print("📡 Récupération des URLs BDPM...")
    urls = get_bdpm_file_urls()

    print("🔐 Téléchargement + calcul signature...")
    downloaded, remote_sig = download_and_compute(urls)

    local_sig = get_local_signature()

    print("Remote :", remote_sig)
    print("Local  :", local_sig)

    if remote_sig == local_sig:
        print("✔ BDPM déjà à jour")
        sys.exit(0)

    print("🆕 Nouvelle version détectée")

    save_files(downloaded)

    run_etl()

    save_signature(remote_sig)

    print("✅ Mise à jour BDPM terminée")


if __name__ == "__main__":
    main()

