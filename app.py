import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

# ---------------------------------------------------
# CONFIGURATION PAGE (Style global & responsive)
# ---------------------------------------------------
st.set_page_config(
    page_title="PharmaIntelligence | Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------
# STYLE EMISSION PREMIUM (CSS Customisé et propre)
# ---------------------------------------------------
st.markdown("""
<style>
    /* Import de la police moderne Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Cartes KPI épurées et modernes */
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 22px 20px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02), 0 1px 2px rgba(0,0,0,0.04);
        transition: all 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-color: #3b82f6;
    }
    
    /* Boutons des Onglets */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        color: #64748b !important;
    }
    
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #3b82f6 !important;
        border-bottom-color: #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# ACCÈS & CHARGEMENT DES DONNÉES (Optimisé)
# ---------------------------------------------------
DB_PATH = Path(__file__).resolve().parent / "data" / "bdpm.db"

@st.cache_data(show_spinner="Analyse de la base de données en cours...")
def load_and_process_data():
    with sqlite3.connect(DB_PATH) as conn:
        cis_df   = pd.read_sql("SELECT * FROM medicaments",  conn)
        cip_df   = pd.read_sql("SELECT * FROM presentations", conn)
        compo_df = pd.read_sql("SELECT * FROM compositions",  conn)
        gener_df = pd.read_sql("SELECT * FROM generiques",   conn)
    
    # Pré-processing global pour éviter les calculs redondants
    df_main = cis_df.merge(cip_df, on="CIS", how="left")
    df_main["PRIX"] = pd.to_numeric(df_main["PRIX"], errors="coerce")
    
    return cis_df, cip_df, compo_df, gener_df, df_main

try:
    df_cis, df_cip, df_compo, df_gener, df = load_and_process_data()
except Exception as e:
    st.error(f"Erreur lors du chargement des données. Vérifiez l'emplacement du fichier BDD. Détails: {e}")
    st.stop()

# ---------------------------------------------------
# SIDEBAR MÉTADONNÉES
# ---------------------------------------------------
# ---------------------------------------------------
# SIDEBAR MÉTADONNÉES (Nettoyée et efficace)
# ---------------------------------------------------
meta_file = Path(__file__).resolve().parent / "data" / ".bdpm_meta.json"

st.sidebar.title("🧬 BDPM - Database v1.0")

if meta_file.exists():
    try:
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)
        st.sidebar.markdown("### 📊 État du système")
        st.sidebar.caption(f"**Source :** BDPM Officielle (ANSM)")
        st.sidebar.caption(f"**Version :** {meta.get('version', 'Inconnue')}")
    except:
        st.sidebar.warning("⚠️ Erreur de lecture des métadonnées")
else:
    st.sidebar.warning("⚠️ Métadonnées absolues introuvables")

st.sidebar.divider()
st.sidebar.caption("💡 Utilisez les onglets supérieurs pour naviguer entre les différentes analyses économiques et structurelles.")

# ---------------------------------------------------
# EN-TÊTE PRINCIPALE
# ---------------------------------------------------
st.title("📊 Analyse Statistique du Marché Pharmaceutique")
st.markdown("Pilotez et analysez les dynamiques de distribution, de concentration et de pricing du marché.")
st.write("")

# Configuration globale du design des graphiques Plotly
plotly_template = "plotly_white"

tabs = st.tabs([
    "📈 Vue Globale Marché",
    "🏭 Analyse Laboratoires",
    "🧪 Cartographie Molécules",
    "🧬 Pénétration Génériques",
    "💰 Ingénierie Économique"
])

# ===================================================
# 📈 ONGLET 1 : VUE GLOBALE MARCHÉ
# ===================================================
with tabs[0]:
    st.subheader("Indicateurs Clés de Performance (KPI)")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Spécialités (CIS)", f"{df_cis['CIS'].nunique():,}".replace(',', ' '))
    with col2:
        st.metric("📦 Présentations (CIP)", f"{df_cip['CIS'].count():,}".replace(',', ' '))
    with col3:
        st.metric("🧪 Substances Actives", f"{df_compo['SUBSTANCE'].nunique():,}".replace(',', ' '))
    with col4:
        st.metric("🏭 Acteurs (Laboratoires)", f"{df_cis['TITULAIRES'].nunique():,}".replace(',', ' '))

    st.markdown("---")
    
    left_col, right_col = st.columns([3, 2])
    
    df_lab = df_cis["TITULAIRES"].value_counts().reset_index()
    df_lab.columns = ["TITULAIRES", "NB"]
    
    with left_col:
        st.markdown("#### 🔝 Top 10 Laboratoires par volume de spécialités")
        fig_bar = px.bar(
            df_lab.head(10), x="NB", y="TITULAIRES", orientation='h',
            text_auto='.s', template=plotly_template,
            color="NB", color_continuous_scale="Blugrn"
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=450)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with right_col:
        st.markdown("#### 🪵 Répartition des Parts de Marché (Treemap)")
        # Graphique Treemap innovant pour voir le poids global visuellement
        fig_tree = px.treemap(
            df_lab.head(30), path=['TITULAIRES'], values='NB',
            template=plotly_template, color='NB', color_continuous_scale="Blues"
        )
        fig_tree.update_layout(margin=dict(t=10, b=10, r=10, l=10), height=450)
        st.plotly_chart(fig_tree, use_container_width=True)

    # Métrique de concentration basse
    top5 = df_lab.head(5)["NB"].sum()
    total = df_lab["NB"].sum()
    concentration = round((top5 / total) * 100, 1)
    st.info(f"💡 **Indice de captation :** Les 5 plus grands laboratoires contrôlent **{concentration}%** de l'offre de médicaments disponible.")

# ===================================================
# 🏭 ONGLET 2 : ANALYSE LABORATOIRES
# ===================================================
with tabs[1]:
    st.subheader("Analyse Croisée du Positionnement Stratégique")
    
    df_lab_price = df.groupby("TITULAIRES").agg(
        nb_produits=("CIS", "nunique"),
        prix_moyen=("PRIX", "mean"),
        prix_median=("PRIX", "median")
    ).reset_index().dropna()
    
    # Filtre dynamique pour éviter d'écraser le graphique avec les petits acteurs
    min_prod = st.slider("Filtrer par nombre minimal de produits commercialisés", 1, 100, 5)
    df_filtered_lab = df_lab_price[df_lab_price["nb_produits"] >= min_prod]
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("#### 🗺️ Matrice Volume vs Prix Moyen")
        fig_scatter = px.scatter(
            df_filtered_lab, x="nb_produits", y="prix_moyen",
            size="nb_produits", hover_name="TITULAIRES",
            log_x=True, template=plotly_template,
            labels={"nb_produits": "Nombre de produits (Échelle Log)", "prix_moyen": "Prix Moyen (€)"},
            color="prix_moyen", color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with col_g2:
        st.markdown("#### 📦 Dispersion des prix des Top Acteurs (Boxplot)")
        top_10_labs_names = df_lab.head(10)["TITULAIRES"].tolist()
        df_top_labs_data = df[df["TITULAIRES"].isin(top_10_labs_names)].dropna(subset=["PRIX"])
        
        # Boxplot pour comprendre la politique de prix réelle d'un acteur
        fig_box = px.box(
            df_top_labs_data, x="TITULAIRES", y="PRIX",
            color="TITULAIRES", template=plotly_template,
            points=False # Évite de saturer avec les outliers
        )
        fig_box.update_layout(showlegend=False, xaxis_tickangle=45, height=450)
        # Limiter l'axe Y pour une meilleure lisibilité si outliers extrêmes
        fig_box.update_yaxes(range=[0, df_top_labs_data["PRIX"].quantile(0.95)])
        st.plotly_chart(fig_box, use_container_width=True)

# ===================================================
# 🧪 ONGLET 3 : CARTOGRAPHIE MOLÉCULES
# ===================================================
with tabs[2]:
    st.subheader("Classement et Intensité Concurrentielle des Molécules")
    
    df_sub = df_compo["SUBSTANCE"].value_counts().reset_index()
    df_sub.columns = ["SUBSTANCE", "NB"]
    
    c1, c2 = st.columns([3, 1])
    
    with c1:
        fig_sub = px.bar(
            df_sub.head(15), x="NB", y="SUBSTANCE", orientation='h',
            text_auto=True, template=plotly_template,
            color="NB", color_continuous_scale="Purples"
        )
        fig_sub.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
        st.plotly_chart(fig_sub, use_container_width=True)
        
    with c2:
        st.write("")
        st.write("")
        intensite = round(df_sub["NB"].mean(), 1)
        st.metric("📈 Intensité concurrentielle moyenne", f"{intensite} g/m")
        st.caption("Nombre moyen d'occurrences ou de déclinaisons d'une même substance au sein du catalogue national.")
        
        st.markdown("---")
        st.markdown("**Note d'analyse :** Les molécules disposant du plus grand nombre d'occurrences désignent généralement les segments de marché matures ou fortement tombés dans le domaine public.")

# ===================================================
# 🧬 ONGLET 4 : PÉNÉTRATION & STATUTS GÉNÉRIQUES
# ===================================================
with tabs[3]:
    st.subheader("Analyse Approfondie de la Générification du Marché")
    
    if not df_gener.empty:
        # 1. Détection automatique de la colonne contenant les codes (0, 1, 2, 3, 4)
        statut_col = None
        for col_name in ["TYPE_GEN", "STATUT", "STATUT_CODE", "CODE_TYPE"]:
            if col_name in df_gener.columns:
                statut_col = col_name
                break
        
        if not statut_col:
            numeric_cols = df_gener.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                statut_col = numeric_cols[0]
            else:
                df_gener["STATUT_CODE"] = 1
                statut_col = "STATUT_CODE"

        # 2. Dictionnaire de correspondance complet des codes du répertoire
        mapping_statuts = {
            0: "👑 Princeps (Médicament de référence)",
            1: "🧬 Générique standard",
            2: "🧪 Générique biologique (Biosimilaire)",
            3: "💊 Générique assimilé / Équivalent",
            4: "🔄 Autre type de substitut économique"
        }
        
        # On convertit en numérique au cas où ce soit du texte pour éviter les échecs de mapping
        df_gener[statut_col] = pd.to_numeric(df_gener[statut_col], errors='coerce').fillna(1).astype(int)
        df_gener["Statut_Identifie"] = df_gener[statut_col].map(mapping_statuts).fillna(f"Code {df_gener[statut_col]}")

        # --- MISE EN PAGE DES MÉTRIQUES ---
        col_m1, col_m2, col_m3 = st.columns(3)
        
        col_cle_gen = "CIS_GEN" if "CIS_GEN" in df_gener.columns else ("CIS" if "CIS" in df_gener.columns else None)
        cis_avec_generique = df_gener[col_cle_gen].nunique() if col_cle_gen else df_gener.shape[0]
        cis_total = df_cis["CIS"].nunique() if not df_cis.empty else 1
        taux_gen = round((cis_avec_generique / cis_total) * 100, 1)
        
        col_m1.metric("🧬 Spécialités Générifiées", f"{cis_avec_generique:,}".replace(',', ' '))
        col_m2.metric("📈 Taux de Pénétration", f"{taux_gen} %")
        
        # Guide d'interprétation pour la bulle d'aide (help)
        legende_codes = (
            "Configuration des statuts du marché français :\n\n"
            "• Code 0 : Princeps (Molécule originale)\n"
            "• Code 1 : Générique standard\n"
            "• Code 2 : Biosimilaire (Biologique)\n"
            "• Code 3 : Générique assimilé / Équivalent\n"
            "• Code 4 : Autre substitut économique"
        )
        
        col_m3.metric(
            label="🗂️ Groupes Génériques", 
            value=f"{df_gener['DENOMINATION_GEN'].nunique():,}".replace(',', ' ') if "DENOMINATION_GEN" in df_gener.columns else "0",
            help=legende_codes
        )

        # Légende en texte brut sous les KPI pour éviter les crashs de balises HTML CSS
        st.caption("💡 Légende du répertoire : 0 = Princeps | 1 = Générique | 2 = Biosimilaire | 3 = Équivalent | 4 = Autre")
        st.divider()

        # --- GRAPHICS SECTION ---
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("#### 📊 Répartition des rôles dans le répertoire")
            df_status_count = df_gener["Statut_Identifie"].value_counts().reset_index()
            df_status_count.columns = ["Statut", "Nombre"]
            
            fig_statut = px.bar(
                df_status_count, x="Nombre", y="Statut", orientation='h',
                color="Statut", template=plotly_template,
                color_discrete_sequence=px.colors.sequential.Tealgrn_r
            )
            fig_statut.update_layout(showlegend=False, height=380, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_statut, use_container_width=True)
            
        with col_g2:
            st.markdown("#### 🍩 Top 10 des Groupes Génériques les plus denses")
            if "DENOMINATION_GEN" in df_gener.columns:
                df_gen_count = df_gener["DENOMINATION_GEN"].value_counts().reset_index()
                df_gen_count.columns = ["Groupes", "Nombre de spécialités"]
                
                fig_pie_gen = px.pie(
                    df_gen_count.head(10), names="Groupes", values="Nombre de spécialités",
                    hole=0.4, template=plotly_template,
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                fig_pie_gen.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_pie_gen, use_container_width=True)
            else:
                st.info("Données de dénominations indisponibles pour le graphique.")

        st.divider()

        # --- COUPLAGE ET IMPACT SUR LES PRIX ---
        st.markdown("#### 💰 Impact de la générification sur le niveau de Pricing")
        
        if "PRIX" in df.columns and col_cle_gen:
            # Duplication de sécurité pour éviter de modifier la source
            df_gener_sub = df_gener[[col_cle_gen, 'Statut_Identifie']].copy()
            df_gener_sub = df_gener_sub.rename(columns={col_cle_gen: "CIS"})
            
            # Merge et nettoyage immédiat
            df_prices_gen = df.merge(df_gener_sub, on="CIS", how="inner").dropna(subset=["PRIX"])
            
            if not df_prices_gen.empty:
                df_prix_moyen_statut = df_prices_gen.groupby("Statut_Identifie")["PRIX"].mean().reset_index()
                df_prix_moyen_statut.columns = ["Statut marché", "Prix Moyen (€)"]
                
                fig_compare_prix = px.bar(
                    df_prix_moyen_statut, x="Statut marché", y="Prix Moyen (€)",
                    color="Statut marché", template=plotly_template,
                    text_auto='.2f',
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_compare_prix.update_layout(showlegend=False, height=380)
                st.plotly_chart(fig_compare_prix, use_container_width=True)
            else:
                st.info("ℹ️ Les médicaments de cette section n'ont pas de prix valides associés dans la table principale pour générer le comparatif.")
        else:
            st.info("ℹ️ Données de prix insuffisantes pour calculer l'impact financier.")
            
    else:
        st.info("Pas de données génériques disponibles.")

# ===================================================
# 💰 ONGLET 5 : INGENIERIE ÉCONOMIQUE & MONOPÔLE
# ===================================================
with tabs[4]:
    st.subheader("Analyse des Prix et Santé Concurrentielle (Indice HHI)")
    
    # Nettoyage des prix pour l'analyse macro
    df_economique = df.dropna(subset=["PRIX"])
    
    col_e1, col_e2, col_e3 = st.columns(3)
    
    prix_moyen  = round(df_economique["PRIX"].mean(), 2)
    prix_mediane = round(df_economique["PRIX"].median(), 2)
    
    # Calcul HHI (Herfindahl-Hirschman Index)
    _df_lab = df_cis["TITULAIRES"].value_counts().reset_index()
    _df_lab.columns = ["TITULAIRES", "NB"]
    parts = _df_lab["NB"] / _df_lab["NB"].sum()
    hhi = round((parts ** 2).sum() * 10000, 0) # Normalisé entre 0 et 10 000
    
    col_e1.metric("💰 Prix Moyen d'un CIP", f"{prix_moyen} €")
    col_e2.metric("📊 Prix Médian d'un CIP", f"{prix_mediane} €")
    col_e3.metric("⚖️ Indice de Concentration HHI", f"{int(hhi)}")
    
    st.markdown("---")
    
    col_graph_inf1, col_graph_inf2 = st.columns(2)
    
    with col_graph_inf1:
        st.markdown("#### 📉 Courbe de Distribution Réelle des Prix")
        # Utilisation d'un histogramme avec courbe de distribution
        fig_hist = px.histogram(
            df_economique[df_economique["PRIX"] <= df_economique["PRIX"].quantile(0.95)], # On coupe les extrêmes (95ème percentile) pour zoomer sur la réalité du marché
            x="PRIX", nbins=60, template=plotly_template,
            marginal="rug", color_discrete_sequence=['#10b981']
        )
        fig_hist.update_layout(xaxis_title="Prix public (€)", yaxis_title="Volume de Références")
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with col_graph_inf2:
        st.markdown("#### 🧐 Interprétation Réglementaire HHI")
        
        if hhi < 1500:
            status_hhi = "🟢 **Marché Concurrentiel (Peu concentré)**"
            color_banner = "success"
            explication = "Le grand nombre d'acteurs de tailles similaires garantit une saine dynamique de concurrence sur les prix."
        elif 1500 <= hhi <= 2500:
            status_hhi = "🟡 **Marché Modérément Concentré**"
            color_banner = "warning"
            explication = "Une vigilance est de mise. Quelques leaders commencent à s'octroyer des barrières à l'entrée structurantes."
        else:
            status_hhi = "🔴 **Marché Fortement Concentré / Oligopole**"
            color_banner = "error"
            explication = "Le secteur est dominé par un groupe ultra-restreint de titulaires. Risque élevé de dépendance économique."
            
        st.info(f"L'indice de Herfindahl-Hirschman ({int(hhi)}) est la métrique de référence pour les autorités de la concurrence (ex: Commission Européenne).\n\n**Résultat :**\n{status_hhi}\n\n*{explication}*")