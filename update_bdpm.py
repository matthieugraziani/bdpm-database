import json
import subprocess
from pathlib import Path

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


def download_resources(dataset_info):
    FILES_DIR.mkdir(exist_ok=True)

    resources = dataset_info.get("resources", [])

    # Debug : affiche toutes les ressources disponibles
    print(f"Ressources trouvées : {len(resources)}")
    for r in resources:
        print(f"  → title: {r.get('title')!r} | url: {r.get('url','')}")

    downloaded = set()

    for resource in resources:
        url = resource.get("url", "")
        title = resource.get("title", "")

        if not url:
            continue

        # ✅ Cherche le nom de fichier attendu dans le title OU dans l'URL
        matched_file = None
        for expected in EXPECTED_FILES:
            if expected in title or expected in url:
                matched_file = expected
                break

        if not matched_file:
            continue

        print(f"Téléchargement : {matched_file}  ({url})")

        r = requests.get(url, headers={"User-Agent": "ETL-BDPM/1.0"}, timeout=300)
        r.raise_for_status()

        with open(FILES_DIR / matched_file, "wb") as f:
            f.write(r.content)

        downloaded.add(matched_file)

    # Vérifie qu'on a bien tout téléchargé
    missing = EXPECTED_FILES - downloaded
    if missing:
        raise RuntimeError(f"Fichiers non trouvés dans le dataset : {missing}")

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