# <p align="center">💊 BDPM Database - Pipeline ETL & Analyse BDPM</p>

![Update BDPM](https://github.com/matthieugraziani/bdpm-database/actions/workflows/update_bdpm.yml/badge.svg)

Pipeline de traitement de données et application d'analyse construits à partir de la Base de Données Publique des Médicaments (BDPM).
Ce projet met en œuvre un processus complet d'ingestion, transformation et structuration de données pharmaceutiques dans une base SQLite optimisée pour l'analyse et la visualisation.

---

# 🎯 Objectif du projet

Concevoir un pipeline ETL robuste permettant d'ingérer, nettoyer, structurer et optimiser les données issues de la :

[Base de Données Publique des Médicaments (BDPM) – data.gouv.fr](https://www.data.gouv.fr/fr/datasets/base-de-donnees-publique-des-medicaments/)

Le projet vise à démontrer :
- Conception d'un pipeline de transformation de données
- Normalisation et standardisation de données hétérogènes
- Optimisation des performances via indexation SQL
- Structuration d'une base exploitable analytiquement
- Séparation claire des couches ingestion / transformation / stockage

---

# 🏗️ Architecture

```
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
├── tests/                      # Tests unitaires du pipeline ETL
├── files/                      # Fichiers BDPM source (.txt)
├── database.py                 # Pipeline ETL (PharmaDataPipeline)
├── app.py                      # Application Streamlit
├── bdpm.db                     # Base SQLite générée
├── requirements.txt
└── README.md
```

---

# 🗄️ Source des données

Données issues de la :

[Base de Données Publique des Médicaments (BDPM) – data.gouv.fr](https://www.data.gouv.fr/fr/datasets/base-de-donnees-publique-des-medicaments/)

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

Télécharger les fichiers `.txt` depuis [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/base-de-donnees-publique-des-medicaments/) et les placer dans le dossier `files/` :
```
files/
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