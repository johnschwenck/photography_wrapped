"""
Command-Line Interface for Photo Metadata Analysis System

Provides commands for extracting, analyzing, and reporting on photo metadata.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors import ExifExtractor
from analyzers import StatisticsAnalyzer
from reporters import TextReporter
from database import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_extract(args):
    """Extract metadata from photos in a folder."""
    logger.info(f"Extracting metadata from: {args.folder}")
    
    extractor = ExifExtractor.from_config(args.config)
    
    session = extractor.extract_folder(
        folder_path=args.folder,
        session_name=args.name or os.path.basename(args.folder),
        category=args.category,
        group=args.group,
        description=args.description,
        calculate_hit_rate=args.hit_rate
    )
    
    if session:
        logger.info(f"✓ Successfully extracted {session.total_photos} photos")
        logger.info(f"  Session ID: {session.id}")
        if session.hit_rate:
            logger.info(f"  Hit Rate: {session.hit_rate:.1f}%")
    else:
        logger.error("✗ Extraction failed")


def cmd_crawl(args):
    """Crawl parent directory and extract metadata from all matching subfolders."""
    logger.info(f"Crawling: {args.parent_dir}")
    logger.info(f"  Looking for folders named: {args.target_folder}")
    
    extractor = ExifExtractor.from_config(args.config)
    
    # Find all target folders
    target_folders = []
    target_lower = args.target_folder.lower()
    
    for root, dirs, files in os.walk(args.parent_dir):
        for dir_name in dirs:
            if dir_name.lower() == target_lower:
                target_folders.append(os.path.join(root, dir_name))
    
    if not target_folders:
        logger.warning(f"No folders named '{args.target_folder}' found in {args.parent_dir}")
        return
    
    logger.info(f"Found {len(target_folders)} folders to process")
    
    # Process each folder
    successful = 0
    failed = 0
    
    for i, folder_path in enumerate(target_folders, 1):
        # Extract session name from path
        # For structure like: "The Sole/01 - 2025-04-03/Photos/Edited"
        # Session name would be: "01_-_2025-04-03"
        parent_parts = Path(folder_path).parts
        
        # Find the session folder (parent of "Photos")
        session_name = None
        for j in range(len(parent_parts) - 1, -1, -1):
            part = parent_parts[j]
            # Skip common folder names
            if part.lower() not in ['photos', 'edited', 'raw', 'images', 'jpg', 'jpeg']:
                session_name = part.replace(' ', '_')
                break
        
        if not session_name:
            session_name = os.path.basename(folder_path)
        
        logger.info(f"\n[{i}/{len(target_folders)}] Processing: {session_name}")
        logger.info(f"  Path: {folder_path}")
        
        try:
            session = extractor.extract_folder(
                folder_path=folder_path,
                session_name=session_name,
                category=args.category,
                group=args.group,
                description=args.description,
                calculate_hit_rate=args.hit_rate
            )
            
            if session:
                logger.info(f"  ✓ Extracted {session.total_photos} photos (ID: {session.id})")
                if session.hit_rate:
                    logger.info(f"  ✓ Hit Rate: {session.hit_rate:.2f}%")
                successful += 1
            else:
                logger.warning(f"  ✗ Failed to extract")
                failed += 1
        
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            failed += 1
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Crawl complete:")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total: {len(target_folders)}")


def cmd_analyze(args):
    """Analyze sessions and generate statistics."""
    logger.info(f"Analyzing: {args.target}")
    
    analyzer = StatisticsAnalyzer.from_config(args.config)
    reporter = TextReporter.from_config(args.config)
    
    if args.type == 'session':
        analysis = analyzer.analyze_session(int(args.target))
    elif args.type == 'group':
        category, group = args.target.split('/', 1) if '/' in args.target else (args.target, args.target)
        analysis = analyzer.analyze_group(group, category)
    elif args.type == 'category':
        analysis = analyzer.analyze_category(args.target)
    else:
        logger.error(f"Unknown analysis type: {args.type}")
        return
    
    logger.info(f"✓ Analysis complete:")
    logger.info(f"  Total Photos: {analysis.total_photos}")
    logger.info(f"  Unique Lenses: {len(analysis.lens_freq)}")
    if analysis.hit_rate:
        logger.info(f"  Hit Rate: {analysis.hit_rate:.1f}%")
    
    # Generate report if requested
    if args.report:
        report_path = reporter.generate_report(
            analysis,
            subdirectory=args.subdirectory,
            filename=args.output
        )
        logger.info(f"✓ Report saved to: {report_path}")


def cmd_report(args):
    """Generate reports from existing analysis."""
    logger.info("Generating reports...")
    
    analyzer = StatisticsAnalyzer.from_config(args.config)
    reporter = TextReporter.from_config(args.config)
    
    if args.session_id:
        analysis = analyzer.analyze_session(args.session_id)
        report_path = reporter.generate_report(analysis)
        logger.info(f"✓ Report saved to: {report_path}")
    
    elif args.all_categories:
        db = DatabaseManager.from_config(args.config)
        categories = db.list_categories()
        
        for category in categories:
            logger.info(f"Processing category: {category.name}")
            analysis = analyzer.analyze_category(category.name)
            report_path = reporter.generate_report(
                analysis,
                subdirectory=category.name,
                filename=f"aggregated_{category.name}_ALL.txt"
            )
            logger.info(f"  ✓ Saved to: {report_path}")


def cmd_list(args):
    """List sessions, categories, or lenses."""
    db = DatabaseManager.from_config(args.config)
    
    if args.type == 'categories':
        categories = db.list_categories()
        logger.info(f"\nCategories ({len(categories)}):")
        logger.info("-" * 60)
        for cat in categories:
            logger.info(f"  {cat.name:30} | {cat.total_sessions:3} sessions | {cat.total_photos:5} photos")
    
    elif args.type == 'sessions':
        sessions = db.list_sessions(category=args.category, group=args.group)
        logger.info(f"\nSessions ({len(sessions)}):")
        logger.info("-" * 80)
        for sess in sessions:
            hit_rate_str = f"{sess.hit_rate:.1f}%" if sess.hit_rate else "N/A"
            logger.info(f"  [{sess.id:3}] {sess.name:30} | {sess.total_photos:4} photos | Hit: {hit_rate_str}")
    
    elif args.type == 'lenses':
        lenses = db.list_lenses()
        logger.info(f"\nLenses ({len(lenses)}):")
        logger.info("-" * 80)
        for lens in lenses:
            logger.info(f"  {lens.name:50} | {lens.lens_type.value:6} | {lens.usage_count:5} uses")


def cmd_migrate(args):
    """Migrate existing JSON data to database."""
    from migrations.migrate_existing_data import migrate_all_json_files
    
    logger.info("Starting migration from JSON files...")
    
    migrate_all_json_files(
        json_directory=args.json_dir,
        config_path=args.config
    )
    
    logger.info("✓ Migration complete")


def cmd_query(args):
    """Query database for specific information."""
    db = DatabaseManager.from_config(args.config)
    
    if args.lens:
        lens = db.get_lens(name=args.lens)
        if lens:
            logger.info(f"\nLens: {lens.name}")
            logger.info(f"  Type: {lens.lens_type.value}")
            logger.info(f"  Manufacturer: {lens.manufacturer}")
            logger.info(f"  Usage: {lens.usage_count} photos")
        else:
            logger.info(f"Lens not found: {args.lens}")
    
    elif args.session_name:
        sessions = db.list_sessions()
        matching = [s for s in sessions if args.session_name.lower() in s.name.lower()]
        
        if matching:
            logger.info(f"\nFound {len(matching)} matching sessions:")
            for sess in matching:
                logger.info(f"  [{sess.id}] {sess.name} - {sess.total_photos} photos")
        else:
            logger.info(f"No sessions found matching: {args.session_name}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Photo Metadata Analysis System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Extract metadata from a folder
  python cli.py extract /photos/event --category concerts --group idkhow --name "IDKHOW 2025"
  
  # Crawl parent directory and process all "Edited" folders
  python cli.py crawl "The Sole" --category running_sole --group weekly --target-folder Edited
  
  # Analyze a group and generate report
  python cli.py analyze running_sole/weekly --type group --report
  
  # List all sessions in a category
  python cli.py list sessions --category running_sole
  
  # Migrate existing JSON files
  python cli.py migrate --json-dir metadata_json/
  
  # Query for specific lens usage
  python cli.py query --lens "FE 85mm F1.4 GM II"
        '''
    )
    
    parser.add_argument('--config', default='config.yaml', help='Path to config file')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract metadata from photos')
    extract_parser.add_argument('folder', help='Folder containing photos')
    extract_parser.add_argument('--name', help='Session name (default: folder name)')
    extract_parser.add_argument('--category', required=True, help='Category name')
    extract_parser.add_argument('--group', required=True, help='Group name')
    extract_parser.add_argument('--description', help='Session description')
    extract_parser.add_argument('--no-hit-rate', dest='hit_rate', action='store_false',
                              help='Skip hit rate calculation')
    extract_parser.set_defaults(func=cmd_extract)
    
    # Crawl command
    crawl_parser = subparsers.add_parser('crawl', help='Crawl directory and extract from all matching subfolders')
    crawl_parser.add_argument('parent_dir', help='Parent directory to crawl')
    crawl_parser.add_argument('--target-folder', default='Edited',
                             help='Target folder name to look for (default: Edited)')
    crawl_parser.add_argument('--category', required=True, help='Category name for all sessions')
    crawl_parser.add_argument('--group', required=True, help='Group name for all sessions')
    crawl_parser.add_argument('--description', help='Description for all sessions')
    crawl_parser.add_argument('--no-hit-rate', dest='hit_rate', action='store_false',
                             help='Skip hit rate calculation')
    crawl_parser.set_defaults(func=cmd_crawl)
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze sessions')
    analyze_parser.add_argument('target', help='Target to analyze (session ID, group name, or category)')
    analyze_parser.add_argument('--type', choices=['session', 'group', 'category'],
                               default='group', help='Analysis type')
    analyze_parser.add_argument('--report', action='store_true', help='Generate text report')
    analyze_parser.add_argument('--subdirectory', help='Subdirectory for report')
    analyze_parser.add_argument('--output', help='Output filename')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--session-id', type=int, help='Generate report for session')
    report_parser.add_argument('--all-categories', action='store_true',
                              help='Generate reports for all categories')
    report_parser.set_defaults(func=cmd_report)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List entities')
    list_parser.add_argument('type', choices=['categories', 'sessions', 'lenses'],
                            help='What to list')
    list_parser.add_argument('--category', help='Filter sessions by category')
    list_parser.add_argument('--group', help='Filter sessions by group')
    list_parser.set_defaults(func=cmd_list)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate existing JSON data')
    migrate_parser.add_argument('--json-dir', default='metadata_json',
                               help='Directory containing JSON files')
    migrate_parser.set_defaults(func=cmd_migrate)
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query database')
    query_parser.add_argument('--lens', help='Query lens by name')
    query_parser.add_argument('--session-name', help='Search sessions by name')
    query_parser.set_defaults(func=cmd_query)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
