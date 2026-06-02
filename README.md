# <p align="center">💊 BDPM Database - Pipeline ETL & Analyse BDPM</p>

![Update BDPM](https://github.com/matthieugraziani/bdpm-database/actions/workflows/update_bdpm.yml/badge.svg)


Pipeline de traitement de données et application d’analyse construits à partir de la Base de Données Publique des Médicaments (BDPM).
Ce projet met en œuvre un processus complet d’ingestion, transformation et structuration de données pharmaceutiques dans une base SQLite optimisée pour l’analyse et la visualisation.

# 🎯 Objectif du projet

Concevoir un pipeline ETL robuste permettant d’ingérer, nettoyer, structurer et optimiser les données issues de la :

[Base de Données Publique des Médicaments (BDPM) – data.gouv.fr](https://www.data.gouv.fr/fr/datasets/base-de-donnees-publique-des-medicaments/)


Le projet vise à démontrer :
- Conception d’un pipeline de transformation de données
- Normalisation et standardisation de données hétérogènes
- Optimisation des performances via indexation SQL
- Structuration d’une base exploitable analytiquement
- Séparation claire des couches ingestion / transformation / stockage

# 🏗️ Architecture
```bash
Fichiers BDPM (.txt)
        │
        ▼
Pipeline ETL (PharmaDataPipeline)
        │
        ▼
Base SQLite (bdpm.db)
        │
        ▼
Application Web (Streamlit)
```
# 📁 Structure du projet
````bash
data/
├── files/                  # Fichiers BDPM source
├── database.py             # Pipeline de traitement BDPM
├── bdpm.db                 # Base SQLite générée
├── app.py                  # Application principale
├── requirements.txt
└── README.md
````
# 🗄️ Source des données

Données issues de la :

[Base de Données Publique des Médicaments (BDPM) – data.gouv.fr](https://www.data.gouv.fr/fr/datasets/base-de-donnees-publique-des-medicaments/)

La base comprend notamment :
- Médicaments (CIS)
- Présentations commerciales (CIP, prix, remboursement)
- Substances actives
- Conditions de prescription
- Relations génériques

# 🔄 Pipeline ETL

Implémenté dans database.py via la classe PharmaDataPipeline.

✔ Nettoyage des données
- Normalisation Unicode
- Suppression des accents
- Mise en majuscules
- Suppression des espaces parasites

✔ Conversion des types
- Conversion des prix en float
- Extraction des taux de remboursement
- Gestion des valeurs invalides (NaN)

✔ Optimisation des performances

Index SQL créés automatiquement sur :
- medicaments(CIS)
- presentations(CIS)
- compositions(SUBSTANCE)
  
# 🚀 Installation
1️⃣ Cloner le projet
```bash
git clone https://github.com/ton-repo/Bdpm-Database.git
cd Bdpm-Database
```
2️⃣ Créer un environnement virtuel
```bash
Windows
python -m venv .venv
.venv\Scripts\activate

Mac / Linux
python3 -m venv .venv
source .venv/bin/activate
```
3️⃣ Installer les dépendances
```bash
pip install -r requirements.txt
```
▶️ Exécution
```bash
python database.py
```
Cela génère : bdpm.db

# 📦 Dépendances principales

- pandas
- sqlite3
- tqdm
- plotly
- unicodedata
- streamlit (si app web)

# 🧹 Transformations appliquées
✔ Normalisation texte
- Suppression des accents
- Trim des espaces
- Conversion en majuscules

✔ Table presentations
- Conversion des prix en float
- Conversion remboursement en numérique

✔ Index SQL créés
- index sur medicaments(CIS)
- index sur presentations(CIP)
- index sur compositions(COMPO)
- index sur conditions prescriptions(CPD)
- index sur génériques(GENER)



# 🔍 Exemple de requête SQL
```bash
SELECT m.DENOMINATION, p.PRIX
FROM medicaments m
JOIN presentations p ON m.CIS = p.CIS
WHERE p.PRIX IS NOT NULL
ORDER BY p.PRIX DESC;
```

# 📊 Lancer l’application web (si Streamlit)
```bash
streamlit run app.py
```

# 🛠️ Améliorations possibles

- Ajout d’API REST (FastAPI)
- Déploiement Docker
- Recherche plein texte SQLite
- Dashboard interactif avancé
- Caching des requêtes lourdes

# 📄 Licence

Projet académique / personnel.