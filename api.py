# api.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Optional

app = FastAPI(
    title="BDPM Data API",
    description="API REST d'accès à la Base de Données Publique des Médicaments pour le projet MediTrack",
    version="1.0.0"
)

# Configuration CORS pour permettre à MediTrack d'appeler l'API depuis un autre domaine/port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production avec l'URL de MediTrack
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).resolve().parent / "data" / "bdpm.db"

def get_db_connection():
    """Garantit une connexion propre à la base SQLite."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Fichier de base de données bdpm.db introuvable.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permet de récupérer les résultats sous forme de dictionnaire
    return conn

# --- FONCTION COMPAGNON : MAPPING GÉOPOLITIQUE ---
def attribuer_pays(titulaire: str) -> dict:
    t = str(titulaire).lower()
    if any(k in t for k in ["sanofi", "biogaran", "servier", "pierre fabre", "ipsen", "guerbet", "france"]):
        return {"pays": "France", "iso": "FRA"}
    elif any(k in t for k in ["pfizer", "merck", "bristol", "lilly", "abbvie", "msd", "mylan", "viatris", "biogen"]):
        return {"pays": "États-Unis", "iso": "USA"}
    elif any(k in t for k in ["glaxosmithkline", "gsk", "astrazeneca", "hospira"]):
        return {"pays": "Royaume-Uni", "iso": "GBR"}
    elif any(k in t for k in ["bayer", "boehringer", "merck kgaa", "fresenius", "stada", "hexal"]):
        return {"pays": "Allemagne", "iso": "DEU"}
    elif any(k in t for k in ["novartis", "roche", "sandoz"]):
        return {"pays": "Suisse", "iso": "CHE"}
    elif "teva" in t:
        return {"pays": "Israël", "iso": "ISR"}
    elif any(k in t for k in ["takeda", "otsuka", "daiichi"]):
        return {"pays": "Japon", "iso": "JPN"}
    elif any(k in t for k in ["ranbaxy", "aurobindo", "cipla", "sun pharma"]):
        return {"pays": "Inde", "iso": "IND"}
    elif any(k in t for k in ["novo nordisk", "leo", "lundbeck"]):
        return {"pays": "Danemark", "iso": "DNK"}
    else:
        return {"pays": "Europe / Autre", "iso": "EUR"}


# ===================================================
# ENDPOINTS API (Points d'accès pour MediTrack)
# ===================================================

@app.get("/", tags=["Système"])
def read_root():
    return {"status": "online", "message": "API BDPM opérationnelle pour MediTrack"}


@app.get("/medicaments/search", tags=["Recherche"])
def search_medicaments(q: str = Query(..., description="Début ou partie du nom du médicament", min_length=2)):
    """Recherche globale de médicaments par dénomination (Auto-complétion pour MediTrack)."""
    conn = get_db_connection()
    try:
        # Recherche insensible à la casse
        query = "SELECT CIS, DENOMINATION, TITULAIRES FROM medicaments WHERE DENOMINATION LIKE ? LIMIT 50"
        df = pd.read_sql(query, conn, params=(f"%{q}%",))
        return df.to_dict(orient="records")
    finally:
        conn.close()


@app.get("/medicaments/{cis}", tags=["Fiche Produit"])
def get_medicament_details(cis: str):
    """Récupère la fiche d'identité complète d'un médicament (Spécialité + Présentations + Compositions)."""
    conn = get_db_connection()
    try:
        # 1. Infos de base
        med = conn.execute("SELECT * FROM medicaments WHERE CIS = ?", (cis,)).fetchone()
        if not med:
            raise HTTPException(status_code=404, detail="Médicament introuvable")
        
        med_dict = dict(med)
        
        # Ajout dynamique des données de provenance calculées
        provenance = attribuer_pays(med_dict.get("TITULAIRES", ""))
        med_dict["PAYS_ORIGINE"] = provenance["pays"]
        med_dict["PAYS_ISO"] = provenance["iso"]

        # 2. Récupération des présentations (Prix, CIP)
        pres = conn.execute("SELECT CIP, DESIGNATION, PRIX FROM presentations WHERE CIS = ?", (cis,)).fetchall()
        med_dict["PRESENTATIONS"] = [dict(p) for p in pres]

        # 3. Récupération des substances composantes
        compo = conn.execute("SELECT SUBSTANCE, DOSAGE FROM compositions WHERE CIS = ?", (cis,)).fetchall()
        med_dict["COMPOSITIONS"] = [dict(c) for c in compo]

        return med_dict
    finally:
        conn.close()


@app.get("/medicaments/{cis}/substituts", tags=["Optimisation Officine"])
def get_substituts(cis: str):
    """Moteur de substitution : Renvoie toutes les alternatives génériques ou équivalentes moins chères."""
    conn = get_db_connection()
    try:
        # Trouver d'abord les substances actives du produit cible
        substances_rows = conn.execute("SELECT SUBSTANCE FROM compositions WHERE CIS = ?", (cis,)).fetchall()
        substances = [row["SUBSTANCE"] for row in substances_rows]
        
        if not substances:
            return {"cis_origine": cis, "substances": [], "substituts": [], "message": "Aucune substance répertoriée"}

        # Trouver tous les médicaments équivalents ayant au moins une de ces substances
        placeholders = ",".join(["?"] * len(substances))
        query = f"""
            SELECT m.CIS, m.DENOMINATION, m.TITULAIRES, p.PRIX 
            FROM compositions c
            JOIN medicaments m ON c.CIS = m.CIS
            JOIN presentations p ON m.CIS = p.CIS
            WHERE c.SUBSTANCE IN ({placeholders}) AND m.CIS != ? AND p.PRIX IS NOT NULL
            ORDER BY p.PRIX ASC
        """
        params = substances + [cis]
        df_substituts = pd.read_sql(query, conn, params=params)
        
        # Supprimer les doublons potentiels (si plusieurs présentations) et sérialiser
        df_clean = df_substituts.drop_duplicates(subset=["CIS"]).sort_values("PRIX")
        
        return {
            "cis_origine": cis,
            "substances_actives": substances,
            "substituts_trouves": df_clean.to_dict(orient="records")
        }
    finally:
        conn.close()


@app.get("/analytics/provenance", tags=["Statistiques & Macro"])
def get_provenance_stats():
    """Génère l'agrégation géopolitique globale pour alimenter les graphiques/cartes de MediTrack."""
    conn = get_db_connection()
    try:
        # Chargement léger des axes nécessaires
        query = """
            SELECT m.CIS, m.TITULAIRES, p.PRIX 
            FROM medicaments m
            LEFT JOIN presentations p ON m.CIS = p.CIS
        """
        df = pd.read_sql(query, conn)
        df["PRIX"] = pd.to_numeric(df["PRIX"], errors="coerce")
        
        # Application du mapping des pays
        df_pays = df["TITULAIRES"].apply(attribuer_pays).apply(pd.Series)
        df["PAYS_ORIGINE"] = df_pays["pays"]
        df["PAYS_ISO"] = df_pays["iso"]
        
        # Agrégation statistique par pays
        df_geo = df.groupby(["PAYS_ORIGINE", "PAYS_ISO"]).agg(
            nb_medicaments=("CIS", "nunique"),
            prix_moyen_pays=("PRIX", "mean")
        ).reset_index()
        
        # Nettoyage des valeurs NaN pour éviter les erreurs JSON
        df_geo["prix_moyen_pays"] = df_geo["prix_moyen_pays"].fillna(0.0)
        
        return df_geo.to_dict(orient="records")
    finally:
        conn.close()