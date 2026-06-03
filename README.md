# <p align="center">💊 BDPM Database - Pipeline ETL & Analyse BDPM</p>

![Update BDPM](https://github.com/matthieugraziani/bdpm-database/actions/workflows/update_bdpm.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Data Source](https://img.shields.io/badge/source-data.gouv.fr-blue)

Pipeline de traitement de données et application d'analyse construits à partir de la Base de Données Publique des Médicaments (BDPM).
Ce projet met en œuvre un processus complet d'ingestion, transformation et structuration de données pharmaceutiques dans une base SQLite optimisée pour l'analyse et la visualisation.

> 🔄 **Les données BDPM sont automatiquement mises à jour** via un pipeline CI/CD GitHub Actions — aucune intervention manuelle requise.

---

# 🎯 Objectif du projet

Concevoir un pipeline ETL robuste permettant d'ingérer, nettoyer, structurer et optimiser les données issues de la :

[Base de Données Publique des Médicaments (BDPM) – data.gouv.fr](https://www.data.gouv.fr/datasets/base-de-donnees-publique-des-medicaments-base-officielle)

Le projet vise à démontrer :
- Conception d'un pipeline de transformation de données
- Normalisation et standardisation de données hétérogènes
- Optimisation des performances via indexation SQL
- Structuration d'une base exploitable analytiquement
- Séparation claire des couches ingestion / transformation / stockage

---

# 🔄 Mise à jour automatique des données (Auto-Update)

Le projet intègre un pipeline de mise à jour automatique du dataset BDPM, orchestré via **GitHub Actions**.

### ⚙️ Fonctionnement

```
GitHub Actions (cron / manuel)
        │
        ▼
update_bdpm.py          ← télécharge les fichiers BDPM depuis data.gouv.fr
        │
        ▼
data/*.txt              ← fichiers source mis à jour
        │
        ▼
database.py             ← régénère bdpm.db via le pipeline ETL
        │
        ▼
bdpm.db                 ← base SQLite à jour, commitée dans le repo
```

### 📅 Déclenchement

| Mode | Détail |
|------|--------|
| ⏰ Planifié | Exécution automatique (ex. hebdomadaire via `cron`) |
| ▶️ Manuel | Déclenchable depuis l'onglet **Actions** de GitHub (`workflow_dispatch`) |

### 📄 Fichier de workflow : `.github/workflows/update_bdpm.yml`

```yaml
name: Update BDPM

on:
  schedule:
    - cron: "0 3 * * 1"   # Chaque lundi à 3h UTC
  workflow_dispatch:        # Déclenchement manuel possible

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt
      - run: python update_bdpm.py      # Télécharge les fichiers BDPM
      - run: python database.py         # Régénère bdpm.db
      - name: Commit & Push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/ bdpm.db
          git commit -m "chore: update BDPM dataset $(date +'%Y-%m-%d')" || echo "No changes"
          git push
```

### 📥 Script de téléchargement : `update_bdpm.py`

Le script `update_bdpm.py` interroge l'API de **data.gouv.fr** pour récupérer les derniers fichiers BDPM disponibles et les place dans le dossier `data/` :

- `CIS_bdpm.txt` — Médicaments
- `CIS_CIP_bdpm.txt` — Présentations commerciales
- `CIS_COMPO_bdpm.txt` — Compositions / substances actives
- `CIS_CPD_bdpm.txt` — Conditions de prescription
- `CIS_GENER_bdpm.txt` — Relations génériques

> ℹ️ En cas d'échec du téléchargement (réseau, indisponibilité API), le pipeline conserve les fichiers existants et logue une erreur sans écraser la base précédente (écriture atomique via `bdpm.db.tmp`).

---

# 🏗️ Architecture

```
GitHub Actions (cron / workflow_dispatch)
        │
        ▼
update_bdpm.py          ← téléchargement automatique depuis data.gouv.fr
        │
        ▼
Fichiers BDPM (.txt)
        │
        ▼
Pipeline ETL (PharmaDataPipeline)
        │
        ▼
Base SQLite (bdpm.db)       ← écriture atomique via bdpm.db.tmp
        │
        ▼
Application Web (Streamlit)
```

---

# 📁 Structure du projet

```
bdpm-database/
├── .github/
│   └── workflows/
│       └── update_bdpm.yml     # CI/CD : mise à jour automatique BDPM
│       └── python-app.yml      # CI/CD : test .py
├── tests/                      # Tests unitaires du pipeline ETL
├── data/                       # Fichiers BDPM source (.txt)            
├── database.py                 # Pipeline ETL (PharmaDataPipeline)
├── update_bdpm.py              # Téléchargement automatique des fichiers BDPM (data.gouv.fr)
├── app.py                      # Application Streamlit
├── bdpm.db                     # Base SQLite générée
├── requirements.txt
└── README.md
```

---

# 🗄️ Source des données

Données issues de la :

[Base de Données Publique des Médicaments (BDPM) – data.gouv.fr](https://www.data.gouv.fr/datasets/base-de-donnees-publique-des-medicaments-base-officielle)

> 🔄 Les fichiers sont **téléchargés et mis à jour automatiquement** via `update_bdpm.py` et le workflow GitHub Actions `update_bdpm.yml`.

La base comprend notamment :
- Médicaments (CIS)
- Présentations commerciales (CIP, prix, remboursement)
- Substances actives
- Conditions de prescription
- Relations génériques

---

# 🔄 Pipeline ETL

Implémenté dans `database.py` via la classe `PharmaDataPipeline`.

### ✔ Nettoyage des données
- Normalisation Unicode (NFKD)
- Suppression des accents
- Mise en majuscules
- Suppression des espaces parasites
- Normalisation appliquée **uniquement aux colonnes textuelles** (les colonnes numériques `PRIX`, `REMBOURSEMENT`, `CIS`, dates ne sont pas altérées)

### ✔ Conversion des types
- Conversion des prix en `float` (remplacement virgule → point)
- Extraction des taux de remboursement en numérique
- Gestion des valeurs invalides (`NaN`)

### ✔ Écriture atomique
Le pipeline écrit dans un fichier temporaire `bdpm.db.tmp` et ne remplace `bdpm.db` qu'une fois l'exécution complète.
En cas d'erreur à mi-chemin, la base précédente est préservée.

### ✔ Optimisation des performances

Index SQL créés automatiquement sur :
- `medicaments(CIS)`
- `presentations(CIS)`
- `presentations(CIP13)`
- `compositions(SUBSTANCE)`
- `conditions_prescription(CIS)`
- `generiques(CIS_GEN)`

---

# 🚀 Installation

**1️⃣ Cloner le projet**
```bash
git clone https://github.com/matthieugraziani/bdpm-database.git
cd bdpm-database
```

**2️⃣ Créer un environnement virtuel**
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Mac / Linux
python3 -m venv .venv
source .venv/bin/activate
```

**3️⃣ Installer les dépendances**
```bash
pip install -r requirements.txt
```

**4️⃣ Placer les fichiers BDPM**

Télécharger les fichiers `.txt` depuis [data.gouv.fr](https://www.data.gouv.fr/datasets/base-de-donnees-publique-des-medicaments-base-officielle) et les placer dans le dossier `data/` :
```
data/
├── CIS_bdpm.txt
├── CIS_CIP_bdpm.txt
├── CIS_COMPO_bdpm.txt
├── CIS_CPD_bdpm.txt
└── CIS_GENER_bdpm.txt
```

---

# ▶️ Exécution

**Générer la base SQLite :**
```bash
python database.py
```
Cela génère `bdpm.db` et affiche un résumé des lignes insérées par table.

**Lancer l'application web :**
```bash
streamlit run app.py
```

---

# 📦 Dépendances principales

| Librairie | Usage |
|-----------|-------|
| `pandas` | Chargement et transformation des fichiers BDPM |
| `sqlite3` | Stockage et interrogation de la base |
| `tqdm` | Barre de progression pendant l'ETL |
| `unicodedata` | Normalisation Unicode / suppression accents |
| `plotly` | Visualisations interactives |
| `streamlit` | Application web d'analyse |

---

# 🧹 Transformations appliquées

### Normalisation texte (colonnes textuelles uniquement)
- Suppression des accents (NFKD)
- Trim des espaces
- Conversion en majuscules

### Table `presentations`
- Conversion des prix en `float` (virgule → point, extraction regex)
- Conversion du remboursement en numérique

### Index SQL créés
- `idx_cis_med` → `medicaments(CIS)`
- `idx_cis_pres` → `presentations(CIS)`
- `idx_cip_pres` → `presentations(CIP13)`
- `idx_substance` → `compositions(SUBSTANCE)`
- `idx_cpd` → `conditions_prescription(CIS)`
- `idx_gener` → `generiques(CIS_GEN)`

---

# 📊 Application Streamlit

L'application propose 5 onglets d'analyse :

| Onglet | Contenu |
|--------|---------|
| 📊 Vue Marché | KPIs globaux, top 10 laboratoires, indice de concentration |
| 🏭 Laboratoires | Positionnement volume vs prix (scatter plot) |
| 🧪 Molécules | Top 10 substances actives |
| 🧬 Génériques | Répartition des groupes génériques, taux de pénétration |
| 💰 Analyse Économique | Distribution des prix, prix moyen/médian, indice HHI |

Les données sont mises en cache (`@st.cache_data`) pour des performances optimales.

---

# 🔍 Exemple de requête SQL

```sql
SELECT m.DENOMINATION, p.PRIX
FROM medicaments m
JOIN presentations p ON m.CIS = p.CIS
WHERE p.PRIX IS NOT NULL
ORDER BY p.PRIX DESC;
```

---

# 🛠️ Améliorations possibles

- Ajout d'une API REST (FastAPI)
- Déploiement Docker
- Recherche plein texte SQLite (FTS5)
- Dashboard interactif avancé
- Migration vers DuckDB pour de meilleures performances analytiques
- Tests unitaires supplémentaires sur les transformations ETL

---

# 📄 Licence

Projet académique / personnel — [MIT License](LICENSE.txt)