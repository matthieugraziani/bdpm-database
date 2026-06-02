import pandas as pd
import sqlite3
import os
from tqdm import tqdm
import unicodedata

# Note: import 'json' supprimé (inutilisé)


class PharmaDataPipeline:

    def __init__(self, db_name="bdpm.db", data_dir="data"):
        self.db_name = db_name
        self.data_dir = data_dir

        # Écriture dans un fichier temporaire pour éviter de perdre
        # la base précédente si le pipeline plante à mi-chemin
        self.tmp_db_name = db_name + ".tmp"
        if os.path.exists(self.tmp_db_name):
            os.remove(self.tmp_db_name)

        self.conn = sqlite3.connect(self.tmp_db_name)

    def _remove_accents(self, text):
        """Supprime les accents d'une chaîne de caractères."""
        if pd.isna(text) or not isinstance(text, str):
            return text
        nfkd = unicodedata.normalize('NFKD', text)
        return ''.join([c for c in nfkd if not unicodedata.combining(c)])

    def process_table(self, file_path, table_name, columns, text_columns=None):
        """
        Charge, nettoie et insère un fichier BDPM dans la base SQLite.

        Args:
            file_path: nom du fichier (relatif à data_dir)
            table_name: nom de la table SQLite cible
            columns: liste des noms de colonnes
            text_columns: colonnes sur lesquelles appliquer la normalisation
                          texte (None = toutes)
        """
        full_path = os.path.join(self.data_dir, file_path)
        if not os.path.exists(full_path):
            print(f"⚠️  Warning: {full_path} non trouvé.")
            return

        print(f"🚀 Processing {table_name}...")

        df = pd.read_csv(
            full_path,
            sep='\t',
            names=columns,
            encoding='latin-1',
            dtype=str,
            on_bad_lines='skip'
        )

        # Normalisation texte uniquement sur les colonnes non-numériques
        cols_to_normalize = text_columns if text_columns is not None else columns
        for col in cols_to_normalize:
            if col in df.columns:
                df[col] = df[col].apply(self._remove_accents)
                df[col] = df[col].str.strip().str.upper()

        # Logique métier spécifique à la table presentations
        if table_name == "presentations":
            df['PRIX'] = df['PRIX'].str.replace(',', '.', regex=False)
            df['PRIX'] = pd.to_numeric(
                df['PRIX'].str.extract(r'(\d+\.?\d*)', expand=False),
                errors='coerce'
            )
            df['REMBOURSEMENT'] = pd.to_numeric(
                df['REMBOURSEMENT'].str.extract(r'(\d+)', expand=False),
                errors='coerce'
            )

        df.to_sql(table_name, self.conn, if_exists='replace', index=False)
        print(f"✅ {table_name}: {len(df)} lignes insérées")

    def create_indexes(self):
        print("⚡ Optimisation des performances (Indexation)...")
        queries = [
            "CREATE INDEX IF NOT EXISTS idx_cis_med ON medicaments(CIS)",
            "CREATE INDEX IF NOT EXISTS idx_cis_pres ON presentations(CIS)",
            # Corrigé : index sur SUBSTANCE (cohérent avec la colonne réelle)
            "CREATE INDEX IF NOT EXISTS idx_substance ON compositions(SUBSTANCE)",
            "CREATE INDEX IF NOT EXISTS idx_cip_pres ON presentations(CIP13)",
            "CREATE INDEX IF NOT EXISTS idx_cpd ON conditions_prescription(CIS)",
            "CREATE INDEX IF NOT EXISTS idx_gener ON generiques(CIS_GEN)",
        ]
        for q in queries:
            try:
                self.conn.execute(q)
            except sqlite3.Error as e:
                print(f"⚠️  Erreur indexation: {e}")
        self.conn.commit()

    def get_stats(self):
        """Retourne un dict avec le nombre de lignes des tables principales."""
        tables = ["medicaments", "presentations", "compositions"]
        stats = {}
        for table in tables:
            try:
                stats[table] = self.conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
            except sqlite3.Error:
                stats[table] = 0
        return stats

    def close(self):
        self.conn.close()

        # Remplacement atomique : on écrase la base finale seulement si
        # tout s'est bien passé
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        os.rename(self.tmp_db_name, self.db_name)

        print("🏁 Pipeline terminé avec succès.")


# --- EXÉCUTION ---
if __name__ == "__main__":
    pipeline = PharmaDataPipeline()

    pipeline.process_table(
        "CIS_bdpm.txt",
        "medicaments",
        ["CIS", "DENOMINATION", "FORME", "VOIES", "STATUT_AMM", "TYPE_PROC",
         "ETAT_COMM", "DATE_AMM", "STATUT_BDM", "NUM_AMM", "TITULAIRES", "SURVEILLANCE"],
        text_columns=["DENOMINATION", "FORME", "VOIES", "STATUT_AMM", "TYPE_PROC",
                      "ETAT_COMM", "STATUT_BDM", "TITULAIRES"]
    )

    pipeline.process_table(
        "CIS_CIP_bdpm.txt",
        "presentations",
        ["CIS", "CIP7", "LIBELLE", "STATUT_ADMIN", "ETAT_COMM", "DATE_DECL",
         "CIP13", "AGREMENT", "REMBOURSEMENT", "PRIX", "HONORAIRE", "PRIX_HONO",
         "INDIC_REMBOURSEMENT"],
        text_columns=["LIBELLE", "STATUT_ADMIN", "ETAT_COMM", "AGREMENT", "INDIC_REMBOURSEMENT"]
    )

    pipeline.process_table(
        "CIS_COMPO_bdpm.txt",
        "compositions",
        ["CIS", "SUBSTANCE", "DOSAGE", "UNITE", "ROLE", "NATURE"]
    )

    pipeline.process_table(
        "CIS_CPD_bdpm.txt",
        "conditions_prescription",
        ["CIS", "CONDITION"]
    )

    pipeline.process_table(
        "CIS_GENER_bdpm.txt",
        "generiques",
        ["DENOMINATION_GEN", "CIS_GEN"]
    )

    pipeline.create_indexes()

    # Affichage des stats après insertion complète
    stats = pipeline.get_stats()
    print("\n📊 Résumé :")
    for table, count in stats.items():
        print(f"   {table}: {count} lignes")

    pipeline.close()
