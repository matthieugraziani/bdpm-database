import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
import json

meta_file = Path(".bdpm_meta.json")

if meta_file.exists():
    meta = json.loads(meta_file.read_text())

    st.sidebar.success(
        f"BDPM mise à jour : {meta['version']}"
    )

st.metric(
    "Médicaments",
    stats["medicaments"]
)
# ---------------------------------------------------
# CONFIGURATION PAGE
# ---------------------------------------------------
st.set_page_config(page_title="Analyse Marché Pharma", layout="wide")

st.title("💊 Outil d’Analyse Marché Pharmaceutique")

st.markdown("""
    <style>
    /* Fond principal Deep Night */
    .stApp {
        background: #FFFFFF;
        color: #E63946;
    }
    
    /* Sidebar style */
    [data-testid="stSidebar"] {
        background-color: #080a0e !important;
        border-right: 1px solid #1f2937;
    }

    /* Cartes Glassmorphism */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    
    /* Glow effect au survol */
    div[data-testid="stMetric"]:hover {
        border: 1px solid #4facfe;
        box-shadow: 0 0 15px rgba(79, 172, 254, 0.2);
    }

    /* Titres en dégradé */
    .premium-title {
        background: linear-gradient(90deg, #4facfe, #00f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
    }

    /* Personnalisation des tableaux */
    .stDataFrame {
        border: 1px solid #1f2937;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# CONNEXION BDD
# ---------------------------------------------------
DB_PATH = Path(__file__).resolve().parent / "bdpm.db"
conn = sqlite3.connect(DB_PATH)

# Chargement des tables principales
df_cis = pd.read_sql("SELECT * FROM medicaments", conn)
df_cip = pd.read_sql("SELECT * FROM presentations", conn)
df_compo = pd.read_sql("SELECT * FROM compositions", conn)
df_gener = pd.read_sql("SELECT * FROM generiques", conn)

# Jointure principale
df = df_cis.merge(df_cip, on="CIS", how="left")

# Nettoyage prix
df["PRIX"] = pd.to_numeric(df["PRIX"], errors="coerce")

# ---------------------------------------------------
# ONGLET NAVIGATION
# ---------------------------------------------------
tabs = st.tabs([
    "📊 Vue Marché",
    "🏭 Laboratoires",
    "🧪 Molécules",
    "🧬 Génériques",
    "💰 Analyse Économique"
])

# ===================================================
# 📊 ONGLET 1 : VUE MARCHE
# ===================================================
with tabs[0]:

    col1, col2, col3, col4 = st.columns(4)

    total_medicaments = df_cis["CIS"].nunique()
    total_presentations = df_cip["CIS"].count()
    total_substances = df_compo["SUBSTANCE"].nunique()
    total_lab = df_cis["TITULAIRES"].nunique()

    col1.metric("💊 Médicaments", total_medicaments)
    col2.metric("📦 Présentations", total_presentations)
    col3.metric("🧪 Substances", total_substances)
    col4.metric("🏭 Laboratoires", total_lab)

    st.divider()

    # Part de marché laboratoires
    df_lab = df_cis["TITULAIRES"].value_counts().reset_index()
    df_lab.columns = ["TITULAIRES", "NB"]

    fig = px.bar(
        df_lab.head(10),
        x="TITULAIRES",
        y="NB",
        title="Top 10 Laboratoires",
    )
    st.plotly_chart(fig, width='stretch')

    # Indice de concentration
    top5 = df_lab.head(5)["NB"].sum()
    total = df_lab["NB"].sum()
    concentration = round((top5 / total) * 100, 1)

    st.metric("📊 Indice concentration (Top 5)", f"{concentration}%")

# ===================================================
# 🏭 ONGLET 2 : LABORATOIRES
# ===================================================
with tabs[1]:

    df_lab_price = df.groupby("TITULAIRES").agg(
        nb_produits=("CIS", "nunique"),
        prix_moyen=("PRIX", "mean")
    ).reset_index()

    fig = px.scatter(
        df_lab_price,
        x="nb_produits",
        y="prix_moyen",
        size="nb_produits",
        hover_name="TITULAIRES",
        title="Positionnement Laboratoires (Volume vs Prix)"
    )

    st.plotly_chart(fig, width='stretch')

# ===================================================
# 🧪 ONGLET 3 : MOLECULES
# ===================================================
with tabs[2]:

    df_sub = df_compo["SUBSTANCE"].value_counts().reset_index()
    df_sub.columns = ["SUBSTANCE", "NB"]

    fig = px.bar(
        df_sub.head(10),
        x="SUBSTANCE",
        y="NB",
        title="Top 10 Substances Actives"
    )

    st.plotly_chart(fig, width='stretch')

    intensite = round(df_sub["NB"].mean(), 1)
    st.metric("📈 Intensité concurrentielle moyenne", intensite)

# ===================================================
# 🧬 ONGLET 4 : GENERIQUES
# ===================================================
with tabs[3]:

    if not df_gener.empty:
        df_gen = df_gener["DENOMINATION_GEN"].value_counts().reset_index()
        df_gen.columns = ["TYPE", "NB"]

        fig = px.pie(
            df_gen,
            names="TYPE",
            values="NB",
            title="Répartition Génériques vs Princeps"
        )

        st.plotly_chart(fig, width='stretch')

        taux_gen = round((df_gen[df_gen["TYPE"] == "GENERIC"]["NB"].sum() / df_gen["NB"].sum()) * 100, 1) if "GENERIC" in df_gen["TYPE"].values else 0

        st.metric("🧬 Taux de pénétration générique", f"{taux_gen}%")
    else:
        st.info("Pas de données génériques disponibles")

# ===================================================
# 💰 ONGLET 5 : ANALYSE ECONOMIQUE
# ===================================================
with tabs[4]:

    prix_moyen = round(df["PRIX"].mean(), 2)
    prix_mediane = round(df["PRIX"].median(), 2)

    col1, col2 = st.columns(2)
    col1.metric("💰 Prix moyen", f"{prix_moyen} €")
    col2.metric("📊 Prix médian", f"{prix_mediane} €")

    st.divider()

    fig = px.histogram(
        df,
        x="PRIX",
        nbins=50,
        title="Distribution des Prix"
    )

    st.plotly_chart(fig, width='stretch')

    # HHI
    parts = df_lab["NB"] / df_lab["NB"].sum()
    hhi = round((parts ** 2).sum(), 3)

    st.metric("📊 Indice HHI (concentration marché)", hhi)

conn.close()
