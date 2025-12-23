
"""
Local Development Server for Photography Wrapped

Provides a web interface for photographers to analyze their photo metadata
through a browser instead of the command line.

This server is designed for:
- Testing the Wrapped concept locally
- Developer preview and early adopter feedback
- Validating the web UI before full deployment

Usage:
    python run_local.py
    Then open browser to http://localhost:5000
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors import ExifExtractor
from analyzers import StatisticsAnalyzer
from reporters import TextReporter
from database import DatabaseManager
from analyzers.analyze_temporal_trends import analyze_temporal_trends

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Configuration
CONFIG_PATH = 'config.yaml'

# Progress tracking for long-running operations
progress_store = {}


@app.route('/')
def index():
    """Serve the main application page."""
    return send_from_directory('static', 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'photography-wrapped-local',
        'version': '0.1.0'
    })


@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """Get progress for a long-running task."""
    progress = progress_store.get(task_id, {'progress': 0, 'total': 0, 'status': 'unknown'})
    percentage = 0
    if progress['total'] > 0:
        percentage = int((progress['progress'] / progress['total']) * 100)
    
    return jsonify({
        'percentage': percentage,
        'progress': progress['progress'],
        'total': progress['total'],
        'status': progress.get('status', 'processing')
    })


@app.route('/api/browse-folder', methods=['POST'])
def browse_folder():
    """
    Open a folder picker dialog using tkinter.
    This works around browser security restrictions.
    
    Returns:
        JSON with selected folder path
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Create root window and hide it
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Open folder picker
        folder_path = filedialog.askdirectory(title='Select Folder')
        
        # Clean up
        root.destroy()
        
        if folder_path:
            return jsonify({
                'success': True,
                'path': folder_path
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No folder selected'
            })
            
    except Exception as e:
        logger.error(f"Error in browse_folder: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-duplicates', methods=['POST'])
def check_duplicates():
    """
    Check for potential duplicate sessions before extraction.
    
    Request JSON:
        {
            "category": "category_name",
            "group": "group_name",
            "session_name": "session_name" (optional),
            "date": "2025-12-04" (optional)
        }
    
    Returns:
        JSON with list of similar existing sessions
    """
    try:
        data = request.json
        category = (data.get('category') or '').strip()
        group = (data.get('group') or '').strip()
        session_name = (data.get('session_name') or '').strip()
        date_str = (data.get('date') or '').strip()
        input_total_photos = data.get('total_photos')
        input_total_raw_photos = data.get('total_raw_photos')
        input_hit_rate = data.get('hit_rate')
        
        if not category or not group:
            return jsonify({'similar_sessions': []}), 200
        
        # Connect to database
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        # Normalize input for comparison
        norm_category = db.normalize_for_comparison(category)
        norm_group = db.normalize_for_comparison(group)
        
        # Parse date if provided
        session_date = None
        if date_str:
            try:
                session_date = datetime.fromisoformat(date_str).date()
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}")
        
        # Find similar sessions with multiple strategies:
        # 1. Exact match on category + group + session_name (if provided)
        # 2. Match on category + group + date (if date provided)
        with db.get_cursor() as cursor:
            similar_sessions_dict = {}  # Use dict to deduplicate
            
            # Strategy 1: Check by session name if provided
            if session_name:
                norm_session_name = db.normalize_for_comparison(session_name)
                cursor.execute("""
                    SELECT DISTINCT name, category, group_name, date, date_detected,
                           total_photos, total_raw_photos, hit_rate
                    FROM sessions
                    WHERE LOWER(TRIM(category)) = ? 
                      AND LOWER(TRIM(group_name)) = ?
                      AND LOWER(TRIM(name)) = ?
                """, (norm_category, norm_group, norm_session_name))
                for row in cursor.fetchall():
                    key = (row['category'], row['group_name'], row['name'])
                    similar_sessions_dict[key] = row
            
            # Strategy 2: Check by date if provided (catches duplicates with different names)
            if session_date:
                cursor.execute("""
                    SELECT DISTINCT name, category, group_name, date, date_detected,
                           total_photos, total_raw_photos, hit_rate
                    FROM sessions
                    WHERE LOWER(TRIM(category)) = ? 
                      AND LOWER(TRIM(group_name)) = ?
                      AND date(date) = date(?)
                """, (norm_category, norm_group, session_date.isoformat()))
                for row in cursor.fetchall():
                    key = (row['category'], row['group_name'], row['name'])
                    similar_sessions_dict[key] = row
            
            # If neither session_name nor date provided, just check category + group
            if not session_name and not session_date:
                cursor.execute("""
                    SELECT DISTINCT name, category, group_name, date, date_detected,
                           total_photos, total_raw_photos, hit_rate
                    FROM sessions
                    WHERE LOWER(TRIM(category)) = ? AND LOWER(TRIM(group_name)) = ?
                """, (norm_category, norm_group))
                for row in cursor.fetchall():
                    key = (row['category'], row['group_name'], row['name'])
                    similar_sessions_dict[key] = row
            
            
            # Convert dict values to list and calculate match percentage
            similar_sessions = []
            for row in similar_sessions_dict.values():
                # Calculate match percentage based on matching fields
                # Fields to compare: category, group, date, total_photos, total_raw_photos, hit_rate
                # (excluding session name since that's what differs)
                matches = 0
                total_fields = 0
                
                # Category (always included in query, so always matches)
                matches += 1
                total_fields += 1
                
                # Group (always included in query, so always matches)
                matches += 1
                total_fields += 1
                
                # Date
                total_fields += 1
                if session_date and row['date']:
                    existing_date = row['date'].split('T')[0] if 'T' in str(row['date']) else str(row['date'])
                    if existing_date == session_date.isoformat():
                        matches += 1
                elif not session_date and not row['date']:
                    matches += 1  # Both have no date
                
                # Total photos (Final Edits)
                if input_total_photos is not None:
                    total_fields += 1
                    if row['total_photos'] == input_total_photos:
                        matches += 1
                
                # Total raw photos
                if input_total_raw_photos is not None:
                    total_fields += 1
                    if row['total_raw_photos'] == input_total_raw_photos:
                        matches += 1
                
                # Hit rate (compare within 1% tolerance since it's a calculated float)
                if input_hit_rate is not None and row['hit_rate'] is not None:
                    total_fields += 1
                    if abs(row['hit_rate'] - input_hit_rate) < 1.0:
                        matches += 1
                elif input_hit_rate is None and row['hit_rate'] is None:
                    # Both don't have hit rate (no RAW folder) - this counts as a match
                    total_fields += 1
                    matches += 1
                
                match_percentage = (matches / total_fields * 100) if total_fields > 0 else 0
                
                logger.debug(f"  Session '{row['name']}': {matches}/{total_fields} fields match = {match_percentage:.1f}%")
                
                similar_sessions.append({
                    'name': row['name'],
                    'category': row['category'],
                    'group': row['group_name'],
                    'date': row['date'],
                    'date_detected': row['date_detected'],
                    'total_photos': row['total_photos'],
                    'total_raw_photos': row['total_raw_photos'],
                    'hit_rate': row['hit_rate'],
                    'match_percentage': round(match_percentage, 1)
                })
        
        logger.info(f"Duplicate check: '{category}' / '{group}' / '{session_name}' / date={date_str} -> Found {len(similar_sessions)} similar session(s)")
        
        return jsonify({
            'similar_sessions': similar_sessions,
            'input_category': category,
            'input_group': group,
            'input_session_name': session_name
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/extract', methods=['POST'])
def extract_metadata():
    """
    Extract EXIF metadata from a folder of photos.
    
    Request JSON:
        {
            "folder_path": "/path/to/photos",
            "session_name": "Session Name",
            "date": "2025-04-03",
            "use_date_heuristics": true,
            "category": "category_name",
            "group": "group_name",
            "description": "Optional description",
            "calculate_hit_rate": true
        }
    
    Returns:
        JSON with session details and extraction results
    """
    try:
        data = request.json
        folder_path = data.get('folder_path')
        session_name = data.get('session_name')
        # If session_name is None or empty string, use basename as fallback
        if not session_name:
            session_name = os.path.basename(folder_path)
        date_str = data.get('date_str') or data.get('date')  # Support both parameter names
        use_date_heuristics = data.get('use_date_heuristics', True)
        use_filename_dates = data.get('use_filename_dates', True)
        category = data.get('category', 'personal')
        group = data.get('group', 'ungrouped')
        description = data.get('description')
        calculate_hit_rate = data.get('calculate_hit_rate', True)
        
        logger.info(f"Extract request - session_name: '{session_name}', folder: {folder_path}")
        logger.info(f"Extract request - use_date_heuristics: {use_date_heuristics}, date_str: {date_str}")
        
        # Parse date if provided
        session_date = None
        if date_str:
            try:
                session_date = datetime.fromisoformat(date_str)
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}")
        
        if not folder_path:
            return jsonify({'error': 'folder_path is required'}), 400
        
        if not os.path.exists(folder_path):
            return jsonify({'error': f'Folder not found: {folder_path}'}), 404
        
        logger.info(f"Processing single folder - Category: {category}, Group: {group}")
        logger.info(f"Extracting metadata from: {folder_path}")
        
        extractor = ExifExtractor.from_config(CONFIG_PATH)
        session = extractor.extract_folder(
            folder_path=folder_path,
            session_name=session_name,
            category=category,
            group=group,
            description=description,
            calculate_hit_rate=calculate_hit_rate,
            date=session_date,
            use_date_heuristics=use_date_heuristics,
            use_filename_dates=use_filename_dates
        )
        
        if not session:
            return jsonify({'error': 'Extraction failed'}), 500
        
        # Use date_detected from session, or fall back to legacy logic
        if session.date_detected:
            date_detected = session.date_detected
        else:
            # Legacy fallback for existing data
            date_detected = 'not found'
            if session.date:
                if session_date:
                    date_detected = 'provided'
                elif use_date_heuristics:
                    date_detected = 'found'
        
        return jsonify({
            'success': True,
            'session': {
                'id': session.id,
                'name': session.name,
                'category': session.category,
                'group': session.group,
                'total_photos': session.total_photos,
                'total_raw_photos': session.total_raw_photos,
                'hit_rate': session.hit_rate,
                'date': session.date.strftime('%Y-%m-%d') if session.date else None,
                'date_detected': date_detected
            }
        })
        
    except Exception as e:
        logger.error(f"Error in extract_metadata: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/crawl', methods=['POST'])
def crawl_folders():
    """
    Crawl a parent directory and extract from all matching subfolders.
    
    Request JSON:
        {
            "parent_dir": "/path/to/parent",
            "target_folder": "Edited",
            "category": "category_name",
            "group": "group_name",
            "description": "Optional description",
            "calculate_hit_rate": true
        }
    
    Returns:
        JSON with summary of all extracted sessions
    """
    try:
        data = request.json
        parent_dir = data.get('parent_dir')
        target_folder = data.get('target_folder', 'Edited')
        date_str = data.get('date_str') or data.get('date')  # Support both parameter names
        use_date_heuristics = data.get('use_date_heuristics', True)
        use_filename_dates = data.get('use_filename_dates', True)
        category = data.get('category', 'personal')
        group = data.get('group', 'ungrouped')
        description = data.get('description')
        calculate_hit_rate = data.get('calculate_hit_rate', True)
        
        if not parent_dir:
            return jsonify({'error': 'parent_dir is required'}), 400
        
        if not os.path.exists(parent_dir):
            return jsonify({'error': f'Directory not found: {parent_dir}'}), 404
        
        logger.info(f"Crawling: {parent_dir} for folders named '{target_folder}'")
        
        extractor = ExifExtractor.from_config(CONFIG_PATH)
        
        # Find all target folders
        target_folders = []
        target_lower = target_folder.lower()
        
        for root, dirs, files in os.walk(parent_dir):
            for dir_name in dirs:
                if dir_name.lower() == target_lower:
                    target_folders.append(os.path.join(root, dir_name))
        
        if not target_folders:
            return jsonify({
                'success': True,
                'message': f'No folders named "{target_folder}" found',
                'sessions': []
            })
        
        logger.info(f"Found {len(target_folders)} folders to process")
        logger.info(f"Batch crawling - Category: {category}, Group: {group}, Target: {target_folder}")
        
        # Parse date if provided
        session_date = None
        if date_str:
            try:
                session_date = datetime.fromisoformat(date_str)
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}")
        
        # Process each folder
        results = []
        successful = 0
        failed = 0
        
        for idx, folder_path in enumerate(target_folders, 1):
            # Extract session name from path
            # Priority: folder with date pattern > non-generic folder > endpoint folder
            parent_parts = Path(folder_path).parts
            session_name = None
            date_pattern_folder = None
            non_generic_folder = None
            
            # Date patterns to look for
            date_patterns = [
                r'\d{4}[-_]\d{2}[-_]\d{2}',  # YYYY-MM-DD or YYYY_MM_DD
                r'\d{2}[-_]\d{2}[-_]\d{4}',  # MM-DD-YYYY or MM_DD_YYYY
                r'\d{8}',                      # YYYYMMDD
                r'\d{2}[-_]\d{2}[-_]\d{2}'   # YY-MM-DD or MM-DD-YY
            ]
            
            generic_folders = ['photos', 'edited', 'raw', 'images', 'jpg', 'jpeg', 'export', 'exported']
            
            for j in range(len(parent_parts) - 1, -1, -1):
                part = parent_parts[j]
                part_lower = part.lower()
                
                # Check if folder has a date pattern
                has_date = any(re.search(pattern, part, re.IGNORECASE) for pattern in date_patterns)
                
                if has_date and not date_pattern_folder:
                    date_pattern_folder = part
                
                if part_lower not in generic_folders and not non_generic_folder:
                    non_generic_folder = part
            
            # Use priority order: date pattern > non-generic > endpoint
            session_name = date_pattern_folder or non_generic_folder or os.path.basename(folder_path)
            session_name = session_name.replace(' ', '_')
            
            logger.info(f"Processing {idx} of {len(target_folders)} - {session_name} (Category: {category}, Group: {group})")
            
            try:
                session = extractor.extract_folder(
                    folder_path=folder_path,
                    session_name=session_name,
                    date=session_date,
                    use_date_heuristics=use_date_heuristics,
                    use_filename_dates=use_filename_dates,
                    category=category,
                    group=group,
                    description=description,
                    calculate_hit_rate=calculate_hit_rate
                )
                
                if session:
                    results.append({
                        'success': True,
                        'session_id': session.id,
                        'session_name': session.name,
                        'total_photos': session.total_photos,
                        'hit_rate': session.hit_rate
                    })
                    successful += 1
                else:
                    results.append({
                        'success': False,
                        'folder': folder_path,
                        'error': 'Extraction returned None'
                    })
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing {folder_path}: {e}")
                results.append({
                    'success': False,
                    'folder': folder_path,
                    'error': str(e)
                })
                failed += 1
        
        return jsonify({
            'success': True,
            'summary': {
                'total': len(target_folders),
                'successful': successful,
                'failed': failed
            },
            'sessions': results
        })
        
    except Exception as e:
        logger.error(f"Error in crawl_folders: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze sessions and generate statistics with progress tracking."""
    try:
        data = request.json
        analysis_type = data.get('type', 'session')
        target = data.get('target')
        task_id = data.get('task_id', 'analyze')
        
        logger.info(f"=== ANALYZE REQUEST === Type: {analysis_type}, Target: {target}")
        
        if not target:
            return jsonify({'error': 'target is required'}), 400
        
        # Initialize progress
        progress_store[task_id] = {'progress': 0, 'total': 100, 'status': 'starting'}
        
        analyzer = StatisticsAnalyzer.from_config(CONFIG_PATH)
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        # Get total photo count for progress tracking
        if analysis_type == 'session':
            progress_store[task_id] = {'progress': 25, 'total': 100, 'status': 'loading session'}
            analysis = analyzer.analyze_session(int(target))
        elif analysis_type == 'group':
            progress_store[task_id] = {'progress': 25, 'total': 100, 'status': 'loading group'}
            # Analyze group across all categories
            analysis = analyzer.analyze_group(target)
        elif analysis_type == 'category':
            progress_store[task_id] = {'progress': 25, 'total': 100, 'status': 'loading category'}
            analysis = analyzer.analyze_category(target)
        else:
            return jsonify({'error': f'Invalid analysis type: {analysis_type}'}), 400
        
        progress_store[task_id] = {'progress': 75, 'total': 100, 'status': 'analyzing'}
        
        if not analysis:
            progress_store[task_id] = {'progress': 100, 'total': 100, 'status': 'failed'}
            return jsonify({'error': 'Analysis failed'}), 500
        
        # Convert analysis to dict
        progress_store[task_id] = {'progress': 90, 'total': 100, 'status': 'formatting results'}
        analysis_dict = analysis.to_dict()
        
        progress_store[task_id] = {'progress': 100, 'total': 100, 'status': 'complete'}
        
        return jsonify({
            'success': True,
            'analysis': analysis_dict
        })
        
    except Exception as e:
        logger.error(f"Error in analyze: {e}", exc_info=True)
        if task_id in progress_store:
            progress_store[task_id] = {'progress': 100, 'total': 100, 'status': 'error'}
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/database', methods=['POST'])
def analyze_database():
    """
    Analyze data from database with optional filters.
    
    Request Body:
        category: Optional category filter
        group: Optional group filter
        sessions: Optional list of specific session names to analyze
        filters: Optional dict of metadata filters (camera, lens, aperture, shutter_speed, iso, focal_length, time_of_day)
    
    Returns:
        JSON with comprehensive analysis results
    """
    try:
        data = request.get_json() or {}
        category = data.get('category')
        group = data.get('group')
        sessions = data.get('sessions')  # List of session names
        filters = data.get('filters', {})  # Metadata filters for drill-down
        
        print(f"[ANALYZE_DATABASE] Received request:")
        print(f"  Category: {category}")
        print(f"  Group: {group}")
        print(f"  Sessions: {sessions}")
        print(f"  Filters: {filters}")
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        analyzer = StatisticsAnalyzer(db)
        
        # Get session IDs based on category/group/sessions filters
        conn = db.conn
        session_ids = []
        
        if sessions and len(sessions) > 0:
            # Get specific sessions by name
            placeholders = ','.join('?' * len(sessions))
            session_rows = conn.execute(
                f"SELECT id FROM sessions WHERE name IN ({placeholders})",
                sessions
            ).fetchall()
            session_ids = [s['id'] for s in session_rows]
        elif category and group:
            # Get sessions by category and group
            session_rows = conn.execute(
                "SELECT id FROM sessions WHERE category = ? AND group_name = ?",
                (category, group)
            ).fetchall()
            session_ids = [s['id'] for s in session_rows]
        elif category:
            # Get sessions by category
            session_rows = conn.execute(
                "SELECT id FROM sessions WHERE category = ?",
                (category,)
            ).fetchall()
            session_ids = [s['id'] for s in session_rows]
        elif group:
            # Get sessions by group
            session_rows = conn.execute(
                "SELECT id FROM sessions WHERE group_name = ?",
                (group,)
            ).fetchall()
            session_ids = [s['id'] for s in session_rows]
        else:
            # Get all sessions
            session_rows = conn.execute("SELECT id FROM sessions").fetchall()
            session_ids = [s['id'] for s in session_rows]
        
        if not session_ids:
            return jsonify({'error': 'No matching sessions found'}), 404
        
        print(f"[ANALYZE_DATABASE] Session IDs: {len(session_ids)}")
        print(f"[ANALYZE_DATABASE] Filters type: {type(filters)}, value: {filters}, len: {len(filters) if filters else 0}")
        
        # Apply metadata filters if provided
        if filters and len(filters) > 0:
            print(f"[ANALYZE_DATABASE] *** APPLYING FILTERS ***")
            print(f"[ANALYZE_DATABASE] Applying filters to {len(session_ids)} sessions")
            print(f"[ANALYZE_DATABASE] Filter details: {filters}")
            
            # Use filtered analysis
            analysis = analyzer.analyze_with_filters(session_ids, filters)
            analysis_dict = analysis.to_dict()
            analysis_dict['filtered'] = True
            analysis_dict['active_filters'] = filters
            
            print(f"[ANALYZE_DATABASE] Filtered result: {analysis.total_photos} photos")
            print(f"[ANALYZE_DATABASE] Lens freq: {dict(analysis.lens_freq)}")
            print(f"[ANALYZE_DATABASE] Camera freq: {dict(analysis.camera_freq)}")
            
            return jsonify({
                'success': True,
                'analysis': analysis_dict
            })
        
        # Original logic for unfiltered analysis
        # Build analysis based on filters
        if sessions and len(sessions) > 0:
            # Analyze specific sessions - use analyzer to get full frequency data
            print(f"[ANALYZE_DATABASE] Analyzing {len(session_ids)} sessions")
            analysis = analyzer.analyze_sessions(session_ids, name="Selected Sessions")
            analysis_dict = analysis.to_dict()
            analysis_dict['scope'] = 'sessions'
            
            return jsonify({
                'success': True,
                'analysis': analysis_dict
            })
        elif category and group:
            # Analyze specific group within category
            analysis = analyzer.analyze_group(group)
        elif category:
            # Analyze entire category
            analysis = analyzer.analyze_category(category)
        elif group:
            # Analyze entire group across all categories
            analysis = analyzer.analyze_group(group)
        else:
            # Analyze entire database - use analyzer for full statistics
            analysis = analyzer.analyze_sessions(session_ids, name="All Data")
            
            # Add categories and groups breakdown for "All Data" view
            conn = db.conn
            all_sessions = conn.execute("SELECT * FROM sessions").fetchall()
            
            # Get category breakdown
            categories = {}
            for session in all_sessions:
                cat = session['category'] or 'Uncategorized'
                if cat not in categories:
                    categories[cat] = {'sessions': 0, 'photos': 0}
                categories[cat]['sessions'] += 1
                categories[cat]['photos'] += session['total_photos']
            
            # Get group breakdown
            groups = {}
            for session in all_sessions:
                grp = session['group_name'] or 'Ungrouped'
                if grp not in groups:
                    groups[grp] = {'sessions': 0, 'photos': 0}
                groups[grp]['sessions'] += 1
                groups[grp]['photos'] += session['total_photos']
            
            analysis.metadata['categories'] = categories
            analysis.metadata['groups'] = groups
        
        # Convert analysis object to dict if we used analyzer
        analysis_dict = analysis.to_dict() if hasattr(analysis, 'to_dict') else analysis
        
        # Add metadata about the query
        analysis_dict['query_category'] = category
        analysis_dict['query_group'] = group
        
        return jsonify({
            'success': True,
            'analysis': analysis_dict
        })
        
    except Exception as e:
        logger.error(f"Error in analyze_database: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/wrapped', methods=['POST'])
def generate_wrapped():
    """Generate temporal trends analysis with progress tracking."""
    try:
        data = request.json
        category = data.get('category', 'running')
        group = data.get('group', 'thesole')
        task_id = data.get('task_id', 'wrapped')
        
        # Initialize progress
        progress_store[task_id] = {'progress': 0, 'total': 100, 'status': 'starting'}
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        progress_store[task_id] = {'progress': 20, 'total': 100, 'status': 'loading sessions'}
        
        # Get sessions for the group
        conn = db.conn
        sessions = conn.execute("""
            SELECT id, name, hit_rate, total_photos, total_raw_photos, 
                   date
            FROM sessions
            WHERE category = ? AND group_name = ?
            ORDER BY date
        """, (category, group)).fetchall()
        
        progress_store[task_id] = {'progress': 60, 'total': 100, 'status': 'analyzing trends'}
        
        if not sessions:
            progress_store[task_id] = {'progress': 100, 'total': 100, 'status': 'complete'}
            return jsonify({
                'success': True,
                'message': 'No sessions found for this category/group',
                'wrapped': None
            })
        
        progress_store[task_id] = {'progress': 80, 'total': 100, 'status': 'formatting results'}
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session['id'],
                'name': session['name'],
                'hit_rate': session['hit_rate'],
                'total_photos': session['total_photos'],
                'total_raw_photos': session['total_raw_photos'],
                'date': session['date']
            })
        
        progress_store[task_id] = {'progress': 100, 'total': 100, 'status': 'complete'}
        
        return jsonify({
            'success': True,
            'wrapped': {
                'category': category,
                'group': group,
                'total_sessions': len(sessions_data),
                'sessions': sessions_data,
                'note': 'Full temporal trends analysis coming soon'
            }
        })
        
    except Exception as e:
        logger.error(f"Error in generate_wrapped: {e}", exc_info=True)
        if task_id in progress_store:
            progress_store[task_id] = {'progress': 100, 'total': 100, 'status': 'error'}
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """
    List all sessions, optionally filtered by category or group.
    
    Query params:
        category: Filter by category
        group: Filter by group
    
    Returns:
        JSON list of sessions
    """
    try:
        category = request.args.get('category')
        group = request.args.get('group')
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        query = "SELECT * FROM sessions WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if group:
            query += " AND group_name = ?"
            params.append(group)
        
        query += " ORDER BY date DESC"
        
        sessions = db.conn.execute(query, params).fetchall()
        
        sessions_list = []
        for session in sessions:
            sessions_list.append({
                'id': session['id'],
                'name': session['name'],
                'category': session['category'],
                'group': session['group_name'],
                'total_photos': session['total_photos'],
                'total_raw_photos': session['total_raw_photos'],
                'hit_rate': session['hit_rate'],
                'date': session['date'],
                'description': session['description']
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_list
        })
        
    except Exception as e:
        logger.error(f"Error in list_sessions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/overview', methods=['GET'])
def database_overview():
    """
    Get comprehensive database overview with summary statistics.
    
    Returns:
        JSON with total counts and detailed session list
    """
    try:
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        # Get total counts
        total_sessions = db.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        total_photos = db.conn.execute("SELECT SUM(total_photos) FROM sessions").fetchone()[0] or 0
        
        # Get category breakdown
        category_stats = db.conn.execute("""
            SELECT category, COUNT(*) as session_count, SUM(total_photos) as photo_count
            FROM sessions
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY category
        """).fetchall()
        
        # Get group breakdown
        group_stats = db.conn.execute("""
            SELECT group_name, COUNT(*) as session_count, SUM(total_photos) as photo_count
            FROM sessions
            WHERE group_name IS NOT NULL
            GROUP BY group_name
            ORDER BY group_name
        """).fetchall()
        
        # Get all sessions with details
        sessions = db.conn.execute("""
            SELECT id, name, category, group_name, total_photos, total_raw_photos, hit_rate, date, 
                   folder_path, date_detected
            FROM sessions
            ORDER BY date DESC
        """).fetchall()
        
        sessions_list = []
        for session in sessions:
            sessions_list.append({
                'id': session['id'],
                'name': session['name'],
                'category': session['category'] or '',
                'group': session['group_name'] or '',
                'total_photos': session['total_photos'],
                'total_raw_photos': session['total_raw_photos'] or 0,
                'hit_rate': round(session['hit_rate'], 1) if session['hit_rate'] is not None else None,
                'date': session['date'],
                'folder_path': session['folder_path'],
                'date_detected': session['date_detected']
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'total_sessions': total_sessions,
                'total_photos': total_photos,
                'categories': [{'name': c['category'], 'sessions': c['session_count'], 'photos': c['photo_count']} 
                              for c in category_stats],
                'groups': [{'name': g['group_name'], 'sessions': g['session_count'], 'photos': g['photo_count']} 
                          for g in group_stats]
            },
            'sessions': sessions_list
        })
        
    except Exception as e:
        logger.error(f"Error in database_overview: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/categories-groups', methods=['GET'])
def get_categories_and_groups():
    """
    Get all categories and groups for dropdown population.
    
    Returns:
        JSON with categories and groups lists
    """
    try:
        db = DatabaseManager.from_config(CONFIG_PATH)
        categories = db.get_all_categories()
        groups = db.get_all_groups()
        
        return jsonify({
            'success': True,
            'categories': categories,
            'groups': groups
        })
        
    except Exception as e:
        logger.error(f"Error getting categories/groups: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/reset', methods=['POST'])
def reset_database():
    """
    Reset entire database (delete all data).
    
    Returns:
        JSON with counts of deleted records
    """
    try:
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({'error': 'Confirmation required'}), 400
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        deleted_counts = db.reset_database()
        
        return jsonify({
            'success': True,
            'message': 'Database reset successfully',
            'deleted': deleted_counts
        })
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/delete-category', methods=['POST'])
def delete_by_category():
    """
    Delete sessions by category.
    
    Request Body:
        categories: List of category names to delete
    
    Returns:
        JSON with number of sessions deleted
    """
    try:
        data = request.get_json() or {}
        categories = data.get('categories', [])
        
        if not categories:
            return jsonify({'error': 'No categories specified'}), 400
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        deleted_count = db.delete_sessions_by_category(categories)
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} sessions from {len(categories)} categories',
            'deleted_sessions': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Error deleting by category: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/delete-group', methods=['POST'])
def delete_by_group():
    """
    Delete sessions by group.
    
    Request Body:
        groups: List of group names to delete
    
    Returns:
        JSON with number of sessions deleted
    """
    try:
        data = request.get_json() or {}
        groups = data.get('groups', [])
        
        if not groups:
            return jsonify({'error': 'No groups specified'}), 400
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        deleted_count = db.delete_sessions_by_group(groups)
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} sessions from {len(groups)} groups',
            'deleted_sessions': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Error deleting by group: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/rename-sessions', methods=['POST'])
def rename_sessions():
    """
    Rename all sessions matching a category/group to new values.
    Used for resolving duplicate naming conflicts.
    
    Request JSON:
        {
            "old_category": "old_category_name",
            "old_group": "old_group_name",
            "new_category": "new_category_name",
            "new_group": "new_group_name"
        }
    
    Returns:
        JSON with count of updated sessions
    """
    try:
        data = request.json
        old_category = data.get('old_category', '').strip()
        old_group = data.get('old_group', '').strip()
        new_category = data.get('new_category', '').strip()
        new_group = data.get('new_group', '').strip()
        
        if not all([old_category, old_group, new_category, new_group]):
            return jsonify({'error': 'All fields are required'}), 400
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        # Get all sessions matching old category/group
        with db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sessions 
                SET category = ?, group_name = ?
                WHERE category = ? AND group_name = ?
            """, (new_category, new_group, old_category, old_group))
            
            updated_count = cursor.rowcount
        
        logger.info(f"Renamed {updated_count} sessions from '{old_category}/{old_group}' to '{new_category}/{new_group}'")
        
        return jsonify({
            'success': True,
            'updated_sessions': updated_count,
            'old': {'category': old_category, 'group': old_group},
            'new': {'category': new_category, 'group': new_group}
        })
        
    except Exception as e:
        logger.error(f"Error renaming sessions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/session/<int:session_id>', methods=['PUT'])
def update_session(session_id):
    """
    Update a session's basic information.
    
    Args:
        session_id: Session ID to update
    
    Request Body:
        name: New session name
        category: New category (optional)
        group: New group (optional)
        total_raw_photos: Total RAW photos count (optional, will auto-calculate hit_rate if provided)
    
    Returns:
        JSON with success status
    """
    try:
        data = request.get_json() or {}
        name = data.get('name')
        category = data.get('category')
        group = data.get('group')
        total_raw_photos = data.get('total_raw_photos')
        
        if not name:
            return jsonify({'error': 'Session name is required'}), 400
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        # Get current session to access total_photos for hit rate calculation
        session = db.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Calculate hit rate if both total_photos and total_raw_photos are present
        hit_rate = None
        if session.total_photos and total_raw_photos and total_raw_photos > 0:
            hit_rate = round((session.total_photos / total_raw_photos) * 100, 1)
        
        # Update session
        with db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sessions 
                SET name = ?, category = ?, group_name = ?, total_raw_photos = ?, hit_rate = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (name, category, group, total_raw_photos, hit_rate, session_id))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Session not found'}), 404
        
        logger.info(f"Updated session {session_id}: {name} (RAW: {total_raw_photos}, Hit Rate: {hit_rate}%)")
        
        return jsonify({
            'success': True,
            'message': 'Session updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/database/session/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    """
    Delete a single session and all its photo metadata.
    
    Args:
        session_id: Session ID to delete
    
    Returns:
        JSON with success status
    """
    try:
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        # Get session name for logging
        session = db.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Delete session (CASCADE will delete associated photos)
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        
        logger.info(f"Deleted session {session_id}: {session.name}")
        
        return jsonify({
            'success': True,
            'message': f'Session "{session.name}" deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories', methods=['GET'])
def list_categories():
    """
    List all categories with summary statistics.
    
    Returns:
        JSON list of categories
    """
    try:
        db = DatabaseManager.from_config(CONFIG_PATH)
        categories = db.list_categories()
        
        categories_list = []
        for category in categories:
            categories_list.append({
                'name': category.name,
                'total_sessions': category.total_sessions,
                'total_photos': category.total_photos
            })
        
        return jsonify({
            'success': True,
            'categories': categories_list
        })
        
    except Exception as e:
        logger.error(f"Error in list_categories: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/groups', methods=['GET'])
def list_groups():
    """
    List all groups, optionally filtered by category.
    
    Query params:
        category: Filter by category
    
    Returns:
        JSON list of groups
    """
    try:
        category = request.args.get('category')
        
        db = DatabaseManager.from_config(CONFIG_PATH)
        
        if category:
            groups = db.list_groups_by_category(category)
        else:
            # Get all groups
            query = """
                SELECT group_name as name, 
                       COUNT(*) as total_sessions,
                       SUM(total_photos) as total_photos
                FROM sessions
                GROUP BY group_name
                ORDER BY name
            """
            results = db.conn.execute(query).fetchall()
            
            from models import Group
            groups = [
                Group(
                    name=row['name'],
                    total_sessions=row['total_sessions'],
                    total_photos=row['total_photos']
                )
                for row in results
            ]
        
        groups_list = []
        for group in groups:
            groups_list.append({
                'name': group.name,
                'total_sessions': group.total_sessions,
                'total_photos': group.total_photos
            })
        
        return jsonify({
            'success': True,
            'groups': groups_list
        })
        
    except Exception as e:
        logger.error(f"Error in list_groups: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def kill_process_on_port(port):
    """Kill any process listening on the specified port."""
    import platform
    import subprocess
    
    try:
        if platform.system() == 'Windows':
            # Find process using port
            result = subprocess.run(
                ['netstat', '-ano'], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    try:
                        subprocess.run(
                            ['taskkill', '/F', '/PID', pid], 
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        logger.info(f"Killed existing process (PID {pid}) on port {port}")
                    except:
                        pass
        else:
            # Unix-like systems
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'], 
                capture_output=True, 
                text=True
            )
            if result.stdout:
                pid = result.stdout.strip()
                subprocess.run(['kill', '-9', pid], capture_output=True)
                logger.info(f"Killed existing process (PID {pid}) on port {port}")
    except Exception as e:
        logger.debug(f"Could not kill process on port {port}: {e}")


def main():
    """Run the development server."""
    # Kill any existing process on port 5000
    kill_process_on_port(5000)
    
    logger.info("=" * 80)
    logger.info("Photography Wrapped - Local Development Server")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Starting server at http://localhost:5000")
    logger.info("")
    logger.info("API Endpoints:")
    logger.info("  GET  /                    - Web interface")
    logger.info("  GET  /api/health          - Health check")
    logger.info("  POST /api/extract         - Extract metadata from folder")
    logger.info("  POST /api/crawl           - Crawl and extract from multiple folders")
    logger.info("  POST /api/analyze         - Analyze sessions")
    logger.info("  POST /api/analyze/database - Analyze database with filters")
    logger.info("  POST /api/wrapped         - Generate wrapped report")
    logger.info("  GET  /api/sessions        - List sessions")
    logger.info("  GET  /api/database/overview - Database overview with stats")
    logger.info("  GET  /api/database/categories-groups - Get categories and groups")
    logger.info("  POST /api/database/reset - Reset entire database")
    logger.info("  POST /api/database/delete-category - Delete by category")
    logger.info("  POST /api/database/delete-group - Delete by group")
    logger.info("  PUT  /api/database/session/<id> - Update session")
    logger.info("  DELETE /api/database/session/<id> - Delete session")
    logger.info("  GET  /api/categories      - List categories")
    logger.info("  GET  /api/groups          - List groups")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 80)
    
    app.run(debug=False, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
