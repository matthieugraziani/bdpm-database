import json
import subprocess
from pathlib import Path

import requests

DATASET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/056b6732-cbaf-447f-9f20-e3b5f655919a"
)

META_FILE = Path(".bdpm_meta.json")
FILES_DIR = Path("data")
# Fichiers attendus par ton ETL
EXPECTED_FILES = {
    "CIS_bdpm.txt",
    "CIS_CIP_bdpm.txt",
    "CIS_COMPO_bdpm.txt",
    "CIS_CPD_bdpm.txt",
    "CIS_GENER_bdpm.txt",
}


def get_dataset():
    r = requests.get(DATASET_URL, timeout=30)
    r.raise_for_status()
    return r.json()


def get_remote_version(dataset):
    return dataset.get("last_update")


def get_local_version():
    if not META_FILE.exists():
        return None

    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("version")


def save_version(version):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": version}, f, indent=2)


def download_resources(dataset):
    FILES_DIR.mkdir(exist_ok=True)

    resources = dataset.get("resources", [])

    for resource in resources:
        url = resource.get("url")

        if not url:
            continue

        filename = resource.get("title", "")

        if filename not in EXPECTED_FILES:
            continue

        print(f"Téléchargement : {filename}")

        r = requests.get(url, timeout=300)
        r.raise_for_status()

        with open(FILES_DIR / filename, "wb") as f:
            f.write(r.content)


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