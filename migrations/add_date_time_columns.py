#!/usr/bin/env python3
"""
Migration script to add date_only, time_only, and day_of_week columns to photos table
and populate them from existing date_taken values.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager

def migrate():
    """Add date/time parsing columns and populate them."""
    
    # Load database
    config_path = Path(__file__).parent.parent / 'config.yaml'
    db = DatabaseManager.from_config(str(config_path))
    conn = db.conn
    
    print("=" * 80)
    print("Adding date_only, time_only, and day_of_week columns to photos table")
    print("=" * 80)
    
    # Check if columns already exist
    cursor = conn.execute("PRAGMA table_info(photos)")
    columns = {row['name'] for row in cursor.fetchall()}
    
    # Add columns if they don't exist
    if 'date_only' not in columns:
        print("\nAdding date_only column...")
        conn.execute("ALTER TABLE photos ADD COLUMN date_only TEXT")
        print("✓ date_only column added")
    else:
        print("\n✓ date_only column already exists")
    
    if 'time_only' not in columns:
        print("Adding time_only column...")
        conn.execute("ALTER TABLE photos ADD COLUMN time_only TEXT")
        print("✓ time_only column added")
    else:
        print("✓ time_only column already exists")
    
    if 'day_of_week' not in columns:
        print("Adding day_of_week column...")
        conn.execute("ALTER TABLE photos ADD COLUMN day_of_week TEXT")
        print("✓ day_of_week column added")
    else:
        print("✓ day_of_week column already exists")
    
    # Populate the new columns from existing date_taken values
    print("\nPopulating new columns from date_taken...")
    
    # Get all photos with date_taken
    photos = conn.execute(
        "SELECT id, date_taken FROM photos WHERE date_taken IS NOT NULL"
    ).fetchall()
    
    print(f"Processing {len(photos)} photos...")
    
    updated = 0
    for photo in photos:
        try:
            # Parse the date_taken timestamp
            date_taken = datetime.fromisoformat(photo['date_taken'].replace('Z', '+00:00'))
            
            # Extract components
            date_only = date_taken.strftime('%Y-%m-%d')
            time_only = date_taken.strftime('%H:%M:%S')
            day_of_week = date_taken.strftime('%A')  # Monday, Tuesday, etc.
            
            # Update the photo
            conn.execute(
                """UPDATE photos 
                   SET date_only = ?, time_only = ?, day_of_week = ? 
                   WHERE id = ?""",
                (date_only, time_only, day_of_week, photo['id'])
            )
            updated += 1
            
            if updated % 1000 == 0:
                print(f"  Processed {updated} photos...")
                
        except Exception as e:
            print(f"  Warning: Could not parse date for photo {photo['id']}: {e}")
            continue
    
    conn.commit()
    print(f"\n✓ Successfully updated {updated} photos")
    
    # Show sample data
    print("\nSample data (first 5 photos):")
    samples = conn.execute(
        """SELECT file_name, date_taken, date_only, time_only, day_of_week 
           FROM photos 
           WHERE date_taken IS NOT NULL 
           LIMIT 5"""
    ).fetchall()
    
    for sample in samples:
        print(f"  {sample['file_name']}")
        print(f"    Date Taken: {sample['date_taken']}")
        print(f"    Date Only:  {sample['date_only']}")
        print(f"    Time Only:  {sample['time_only']}")
        print(f"    Day of Week: {sample['day_of_week']}")
        print()
    
    print("=" * 80)
    print("Migration completed successfully!")
    print("=" * 80)
    
    db.close()

if __name__ == '__main__':
    migrate()
