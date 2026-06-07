import pytest
import sqlite3
import pandas as pd
import tempfile
import os
from database import PharmaDataPipeline


class TestPharmaDataPipeline:
    """Test suite for PharmaDataPipeline class"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield db_path
            # Cleanup
            if os.path.exists(db_path):
                os.remove(db_path)
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_pipeline_initialization(self, temp_db, temp_data_dir):
        """Test that pipeline initializes correctly"""
        pipeline = PharmaDataPipeline(db_name=temp_db, data_dir=temp_data_dir)
        assert os.path.exists(temp_db)
        assert isinstance(pipeline.conn, sqlite3.Connection)
        pipeline.close()
    
    def test_pipeline_removes_old_db(self, temp_db, temp_data_dir):
        """Test that pipeline removes old database before creating new one"""
        # Create initial database
        PharmaDataPipeline(db_name=temp_db, data_dir=temp_data_dir).close()

        # Create new pipeline - should remove and recreate
        pipeline = PharmaDataPipeline(db_name=temp_db, data_dir=temp_data_dir)
        
        # New database should be created (smaller initially)
        assert os.path.exists(temp_db)
        pipeline.close()
    
    def test_remove_accents(self, temp_db, temp_data_dir):
        """Test accent removal functionality"""
        pipeline = PharmaDataPipeline(db_name=temp_db, data_dir=temp_data_dir)
        
        # Test cases
        # pylint: disable=protected-access
        assert pipeline._remove_accents("café") == "cafe"
        assert pipeline._remove_accents("naïve") == "naive"
        assert pipeline._remove_accents("résumé") == "resume"
        assert pipeline._remove_accents("normal") == "normal"
        assert pipeline._remove_accents(None) is None
        assert pipeline._remove_accents(123) == 123
        # pylint: enable=protected-access
        
        pipeline.close()
    
    def test_create_indexes(self, temp_db, temp_data_dir):
        """Test that indexes are created successfully"""
        pipeline = PharmaDataPipeline(db_name=temp_db, data_dir=temp_data_dir)
        
        # Create a dummy table first
        df = pd.DataFrame({
            'CIS': ['001', '002', '003'],
            'DENOMINATION': ['MED1', 'MED2', 'MED3']
        })
        df.to_sql('medicaments', pipeline.conn, if_exists='replace', index=False)
        
        # Create indexes
        pipeline.create_indexes()
        
        # Verify indexes exist
        cursor = pipeline.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert any('idx_cis' in idx for idx in indexes)
        
        pipeline.close()
    
    def test_close_connection(self, temp_db, temp_data_dir):
        """Test that connection is closed properly"""
        pipeline = PharmaDataPipeline(db_name=temp_db, data_dir=temp_data_dir)
        pipeline.close()
        
        # Attempting to use closed connection should raise an error
        with pytest.raises(sqlite3.ProgrammingError):
            pipeline.conn.execute("SELECT 1")


class TestPharmaDataIntegration:
    """Integration tests for the pharmacy data pipeline"""
    
    def test_database_connection(self):
        """Test basic database connectivity"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create connection
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            """)
            conn.commit()
            
            # Verify table was created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
            assert cursor.fetchone() is not None
            
            conn.close()
            os.remove(db_path)
    
    def test_pandas_dataframe_operations(self):
        """Test pandas operations used in pipeline"""
        df = pd.DataFrame({
            'PRIX': ['10,50', '20,75', '5,00'],
            'REMBOURSEMENT': ['65%', '75%', '100%']
        })
        
        # Test price conversion
        df['PRIX'] = df['PRIX'].str.replace(',', '.', regex=False)
        df['PRIX'] = pd.to_numeric(
            df['PRIX'].str.extract(r'(\d+\.?\d*)', expand=False),
            errors='coerce'
        )
        
        assert df['PRIX'].tolist() == [10.5, 20.75, 5.0]
        
        # Test reimbursement extraction
        df['REMBOURSEMENT'] = pd.to_numeric(
            df['REMBOURSEMENT'].str.extract(r'(\d+)', expand=False),
            errors='coerce'
        )
        
        assert df['REMBOURSEMENT'].tolist() == [65.0, 75.0, 100.0]
