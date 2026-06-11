import json
import subprocess
import sys
import hashlib
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

HEADERS = {"User-Agent": "ETL-BDPM/1.0"}


# =========================
# UTILS HASH
# =========================

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_file_hash(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return sha256_bytes(r.content)


# =========================
# VERSION LOCAL
# =========================

def get_local_signature():
    if not META_FILE.exists():
        return None

    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("signature")


def save_signature(signature: str):
    DATA_DIR.mkdir(exist_ok=True)

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"signature": signature}, f, indent=2)


# =========================
# SCRAPING LIENS BDPM
# =========================

def get_bdpm_file_urls():
    r = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
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
        raise RuntimeError(f"Fichiers BDPM introuvables : {missing}")

    return urls


# =========================
# SIGNATURE GLOBALE
# =========================

def compute_remote_signature(urls: dict) -> str:
    """
    Hash global basé sur le contenu réel des fichiers
    """
    hashes = []

    for name, url in sorted(urls.items()):
        print(f"🔍 Hash fichier : {name}")
        file_hash = fetch_file_hash(url)
        hashes.append(file_hash)

    return sha256_bytes("".join(hashes).encode())


# =========================
# DOWNLOAD FILES
# =========================

def download_resources(urls: dict):
    DATA_DIR.mkdir(exist_ok=True)

    for name, url in urls.items():
        print(f"⬇ Téléchargement : {name}")

        r = requests.get(url, headers=HEADERS, timeout=300)
        r.raise_for_status()

        with open(DATA_DIR / name, "wb") as f:
            f.write(r.content)


# =========================
# ETL
# =========================

def run_etl():
    print("⚙ Construction de bdpm.db...")

    result = subprocess.run(
        [sys.executable, "database.py"],
        check=True
    )

    return result.returncode


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("📡 Récupération des URLs BDPM...")
    urls = get_bdpm_file_urls()

    print("🔐 Calcul signature distante...")
    remote_sig = compute_remote_signature(urls)

    print("💾 Signature locale...")
    local_sig = get_local_signature()

    print("Remote :", remote_sig)
    print("Local  :", local_sig)

    # =========================
    # CHECK UPDATE
    # =========================

    if remote_sig == local_sig:
        print("✔ BDPM déjà à jour → exit")
        raise SystemExit(0)

    print("🆕 Nouvelle version détectée")

    # =========================
    # PIPELINE
    # =========================

    download_resources(urls)
    run_etl()
    save_signature(remote_sig)

    print("✅ Mise à jour BDPM terminée")