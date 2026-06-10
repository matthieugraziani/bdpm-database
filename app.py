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
    page_title="BDPM-Database | Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------
# STYLE PREMIUM (CSS Customisé, moderne et propre)
# ---------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
    }
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
# ACCÈS & CHARGEMENT DES DONNÉES (Auto-adaptatif)
# ---------------------------------------------------
DB_PATH = Path(__file__).resolve().parent / "data" / "bdpm.db"

@st.cache_data(show_spinner="Analyse et indexation de la base de données...")
def load_and_process_data():
    with sqlite3.connect(DB_PATH) as conn:
        # 1. On liste les tables réellement existantes dans le fichier SQLITE
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables_existantes = [row[0] for row in cursor.fetchall()]
        
        # Si la base est totalement vide
        if not tables_existantes:
            raise ValueError("La base de données bdpm.db ne contient aucune table. Vérifiez son initialisation.")
            
        # 2. Système de détection de correspondance des tables (fallback si noms officiels ANSM)
        table_cis = "medicaments" if "medicaments" in tables_existantes else next((t for t in tables_existantes if "cis" in t.lower() and "cip" not in t.lower() and "gener" not in t.lower() and "compo" not in t.lower()), tables_existantes[0])
        table_cip = "presentations" if "presentations" in tables_existantes else next((t for t in tables_existantes if "cip" in t.lower()), tables_existantes[0])
        table_compo = "compositions" if "compositions" in tables_existantes else next((t for t in tables_existantes if "compo" in t.lower()), tables_existantes[0])
        table_gener = "generiques" if "generiques" in tables_existantes else next((t for t in tables_existantes if "gener" in t.lower()), tables_existantes[0])
        
        # 3. Chargement dynamique
        cis_df   = pd.read_sql(f"SELECT * FROM {table_cis}",  conn)
        cip_df   = pd.read_sql(f"SELECT * FROM {table_cip}",  conn)
        compo_df = pd.read_sql(f"SELECT * FROM {table_compo}", conn)
        gener_df = pd.read_sql(f"SELECT * FROM {table_gener}", conn)
    
    # 4. Standardisation des colonnes au cas où elles soient en minuscules ou possèdent des suffixes
    for df_tmp in [cis_df, cip_df, compo_df, gener_df]:
        df_tmp.columns = [c.upper() for c in df_tmp.columns]
        
    # Renommer les colonnes clés si variantes constatées (ex: CODE_CIS -> CIS)
    for target_df in [cis_df, cip_df, compo_df, gener_df]:
        for col in target_df.columns:
            if "CIS" in col and col != "CIS" and "GEN" not in col:
                target_df.rename(columns={col: "CIS"}, inplace=True)
            if "TITULAIRE" in col:
                target_df.rename(columns={col: "TITULAIRES"}, inplace=True)
            if "SUBSTANCE" in col:
                target_df.rename(columns={col: "SUBSTANCE"}, inplace=True)
            if "DESIGNATION" in col or "NOM" in col:
                target_df.rename(columns={col: "DENOMINATION"}, inplace=True)
    
    # Jointure principale et typage
    df_main = cis_df.merge(cip_df, on="CIS", how="left")
    
    if "PRIX" in df_main.columns:
        df_main["PRIX"] = pd.to_numeric(df_main["PRIX"], errors="coerce")
    else:
        # Si la colonne prix s'appelle autrement (ex: PRIX_EURO, TARIF...)
        col_prix = next((c for c in df_main.columns if "PRIX" in c or "TARIF" in c), None)
        if col_prix:
            df_main["PRIX"] = pd.to_numeric(df_main[col_prix], errors="coerce")
        else:
            df_main["PRIX"] = 0.0 # Fallback si pas de prix
            
    # NLP / Extraction textuelle des Formes Galéniques majeures
    col_denom = "DENOMINATION" if "DENOMINATION" in df_main.columns else df_main.columns[1]
    def extraire_forme(text):
        text = str(text).lower()
        if "comprim" in text: return "💊 Comprimé"
        elif "gélule" in text or "gelule" in text: return "📦 Gélule"
        elif "inject" in text or "ampoule" in text or "perfusion" in text: return "💉 Injectable"
        elif "sirop" in text or "solub" in text or "buvabl" in text: return "🧪 Solution Orale"
        elif "crème" in text or "creme" in text or "pommade" in text: return "🧴 Pommade / Crème"
        else: return "🧩 Autre forme"
        
    df_main["FORME_CATEGORIE"] = df_main[col_denom].apply(extraire_forme)
    
    return cis_df, cip_df, compo_df, gener_df, df_main

try:
    df_cis, df_cip, df_compo, df_gener, df = load_and_process_data()
except Exception as e:
    st.error(f"❌ Impossible de charger les données : {e}")
    st.info("💡 Suggestions : Vérifiez que votre script de parsing a bien rempli le fichier 'data/bdpm.db' avec des tables valides.")
    st.stop()

# ---------------------------------------------------
# SIDEBAR MÉTADONNÉES
# ---------------------------------------------------
meta_file = Path(__file__).resolve().parent / "data" / ".bdpm_meta.json"
st.sidebar.title("🧬 BDPM-DatabaseV1.0")

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

plotly_template = "plotly_white"

tabs = st.tabs([
    "📈 Vue Globale Marché",
    "🏭 Analyse Laboratoires",
    "🧪 Cartographie Molécules",
    "🧬 Pénétration Génériques",
    "💰 Ingénierie Économique",
    "🛠️ Outils Décisionnels & Deep-Dive"
])

# ===================================================
# 📈 ONGLET 1 : VUE GLOBALE MARCHÉ
# ===================================================
with tabs[0]:
    st.subheader("Indicateurs Clés de Performance (KPI)")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("📦 Spécialités (CIS)", f"{df_cis['CIS'].nunique():,}".replace(',', ' '))
    with col2: st.metric("📦 Présentations (CIP)", f"{df_cip['CIS'].count():,}".replace(',', ' '))
    with col3: st.metric("🧪 Substances Actives", f"{df_compo['SUBSTANCE'].nunique():,}".replace(',', ' '))
    with col4: st.metric("🏭 Acteurs (Laboratoires)", f"{df_cis['TITULAIRES'].nunique():,}".replace(',', ' '))

    st.divider()
    left_col, right_col = st.columns([3, 2])
    df_lab = df_cis["TITULAIRES"].value_counts().reset_index()
    df_lab.columns = ["TITULAIRES", "NB"]
    
    with left_col:
        st.markdown("#### 🔝 Top 10 Laboratoires par volume de spécialités")
        fig_bar = px.bar(df_lab.head(10), x="NB", y="TITULAIRES", orientation='h', text_auto='.s', template=plotly_template, color="NB", color_continuous_scale="Blugrn")
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=450)
        st.plotly_chart(fig_bar, width='stretch')
        
    with right_col:
        st.markdown("#### 🪵 Répartition des Parts de Marché (Treemap)")
        fig_tree = px.treemap(df_lab.head(30), path=['TITULAIRES'], values='NB', template=plotly_template, color='NB', color_continuous_scale="Blues")
        fig_tree.update_layout(margin=dict(t=10, b=10, r=10, l=10), height=450)
        st.plotly_chart(fig_tree, width='stretch')

# ===================================================
# 🏭 ONGLET 2 : ANALYSE LABORATOIRES
# ===================================================
with tabs[1]:
    st.subheader("Analyse Croisée du Positionnement Stratégique")
    df_lab_price = df.groupby("TITULAIRES").agg(nb_produits=("CIS", "nunique"), prix_moyen=("PRIX", "mean")).reset_index().dropna()
    min_prod = st.slider("Filtrer par nombre minimal de produits commercialisés", 1, 100, 5)
    df_filtered_lab = df_lab_price[df_lab_price["nb_produits"] >= min_prod]
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### 🗺️ Matrice Volume vs Prix Moyen")
        fig_scatter = px.scatter(df_filtered_lab, x="nb_produits", y="prix_moyen", size="nb_produits", hover_name="TITULAIRES", log_x=True, template=plotly_template, color="prix_moyen", color_continuous_scale="Viridis")
        st.plotly_chart(fig_scatter, width='stretch')
    with col_g2:
        st.markdown("#### 📦 Dispersion des prix des Top Acteurs (Boxplot)")
        top_10_labs_names = df_lab.head(10)["TITULAIRES"].tolist()
        df_top_labs_data = df[df["TITULAIRES"].isin(top_10_labs_names)].dropna(subset=["PRIX"])
        fig_box = px.box(df_top_labs_data, x="TITULAIRES", y="PRIX", color="TITULAIRES", template=plotly_template, points=False)
        fig_box.update_layout(showlegend=False, xaxis_tickangle=45, height=450)
        fig_box.update_yaxes(range=[0, df_top_labs_data["PRIX"].quantile(0.95)])
        st.plotly_chart(fig_box, width='stretch')

# ===================================================
# 🧪 ONGLET 3 : CARTOGRAPHIE MOLÉCULES
# ===================================================
with tabs[2]:
    st.subheader("Classement et Intensité Concurrentielle des Molécules")
    df_sub = df_compo["SUBSTANCE"].value_counts().reset_index()
    df_sub.columns = ["SUBSTANCE", "NB"]
    c1, c2 = st.columns([3, 1])
    with c1:
        fig_sub = px.bar(df_sub.head(15), x="NB", y="SUBSTANCE", orientation='h', text_auto=True, template=plotly_template, color="NB", color_continuous_scale="Purples")
        fig_sub.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
        st.plotly_chart(fig_sub, width='stretch')
    with c2:
        st.metric("📈 Intensité concurrentielle moyenne", f"{round(df_sub['NB'].mean(), 1)} g/m")
        st.caption("Nombre moyen de déclinaisons d'une même substance au sein du catalogue national.")

# ===================================================
# 🧬 ONGLET 4 : PÉNÉTRATION & STATUTS GÉNÉRIQUES
# ===================================================
with tabs[3]:
    st.subheader("Analyse Approfondie de la Générification du Marché")
    if not df_gener.empty:
        statut_col = next((c for c in ["TYPE_GEN", "STATUT", "STATUT_CODE", "CODE_TYPE"] if c in df_gener.columns), None)
        if not statut_col:
            numeric_cols = df_gener.select_dtypes(include=['number']).columns
            statut_col = numeric_cols[0] if len(numeric_cols) > 0 else "STATUT_CODE"
            if statut_col == "STATUT_CODE": df_gener["STATUT_CODE"] = 1

        mapping_statuts = {
            0: "👑 Princeps (Médicament de référence)",
            1: "🧬 Générique standard",
            2: "🧪 Générique biologique (Biosimilaire)",
            3: "💊 Générique assimilé / Équivalent",
            4: "🔄 Autre type de substitut économique"
        }
        df_gener[statut_col] = pd.to_numeric(df_gener[statut_col], errors='coerce').fillna(1).astype(int)
        df_gener["Statut_Identifie"] = df_gener[statut_col].map(mapping_statuts).fillna(f"Code {df_gener[statut_col]}")

        col_m1, col_m2, col_m3 = st.columns(3)
        col_cle_gen = "CIS_GEN" if "CIS_GEN" in df_gener.columns else ("CIS" if "CIS" in df_gener.columns else None)
        cis_avec_generique = df_gener[col_cle_gen].nunique() if col_cle_gen else df_gener.shape[0]
        taux_gen = round((cis_avec_generique / df_cis["CIS"].nunique()) * 100, 1) if not df_cis.empty else 0
        
        col_m1.metric("🧬 Spécialités Générifiées", f"{cis_avec_generique:,}".replace(',', ' '))
        col_m2.metric("📈 Taux de Pénétration", f"{taux_gen} %")
        
        legende_codes = "• Code 0 : Princeps\n• Code 1 : Générique standard\n• Code 2 : Biosimilaire\n• Code 3 : Équivalent\n• Code 4 : Autre"
        col_m3.metric(label="🗂️ Groupes Génériques", value=f"{df_gener['DENOMINATION_GEN'].nunique():,}".replace(',', ' ') if "DENOMINATION_GEN" in df_gener.columns else "0", help=legende_codes)
        st.caption("💡 Légende du répertoire : 0 = Princeps | 1 = Générique | 2 = Biosimilaire | 3 = Équivalent | 4 = Autre")
        st.divider()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            df_status_count = df_gener["Statut_Identifie"].value_counts().reset_index()
            df_status_count.columns = ["Statut", "Nombre"]
            fig_statut = px.bar(df_status_count, x="Nombre", y="Statut", orientation='h', color="Statut", template=plotly_template, color_discrete_sequence=px.colors.sequential.Tealgrn_r)
            fig_statut.update_layout(showlegend=False, height=350, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_statut, width='stretch')
        with col_g2:
            if "DENOMINATION_GEN" in df_gener.columns:
                df_gen_count = df_gener["DENOMINATION_GEN"].value_counts().reset_index()
                df_gen_count.columns = ["Groupes", "Nombre"]
                fig_pie_gen = px.pie(df_gen_count.head(10), names="Groupes", values="Nombre", hole=0.4, template=plotly_template, color_discrete_sequence=px.colors.sequential.Blues_r)
                fig_pie_gen.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_pie_gen, width='stretch')

# ===================================================
# 💰 ONGLET 5 : INGENIERIE ÉCONOMIQUE
# ===================================================
with tabs[4]:
    st.subheader("Analyse des Prix et Santé Concurrentielle")
    df_economique = df.dropna(subset=["PRIX"])
    col_e1, col_e2, col_e3 = st.columns(3)
    
    parts = df_cis["TITULAIRES"].value_counts(normalize=True)
    hhi = round((parts ** 2).sum() * 10000, 0)
    
    col_e1.metric("💰 Prix Moyen d'un CIP", f"{round(df_economique['PRIX'].mean(), 2)} €")
    col_e2.metric("📊 Prix Médian d'un CIP", f"{round(df_economique['PRIX'].median(), 2)} €")
    col_e3.metric("⚖️ Indice de Concentration HHI", f"{int(hhi)}")
    st.divider()
    
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        fig_hist = px.histogram(df_economique[df_economique["PRIX"] <= df_economique["PRIX"].quantile(0.95)], x="PRIX", nbins=60, template=plotly_template, color_discrete_sequence=['#10b981'])
        st.plotly_chart(fig_hist, width='stretch')
    with c_g2:
        st.markdown("#### 📦 Répartition par Formes Galéniques")
        df_forme = df_economique["FORME_CATEGORIE"].value_counts().reset_index()
        df_forme.columns = ["Forme", "Volume"]
        fig_forme = px.bar(df_forme, x="Volume", y="Forme", orientation="h", color="Forme", template=plotly_template, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_forme.update_layout(showlegend=False, height=350, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_forme, width='stretch')

# ===================================================
# 🛠️ NOUVEL COMPOSANT : OUTILS DÉCISIONNELS & DEEP-DIVE
# ===================================================
with tabs[5]:
    st.header("🧰 Suite d'Outils Stratégiques Avancés")
    
    sub_tabs = st.tabs([
        "🔍 Deep-Dive Fiche d'Identité", 
        "🔀 Moteur de Substitution", 
        "📈 Simulateur Macro-Économique (What-If)"
    ])
    
    # -----------------------------------------------
    # SUB-TAB 1 : DEEP DIVE LABORATOIRES
    # -----------------------------------------------
    with sub_tabs[0]:
        st.subheader("🕵️‍♂️ Profil Économique d'un Laboratoire")
        liste_labs = sorted(df["TITULAIRES"].dropna().unique())
        selected_lab = st.selectbox("Sélectionnez l'acteur à auditer :", liste_labs, index=0 if liste_labs else None)
        
        if selected_lab:
            df_sub_lab = df[df["TITULAIRES"] == selected_lab]
            c_l1, c_l2, c_l3 = st.columns(3)
            c_l1.metric("Catalogue de Spécialités", f"{df_sub_lab['CIS'].nunique()} réf.")
            c_l2.metric("Prix Moyen Catalogue", f"{round(df_sub_lab['PRIX'].mean(), 2)} €")
            c_l3.metric("Prix Maximum Pratiqué", f"{round(df_sub_lab['PRIX'].max(), 2)} €")
            
            st.markdown(f"**Échantillon du catalogue commercial de {selected_lab} :**")
            st.dataframe(df_sub_lab[["DENOMINATION", "FORME_CATEGORIE", "PRIX"]].dropna().head(10), width='stretch')

    # -----------------------------------------------
    # SUB-TAB 2 : MOTEUR DE SUBSTITUTION
    # -----------------------------------------------
    with sub_tabs[1]:
        st.subheader("💊 Outil Officine : Recherche d'Alternatives Économiques")
        recherche = st.text_input("Entrez le début du nom d'un médicament (ex: DOLIPRANE, AMX) :", "").upper()
        
        if recherche:
            match_meds = df[df["DENOMINATION"].str.contains(recherche, na=False)]
            if not match_meds.empty:
                med_choisi = st.selectbox("Sélectionnez le médicament exact à substituer :", match_meds["DENOMINATION"].unique())
                
                # Extraction du code CIS cible
                cis_cible = df[df["DENOMINATION"] == med_choisi]["CIS"].values[0]
                
                # Recherche des substances actives liées à ce médicament
                substances = df_compo[df_compo["CIS"] == cis_cible]["SUBSTANCE"].unique()
                
                if len(substances) > 0:
                    st.success(f"🧪 Substance active détectée : **{', '.join(substances)}**")
                    
                    # Recherche de tous les autres médicaments contenant cette même substance
                    cis_equivalents = df_compo[df_compo["SUBSTANCE"].isin(substances)]["CIS"].unique()
                    df_substituts = df[(df["CIS"].isin(cis_equivalents)) & (df["CIS"] != cis_cible)].dropna(subset=["PRIX"])
                    
                    if not df_substituts.empty:
                        st.markdown("### 🔄 Alternatives génériques & équivalents identifiés (classés par prix croissants) :")
                        df_substituts_clean = df_substituts[["DENOMINATION", "TITULAIRES", "PRIX"]].drop_duplicates().sort_values("PRIX")
                        st.dataframe(df_substituts_clean, width='stretch')
                        
                        # Bouton d'exportation CSV Pro
                        csv = df_substituts_clean.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Exporter la liste des substituts (CSV)", data=csv, file_name=f"substituts_{recherche}.csv", mime="text/csv")
                    else:
                        st.info("Aucune alternative moins chère trouvée dans la base de données actuelle.")
                else:
                    st.warning("Aucune formule chimique/substance répertoriée pour ce produit.")
            else:
                st.error("Aucun médicament trouvé avec ce nom.")

    # -----------------------------------------------
    # SUB-TAB 3 : SIMULATEUR WHAT-IF
    # -----------------------------------------------
    with sub_tabs[2]:
        st.subheader("📉 Modélisation des Politiques de Baisses de Prix Publiques")
        st.markdown("Estimez les économies théoriques ou l'impact d'une contrainte réglementaire nationale sur les prix.")
        
        pct_baisse = st.slider("Pourcentage de réduction réglementaire à imposer (%) :", 0, 50, 10)
        cible_statut = st.radio("Marché ciblé par la baisse :", ["Tous les médicaments", "Uniquement les Princeps (Code 0)", "Uniquement les Génériques"])
        
        # Application du filtre selon la simulation
        df_simul = df.dropna(subset=["PRIX"]).copy()
        
        if cible_statut == "Uniquement les Princeps (Code 0)" and not df_gener.empty:
            if col_cle_gen:
                cis_princeps = df_gener[df_gener[statut_col] == 0][col_cle_gen].unique()
                df_simul = df_simul[df_simul["CIS"].isin(cis_princeps)]
        elif cible_statut == "Uniquement les Génériques" and not df_gener.empty:
            if col_cle_gen:
                cis_gen_list = df_gener[df_gener[statut_col] != 0][col_cle_gen].unique()
                df_simul = df_simul[df_simul["CIS"].isin(cis_gen_list)]
                
        prix_total_avant = df_simul["PRIX"].sum()
        prix_total_apres = prix_total_avant * (1 - (pct_baisse / 100))
        economie_theorique = prix_total_avant - prix_total_apres
        
        c_s1, c_s2 = st.columns(2)
        c_s1.metric("Coût cumulé de l'échantillon ciblé", f"{round(prix_total_avant, 2):,}".replace(',', ' ') + " €")
        c_s2.metric("📉 Économie théorique estimée (Par panier d'achat)", f"{round(economie_theorique, 2):,}".replace(',', ' ') + " €", delta=f"-{pct_baisse}%")
        
        # Graphique prédictif comparatif
        fig_sim = go.Figure(data=[
            go.Bar(name='Avant régulation', x=['Panier global'], y=[prix_total_avant], marker_color='#64748b'),
            go.Bar(name='Après baisse réglementaire', x=['Panier global'], y=[prix_total_apres], marker_color='#ef4444')
        ])
        fig_sim.update_layout(barmode='group', template=plotly_template, height=350)
        st.plotly_chart(fig_sim, width='stretch')