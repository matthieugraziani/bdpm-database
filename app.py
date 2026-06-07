import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
import json

# ---------------------------------------------------
# CONFIGURATION PAGE  (doit être le 1er appel Streamlit)
# ---------------------------------------------------
st.set_page_config(page_title="Analyse Marché Pharma", layout="wide")

# ---------------------------------------------------
# CONNEXION BDD  (context manager → fermeture garantie)
# ---------------------------------------------------
DB_PATH = Path(__file__).resolve().parent / "data" / "bdpm.db"

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_connection()

# ---------------------------------------------------
# CHARGEMENT DES DONNÉES
# ---------------------------------------------------
@st.cache_data
def load_data():
    cis_df   = pd.read_sql("SELECT * FROM medicaments",            conn)
    cip_df   = pd.read_sql("SELECT * FROM presentations",          conn)
    compo_df = pd.read_sql("SELECT * FROM compositions",           conn)
    gener_df = pd.read_sql("SELECT * FROM generiques",             conn)
    return cis_df, cip_df, compo_df, gener_df

df_cis, df_cip, df_compo, df_gener = load_data()

# Jointure principale + nettoyage prix
df = df_cis.merge(df_cip, on="CIS", how="left")
df["PRIX"] = pd.to_numeric(df["PRIX"], errors="coerce")

# ---------------------------------------------------
# SIDEBAR — version BDPM
# ---------------------------------------------------
meta_file = Path("data") / ".bdpm_meta.json"
if meta_file.exists():
    meta = json.loads(meta_file.read_text())
    st.sidebar.success(f"BDPM mise à jour : {meta['version']}")
    
with open("data/.bdpm_meta.json", encoding="utf-8") as f:
    meta = json.load(f)

st.sidebar.info(
    f"Dernière mise à jour : {meta['version']}"
)
# ---------------------------------------------------
# TITRE & STYLE
# ---------------------------------------------------
st.title("💊 Outil d'Analyse Marché Pharmaceutique")

st.markdown("""
<style>
/* Fond principal blanc */
.stApp {
    background: #FFFFFF;
    color: #1a1a2e;      /* texte sombre lisible — corrigé depuis #E63946 */
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #080a0e !important;
    border-right: 1px solid #1f2937;
}

/* Cartes Glassmorphism */
div[data-testid="stMetric"] {
    background: rgba(0, 0, 0, 0.03);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 12px;
    padding: 20px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

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

.stDataFrame {
    border: 1px solid #1f2937;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# ONGLETS
# ---------------------------------------------------
tabs = st.tabs([
    "📊 Vue Marché",
    "🏭 Laboratoires",
    "🧪 Molécules",
    "🧬 Génériques",
    "💰 Analyse Économique"
])

# ===================================================
# 📊 ONGLET 1 : VUE MARCHÉ
# ===================================================
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)

    total_medicaments  = df_cis["CIS"].nunique()
    total_presentations = df_cip["CIS"].count()
    total_substances   = df_compo["SUBSTANCE"].nunique()
    total_lab          = df_cis["TITULAIRES"].nunique()

    col1.metric("💊 Médicaments",    total_medicaments)
    col2.metric("📦 Présentations",  total_presentations)
    col3.metric("🧪 Substances",     total_substances)
    col4.metric("🏭 Laboratoires",   total_lab)

    st.divider()

    df_lab = df_cis["TITULAIRES"].value_counts().reset_index()
    df_lab.columns = ["TITULAIRES", "NB"]

    fig = px.bar(
        df_lab.head(10),
        x="TITULAIRES",
        y="NB",
        title="Top 10 Laboratoires",
    )
    st.plotly_chart(fig, width='stretch')   # corrigé : width='stretch' → use_container_width

    top5         = df_lab.head(5)["NB"].sum()
    total        = df_lab["NB"].sum()
    concentration = round((top5 / total) * 100, 1)
    st.metric("📊 Indice concentration (Top 5)", f"{concentration}%")

# ===================================================
# 🏭 ONGLET 2 : LABORATOIRES
# ===================================================
with tabs[1]:
    df_lab_price = df.groupby("TITULAIRES").agg(
        nb_produits=("CIS",  "nunique"),
        prix_moyen= ("PRIX", "mean")
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
# 🧪 ONGLET 3 : MOLÉCULES
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
# 🧬 ONGLET 4 : GÉNÉRIQUES
# ===================================================
with tabs[3]:
    if not df_gener.empty:
        # Comptage du nombre de médicaments par groupe générique
        df_gen_count = df_gener["DENOMINATION_GEN"].value_counts().reset_index()
        df_gen_count.columns = ["DENOMINATION_GEN", "NB"]

        fig = px.pie(
            df_gen_count.head(20),
            names="DENOMINATION_GEN",
            values="NB",
            title="Top 20 Groupes Génériques par Nombre de Spécialités"
        )
        st.plotly_chart(fig, width='stretch')

        # Taux de pénétration : part des médicaments appartenant à un groupe générique
        cis_avec_generique = df_gener["CIS_GEN"].nunique()
        cis_total          = df_cis["CIS"].nunique()
        taux_gen = round((cis_avec_generique / cis_total) * 100, 1) if cis_total > 0 else 0

        st.metric("🧬 Taux de pénétration générique", f"{taux_gen}%")
        st.caption(f"{cis_avec_generique} médicaments sur {cis_total} appartiennent à un groupe générique.")
    else:
        st.info("Pas de données génériques disponibles.")

# ===================================================
# 💰 ONGLET 5 : ANALYSE ÉCONOMIQUE
# ===================================================
with tabs[4]:
    prix_moyen  = round(df["PRIX"].mean(),   2)
    prix_mediane = round(df["PRIX"].median(), 2)

    col1, col2 = st.columns(2)
    col1.metric("💰 Prix moyen",   f"{prix_moyen} €")
    col2.metric("📊 Prix médian",  f"{prix_mediane} €")

    st.divider()

    fig = px.histogram(
        df,
        x="PRIX",
        nbins=50,
        title="Distribution des Prix"
    )
    st.plotly_chart(fig, width='stretch')

    # Indice HHI (df_lab calculé dans l'onglet 1 — recalcul local pour robustesse)
    _df_lab = df_cis["TITULAIRES"].value_counts().reset_index()
    _df_lab.columns = ["TITULAIRES", "NB"]
    parts = _df_lab["NB"] / _df_lab["NB"].sum()
    hhi   = round((parts ** 2).sum(), 3)
    st.metric("📊 Indice HHI (concentration marché)", hhi)
