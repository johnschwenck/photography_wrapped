"""
Add date_detected column to sessions table

This migration adds a date_detected column to track how session dates were determined
(e.g., "path", "filename (2 different dates, using most common (3/5 files))").
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager

def migrate():
    """Add date_detected column to sessions table."""
    
    # Connect directly to the database
    db_path = Path(__file__).parent.parent / 'metadata.db'
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.cursor()
        # Check if column already exists
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'date_detected' in columns:
            print("✓ Column 'date_detected' already exists in sessions table")
            return
        
        # Add the column
        print("Adding 'date_detected' column to sessions table...")
        cursor.execute("""
            ALTER TABLE sessions
            ADD COLUMN date_detected TEXT
        """)
        
        print("✓ Successfully added 'date_detected' column to sessions table")
        
        conn.commit()
            
    except Exception as e:
        conn.rollback()
        print(f"✗ Error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
