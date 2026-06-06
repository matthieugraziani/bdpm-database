import json
import subprocess
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

DATASET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "base-de-donnees-publique-des-medicaments-base-officielle/"
)

META_FILE = Path(".bdpm_meta.json")
FILES_DIR = Path("data")

EXPECTED_FILES = {
    "CIS_bdpm.txt",
    "CIS_CIP_bdpm.txt",
    "CIS_COMPO_bdpm.txt",
    "CIS_CPD_bdpm.txt",
    "CIS_GENER_bdpm.txt",
}


def get_dataset():
    headers = {"User-Agent": "ETL-BDPM/1.0"}
    r = requests.get(DATASET_URL, headers=headers, timeout=30)
    r.raise_for_status()

    if not r.text.strip():
        raise ValueError(f"Réponse vide (status {r.status_code})")

    return r.json()


def get_remote_version(dataset_info):
    return dataset_info.get("last_update")


def get_local_version():
    if not META_FILE.exists():
        return None
    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("version")


def save_version(version):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": version}, f, indent=2)


def download_resources(dataset_info=None):
    """
    Télécharge les fichiers BDPM depuis la page officielle
    https://base-donnees-publique.medicaments.gouv.fr/telechargement
    """

    FILES_DIR.mkdir(exist_ok=True)

    BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr"
    PAGE_URL = f"{BASE_URL}/telechargement"

    headers = {"User-Agent": "ETL-BDPM/1.0"}

    # Récupération de la page de téléchargement
    response = requests.get(PAGE_URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    downloaded = set()

    # Recherche de tous les liens de téléchargement
    for link in soup.find_all("a", href=True):
        href = link["href"]

        for expected in EXPECTED_FILES:
            if expected.lower() in href.lower():
                url = urljoin(BASE_URL, href)

                print(f"Téléchargement : {expected}")
                print(f"  -> {url}")

                r = requests.get(
                    url,
                    headers=headers,
                    timeout=300,
                    allow_redirects=True,
                )
                r.raise_for_status()

                with open(FILES_DIR / expected, "wb") as f:
                    f.write(r.content)

                downloaded.add(expected)
                break

    missing = EXPECTED_FILES - downloaded

    if missing:
        raise RuntimeError(
            f"Fichiers introuvables sur la page de téléchargement : {missing}"
        )

    print(f"✅ {len(downloaded)} fichiers téléchargés.")


def run_etl():
    print("Construction de bdpm.db...")
    subprocess.run(["python", "database.py"], check=True)


if __name__ == "__main__":
    dataset = get_dataset()

    remote_version = get_remote_version(dataset)
    local_version = get_local_version()

    print("Version distante :", remote_version)
    print("Version locale   :", local_version)

    if remote_version == local_version:
        print("BDPM déjà à jour")
        raise SystemExit(0)

    download_resources(dataset)
    run_etl()
    save_version(remote_version)

    print("Mise à jour terminée")