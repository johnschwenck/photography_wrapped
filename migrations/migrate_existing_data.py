"""
Migrate Existing Data

Imports existing JSON metadata files into the new database structure.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import PhotoMetadata, Session
from database import DatabaseManager

logger = logging.getLogger(__name__)


def parse_session_info_from_path(json_path: str) -> Dict[str, str]:
    """
    Extract session info from JSON file path.
    
    Args:
        json_path: Path to JSON file
    
    Returns:
        Dict with category, group, and session_name
    
    Example:
        >>> info = parse_session_info_from_path('metadata_json/running_sole/01_-_2025-04-03/metadata_01.json')
        >>> print(info)
        {'category': 'running_sole', 'group': 'running_sole', 'session_name': '01_-_2025-04-03'}
    """
    parts = Path(json_path).parts
    
    # Find metadata_json index
    try:
        metadata_idx = parts.index('metadata_json')
    except ValueError:
        metadata_idx = 0
    
    # Extract components after metadata_json
    remaining = parts[metadata_idx + 1:]
    
    if len(remaining) >= 2:
        category = remaining[0]
        session_name = remaining[1]
        group = category  # Default group same as category
    elif len(remaining) == 1:
        category = 'uncategorized'
        group = 'uncategorized'
        session_name = remaining[0]
    else:
        category = 'uncategorized'
        group = 'uncategorized'
        session_name = 'unknown'
    
    return {
        'category': category,
        'group': group,
        'session_name': session_name
    }


def migrate_json_file(json_path: str, db: DatabaseManager, dry_run: bool = False) -> bool:
    """
    Migrate a single JSON file to database.
    
    Args:
        json_path: Path to JSON metadata file
        db: DatabaseManager instance
        dry_run: If True, don't actually insert into database
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Processing: {json_path}")
        
        # Parse session info from path
        session_info = parse_session_info_from_path(json_path)
        
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
        
        if not metadata_list:
            logger.warning(f"  Empty JSON file: {json_path}")
            return False
        
        logger.info(f"  Category: {session_info['category']}, "
                   f"Group: {session_info['group']}, "
                   f"Session: {session_info['session_name']}")
        logger.info(f"  Photos: {len(metadata_list)}")
        
        if dry_run:
            logger.info("  [DRY RUN] Would insert into database")
            return True
        
        # Check if session already exists
        existing_session = db.get_session_by_name(
            session_info['session_name'],
            session_info['category'],
            session_info['group']
        )
        
        if existing_session:
            logger.info(f"  Session already exists (ID: {existing_session.id}), skipping")
            return True
        
        # Create session
        session = Session(
            name=session_info['session_name'],
            category=session_info['category'],
            group=session_info['group'],
            total_photos=len(metadata_list)
        )
        
        session = db.create_session(session)
        logger.info(f"  Created session ID: {session.id}")
        
        # Insert photos
        photo_count = 0
        for metadata_dict in metadata_list:
            try:
                # Handle date parsing
                date_taken = None
                if 'DateTaken' in metadata_dict and metadata_dict['DateTaken']:
                    try:
                        date_taken = datetime.fromisoformat(metadata_dict['DateTaken'])
                    except:
                        pass
                
                photo = PhotoMetadata(
                    session_id=session.id,
                    file_path=metadata_dict.get('FilePath'),
                    file_name=metadata_dict.get('File', ''),
                    camera=metadata_dict.get('Camera', ''),
                    lens=metadata_dict.get('Lens', 'Unknown'),
                    focal_length=metadata_dict.get('FocalLength'),
                    iso=metadata_dict.get('ISO'),
                    aperture=metadata_dict.get('Aperture'),
                    shutter_speed=metadata_dict.get('ShutterSpeed'),
                    exposure_program=metadata_dict.get('ExposureProgram'),
                    exposure_bias=metadata_dict.get('ExposureBias'),
                    flash_mode=metadata_dict.get('FlashMode'),
                    date_taken=date_taken,
                    file_size=metadata_dict.get('FileSize'),
                    width=metadata_dict.get('Width'),
                    height=metadata_dict.get('Height'),
                )
                
                db.create_photo(photo)
                photo_count += 1
            
            except Exception as e:
                logger.error(f"    Error inserting photo: {e}")
        
        logger.info(f"  ✓ Migrated {photo_count} photos")
        return True
    
    except Exception as e:
        logger.error(f"  ✗ Error migrating {json_path}: {e}")
        return False


def find_all_json_files(directory: str) -> List[str]:
    """
    Recursively find all JSON metadata files.
    
    Args:
        directory: Root directory to search
    
    Returns:
        List of JSON file paths
    """
    json_files = []
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.json') and 'metadata' in filename.lower():
                json_files.append(os.path.join(root, filename))
    
    return json_files


def migrate_all_json_files(json_directory: str = 'metadata_json',
                          config_path: str = 'config.yaml',
                          dry_run: bool = False):
    """
    Migrate all JSON files in directory to database.
    
    Args:
        json_directory: Directory containing JSON files
        config_path: Path to configuration file
        dry_run: If True, don't actually insert into database
    """
    logger.info(f"Starting migration from: {json_directory}")
    
    # Find all JSON files
    json_files = find_all_json_files(json_directory)
    logger.info(f"Found {len(json_files)} JSON files")
    
    if not json_files:
        logger.warning("No JSON files found!")
        return
    
    # Connect to database
    db = DatabaseManager.from_config(config_path)
    
    # Migrate each file
    success_count = 0
    fail_count = 0
    
    for i, json_path in enumerate(json_files, 1):
        logger.info(f"\n[{i}/{len(json_files)}]")
        
        if migrate_json_file(json_path, db, dry_run=dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total files processed: {len(json_files)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    
    if dry_run:
        logger.info("\n[DRY RUN] No changes were made to database")
    
    db.close()


if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv
    
    migrate_all_json_files(dry_run=dry_run)
