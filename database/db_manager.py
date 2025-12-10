"""
Database Manager

Provides database connection and CRUD operations with support for SQLite,
PostgreSQL, and MySQL.
"""

import sqlite3
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from contextlib import contextmanager
import yaml

# Import models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import (
    PhotoMetadata, Lens, LensType, Session, Category, Group,
    Analysis, AggregatedStats
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and operations.
    
    Supports SQLite (local), PostgreSQL (cloud), and MySQL (cloud) databases.
    Provides high-level CRUD operations for all domain models.
    
    Attributes:
        db_type: Type of database ('sqlite', 'postgresql', 'mysql')
        connection_string: Connection string or path to database
        conn: Active database connection
    
    Example:
        >>> db = DatabaseManager.from_config('config.yaml')
        >>> session = db.create_session(Session(...))
        >>> photos = db.get_photos_by_session(session.id)
    """
    
    def __init__(self, db_type: str = 'sqlite', connection_string: str = 'metadata.db'):
        """
        Initialize database manager.
        
        Args:
            db_type: Type of database ('sqlite', 'postgresql', 'mysql')
            connection_string: Connection string or path for SQLite
        """
        self.db_type = db_type
        self.connection_string = connection_string
        self.conn = None
        
        # Initialize connection
        self._connect()
        
        # Initialize schema if needed
        self._initialize_schema()
    
    @classmethod
    def from_config(cls, config_path: str = 'config.yaml') -> 'DatabaseManager':
        """
        Create DatabaseManager from configuration file.
        
        Args:
            config_path: Path to YAML configuration file
        
        Returns:
            Configured DatabaseManager instance
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        db_config = config.get('database', {})
        db_type = db_config.get('type', 'sqlite')
        
        if db_type == 'sqlite':
            connection_string = db_config.get('sqlite', {}).get('path', 'metadata.db')
        elif db_type == 'postgresql':
            # TODO: Implement PostgreSQL connection string
            connection_string = db_config.get('postgresql', {}).get('connection_string', '')
        elif db_type == 'mysql':
            # TODO: Implement MySQL connection string
            connection_string = db_config.get('mysql', {}).get('connection_string', '')
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        return cls(db_type=db_type, connection_string=connection_string)
    
    def _connect(self):
        """Establish database connection."""
        if self.db_type == 'sqlite':
            self.conn = sqlite3.connect(self.connection_string)
            self.conn.row_factory = sqlite3.Row
            # Enable foreign key constraints
            self.conn.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Connected to SQLite database: {self.connection_string}")
        elif self.db_type == 'postgresql':
            # TODO: Implement PostgreSQL connection
            try:
                import psycopg2  # type: ignore
                self.conn = psycopg2.connect(self.connection_string)
                logger.info("Connected to PostgreSQL database")
            except ImportError:
                raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")
        elif self.db_type == 'mysql':
            # TODO: Implement MySQL connection
            try:
                import mysql.connector  # type: ignore
                self.conn = mysql.connector.connect(self.connection_string)
                logger.info("Connected to MySQL database")
            except ImportError:
                raise ImportError("mysql-connector-python is required for MySQL. Install with: pip install mysql-connector-python")
    
    def _initialize_schema(self):
        """Initialize database schema if tables don't exist."""
        schema_path = os.path.join(
            os.path.dirname(__file__),
            'schema.sql'
        )
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            cursor = self.conn.cursor()  # type: ignore
            # Execute schema (SQLite allows multiple statements)
            if self.db_type == 'sqlite':
                cursor.executescript(schema_sql)  # type: ignore
            else:
                # For PostgreSQL/MySQL, split and execute individually
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        cursor.execute(statement)
            
            self.conn.commit()  # type: ignore
            logger.info("Database schema initialized")
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursors.
        
        Yields:
            Database cursor
        
        Example:
            >>> with db.get_cursor() as cursor:
            ...     cursor.execute("SELECT * FROM sessions")
            ...     rows = cursor.fetchall()
        """
        cursor = self.conn.cursor()  # type: ignore
        try:
            yield cursor
            self.conn.commit()  # type: ignore
        except Exception as e:
            self.conn.rollback()  # type: ignore
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    # ===========================
    # Category Operations
    # ===========================
    
    def create_category(self, category: Category) -> Category:
        """
        Create a new category in the database.
        
        Args:
            category: Category instance to create
        
        Returns:
            Category instance with assigned ID
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO categories (name, description)
                VALUES (?, ?)
            """, (category.name, category.description))
            
            category.id = cursor.lastrowid
            category.created_at = datetime.now()
            category.updated_at = datetime.now()
        
        logger.info(f"Created category: {category.name} (ID: {category.id})")
        return category
    
    def get_category(self, category_id: Optional[int] = None, name: Optional[str] = None) -> Optional[Category]:
        """
        Get category by ID or name.
        
        Args:
            category_id: Category ID
            name: Category name
        
        Returns:
            Category instance or None
        """
        with self.get_cursor() as cursor:
            if category_id:
                cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
            elif name:
                cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
            else:
                return None
            
            row = cursor.fetchone()
            if row:
                return Category(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    description=row['description'],  # type: ignore
                    total_groups=row['total_groups'],  # type: ignore
                    total_sessions=row['total_sessions'],  # type: ignore
                    total_photos=row['total_photos'],  # type: ignore
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,  # type: ignore
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,  # type: ignore
                )
        
        return None
    
    def get_or_create_category(self, name: str, description: Optional[str] = None) -> Category:
        """
        Get existing category or create if doesn't exist.
        
        Args:
            name: Category name
            description: Optional description
        
        Returns:
            Category instance
        """
        category = self.get_category(name=name)
        if category:
            return category
        
        return self.create_category(Category(name=name, description=description))
    
    def list_categories(self) -> List[Category]:
        """Get all categories."""
        categories = []
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM categories ORDER BY name")
            for row in cursor.fetchall():
                categories.append(Category(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    description=row['description'],  # type: ignore
                    total_groups=row['total_groups'],  # type: ignore
                    total_sessions=row['total_sessions'],  # type: ignore
                    total_photos=row['total_photos'],  # type: ignore
                ))
        
        return categories
    
    # ===========================
    # Group Operations
    # ===========================
    
    def create_group(self, group: Group) -> Group:
        """Create a new group."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO groups (name, category_id, description)
                VALUES (?, ?, ?)
            """, (group.name, group.category_id, group.description))
            
            group.id = cursor.lastrowid
            group.created_at = datetime.now()
            group.updated_at = datetime.now()
        
        logger.info(f"Created group: {group.name} (ID: {group.id})")
        return group
    
    def get_group(self, group_id: Optional[int] = None, name: Optional[str] = None, category_id: Optional[int] = None) -> Optional[Group]:
        """Get group by ID or name+category."""
        with self.get_cursor() as cursor:
            if group_id:
                cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
            elif name and category_id:
                cursor.execute(
                    "SELECT * FROM groups WHERE name = ? AND category_id = ?",
                    (name, category_id)
                )
            else:
                return None
            
            row = cursor.fetchone()
            if row:
                return Group(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    category_id=row['category_id'],  # type: ignore
                    description=row['description'],  # type: ignore
                    total_sessions=row['total_sessions'],  # type: ignore
                    total_photos=row['total_photos'],  # type: ignore
                )
        
        return None
    
    def get_or_create_group(self, name: str, category_id: int, description: Optional[str] = None) -> Group:
        """Get existing group or create if doesn't exist."""
        group = self.get_group(name=name, category_id=category_id)
        if group:
            return group
        
        return self.create_group(Group(
            name=name,
            category_id=category_id,
            description=description
        ))
    
    # ===========================
    # Session Operations
    # ===========================
    
    def create_session(self, session: Session) -> Session:
        """Create a new session."""
        with self.get_cursor() as cursor:
            # Get or create category and group
            category = self.get_or_create_category(session.category)
            assert category.id is not None, "Category ID should not be None after creation"
            group = self.get_or_create_group(session.group, category.id)
            
            # Debug logging for date
            logger.info(f"Creating session '{session.name}' with date: {session.date} (type: {type(session.date)})")
            
            cursor.execute("""
                INSERT INTO sessions (
                    name, category, group_name, category_id, group_id,
                    date, date_detected, location, description, folder_path, raw_folder_path,
                    total_photos, total_raw_photos, hit_rate
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.name, session.category, session.group,
                category.id, group.id,
                session.date, session.date_detected, session.location, session.description,
                session.folder_path, session.raw_folder_path,
                session.total_photos, session.total_raw_photos, session.hit_rate
            ))
            
            session.id = cursor.lastrowid
            session.created_at = datetime.now()
            session.updated_at = datetime.now()
        
        logger.info(f"Created session: {session.name} (ID: {session.id})")
        return session
    
    def get_session(self, session_id: int) -> Optional[Session]:
        """Get session by ID."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                return Session(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    category=row['category'],  # type: ignore
                    group=row['group_name'],  # type: ignore
                    date=datetime.fromisoformat(row['date']) if row['date'] else None,  # type: ignore
                    date_detected=row['date_detected'] if 'date_detected' in row.keys() else None,  # type: ignore
                    location=row['location'],  # type: ignore
                    description=row['description'],  # type: ignore
                    folder_path=row['folder_path'],  # type: ignore
                    raw_folder_path=row['raw_folder_path'],  # type: ignore
                    total_photos=row['total_photos'],  # type: ignore
                    total_raw_photos=row['total_raw_photos'],  # type: ignore
                    hit_rate=row['hit_rate'],  # type: ignore
                )
        
        return None
    
    def get_session_by_name(self, name: str, category: str, group: str) -> Optional[Session]:
        """Get session by unique name+category+group."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE name = ? AND category = ? AND group_name = ?
            """, (name, category, group))
            
            row = cursor.fetchone()
            if row:
                return Session(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    category=row['category'],  # type: ignore
                    group=row['group_name'],  # type: ignore
                    date=datetime.fromisoformat(row['date']) if row['date'] else None,  # type: ignore
                    folder_path=row['folder_path'],  # type: ignore
                    total_photos=row['total_photos'],  # type: ignore
                    hit_rate=row['hit_rate'],  # type: ignore
                )
        
        return None
    
    def list_sessions(self, category: Optional[str] = None, group: Optional[str] = None) -> List[Session]:
        """List sessions with optional filtering."""
        sessions = []
        with self.get_cursor() as cursor:
            if category and group:
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE category = ? AND group_name = ?
                    ORDER BY date DESC, name
                """, (category, group))
            elif category:
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE category = ?
                    ORDER BY date DESC, name
                """, (category,))
            else:
                cursor.execute("SELECT * FROM sessions ORDER BY date DESC, name")
            
            for row in cursor.fetchall():
                sessions.append(Session(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    category=row['category'],  # type: ignore
                    group=row['group_name'],  # type: ignore
                    date=datetime.fromisoformat(row['date']) if row['date'] else None,  # type: ignore
                    date_detected=row['date_detected'] if 'date_detected' in row.keys() else None,  # type: ignore
                    total_photos=row['total_photos'],  # type: ignore
                    hit_rate=row['hit_rate'],  # type: ignore
                ))
        
        return sessions
    
    def update_session(self, session: Session):
        """Update existing session."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sessions
                SET total_photos = ?, total_raw_photos = ?, hit_rate = ?
                WHERE id = ?
            """, (session.total_photos, session.total_raw_photos, session.hit_rate, session.id))
        
        logger.info(f"Updated session ID {session.id}")
    
    # ===========================
    # Photo Operations
    # ===========================
    
    def create_photo(self, photo: PhotoMetadata) -> PhotoMetadata:
        """Create a new photo record."""
        with self.get_cursor() as cursor:
            # Get or create lens
            lens_id = None
            if photo.lens:
                lens = self.get_or_create_lens(photo.lens)
                lens_id = lens.id
            
            cursor.execute("""
                INSERT INTO photos (
                    session_id, lens_id, file_path, file_name, camera, lens_name,
                    focal_length, iso, aperture, shutter_speed, shutter_speed_decimal,
                    exposure_program, exposure_bias, flash_mode, date_taken,
                    file_size, width, height
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                photo.session_id, lens_id, photo.file_path, photo.file_name,
                photo.camera, photo.lens, photo.focal_length, photo.iso,
                photo.aperture, photo.shutter_speed, photo.shutter_speed_decimal,
                photo.exposure_program, photo.exposure_bias, photo.flash_mode,
                photo.date_taken, photo.file_size, photo.width, photo.height
            ))
            
            photo.id = cursor.lastrowid
            photo.created_at = datetime.now()
        
        return photo
    
    def get_photos_by_session(self, session_id: int) -> List[PhotoMetadata]:
        """Get all photos for a session."""
        photos = []
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM photos WHERE session_id = ? ORDER BY file_name
            """, (session_id,))
            
            for row in cursor.fetchall():
                photos.append(PhotoMetadata(
                    id=row['id'],  # type: ignore
                    session_id=row['session_id'],  # type: ignore
                    file_path=row['file_path'],  # type: ignore
                    file_name=row['file_name'],  # type: ignore
                    camera=row['camera'],  # type: ignore
                    lens=row['lens_name'],  # type: ignore
                    focal_length=row['focal_length'],  # type: ignore
                    iso=row['iso'],  # type: ignore
                    aperture=row['aperture'],  # type: ignore
                    shutter_speed=row['shutter_speed'],  # type: ignore
                    shutter_speed_decimal=row['shutter_speed_decimal'],  # type: ignore
                    exposure_program=row['exposure_program'],  # type: ignore
                    exposure_bias=row['exposure_bias'],  # type: ignore
                    flash_mode=row['flash_mode'],  # type: ignore
                    date_taken=datetime.fromisoformat(row['date_taken']) if row['date_taken'] else None,  # type: ignore
                ))
        
        return photos
    
    # ===========================
    # Lens Operations
    # ===========================
    
    def create_lens(self, lens: Lens) -> Lens:
        """Create a new lens record."""
        # Auto-classify and extract info
        lens.classify_type()
        lens.extract_max_aperture()
        lens.extract_manufacturer()
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO lenses (
                    name, lens_type, manufacturer, focal_length_min,
                    focal_length_max, max_aperture
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                lens.name, lens.lens_type.value, lens.manufacturer,
                lens.focal_length_min, lens.focal_length_max, lens.max_aperture
            ))
            
            lens.id = cursor.lastrowid
        
        logger.info(f"Created lens: {lens.name} (ID: {lens.id})")
        return lens
    
    def get_lens(self, lens_id: Optional[int] = None, name: Optional[str] = None) -> Optional[Lens]:
        """Get lens by ID or name."""
        with self.get_cursor() as cursor:
            if lens_id:
                cursor.execute("SELECT * FROM lenses WHERE id = ?", (lens_id,))
            elif name:
                cursor.execute("SELECT * FROM lenses WHERE name = ?", (name,))
            else:
                return None
            
            row = cursor.fetchone()
            if row:
                return Lens(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    lens_type=LensType(row['lens_type']),  # type: ignore
                    manufacturer=row['manufacturer'],  # type: ignore
                    focal_length_min=row['focal_length_min'],  # type: ignore
                    focal_length_max=row['focal_length_max'],  # type: ignore
                    max_aperture=row['max_aperture'],  # type: ignore
                    usage_count=row['usage_count'],  # type: ignore
                )
        
        return None
    
    def get_or_create_lens(self, name: str) -> Lens:
        """Get existing lens or create if doesn't exist."""
        lens = self.get_lens(name=name)
        if lens:
            return lens
        
        return self.create_lens(Lens(name=name))
    
    def list_lenses(self) -> List[Lens]:
        """Get all lenses."""
        lenses = []
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM lenses ORDER BY name")
            for row in cursor.fetchall():
                lenses.append(Lens(
                    id=row['id'],  # type: ignore
                    name=row['name'],  # type: ignore
                    lens_type=LensType(row['lens_type']),  # type: ignore
                    manufacturer=row['manufacturer'],  # type: ignore
                    usage_count=row['usage_count'],  # type: ignore
                ))
        
        return lenses
    
    def get_all_categories(self) -> List[str]:
        """Get all unique categories from sessions."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT DISTINCT category FROM sessions WHERE category IS NOT NULL ORDER BY category")
            return [row[0] for row in cursor.fetchall()]
    
    def get_all_groups(self) -> List[str]:
        """Get all unique groups from sessions."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT DISTINCT group_name FROM sessions WHERE group_name IS NOT NULL ORDER BY group_name")
            return [row[0] for row in cursor.fetchall()]
    
    def delete_sessions_by_category(self, categories: List[str]) -> int:
        """Delete sessions and their photos by category.
        
        Args:
            categories: List of category names to delete
            
        Returns:
            Number of sessions deleted
        """
        if not categories:
            return 0
        
        placeholders = ','.join('?' * len(categories))
        with self.get_cursor() as cursor:
            # Get session IDs to delete
            cursor.execute(f"SELECT id FROM sessions WHERE category IN ({placeholders})", categories)
            session_ids = [row[0] for row in cursor.fetchall()]
            
            if not session_ids:
                return 0
            
            # Delete photos first (foreign key constraint)
            id_placeholders = ','.join('?' * len(session_ids))
            cursor.execute(f"DELETE FROM photos WHERE session_id IN ({id_placeholders})", session_ids)
            
            # Delete sessions
            cursor.execute(f"DELETE FROM sessions WHERE category IN ({placeholders})", categories)
            self.conn.commit()
            
            logger.info(f"Deleted {len(session_ids)} sessions from categories: {categories}")
            return len(session_ids)
    
    def delete_sessions_by_group(self, groups: List[str]) -> int:
        """Delete sessions and their photos by group.
        
        Args:
            groups: List of group names to delete
            
        Returns:
            Number of sessions deleted
        """
        if not groups:
            return 0
        
        placeholders = ','.join('?' * len(groups))
        with self.get_cursor() as cursor:
            # Get session IDs to delete
            cursor.execute(f"SELECT id FROM sessions WHERE group_name IN ({placeholders})", groups)
            session_ids = [row[0] for row in cursor.fetchall()]
            
            if not session_ids:
                return 0
            
            # Delete photos first (foreign key constraint)
            id_placeholders = ','.join('?' * len(session_ids))
            cursor.execute(f"DELETE FROM photos WHERE session_id IN ({id_placeholders})", session_ids)
            
            # Delete sessions
            cursor.execute(f"DELETE FROM sessions WHERE group_name IN ({placeholders})", groups)
            self.conn.commit()
            
            logger.info(f"Deleted {len(session_ids)} sessions from groups: {groups}")
            return len(session_ids)
    
    def reset_database(self) -> Dict[str, int]:
        """Reset entire database by deleting all data.
        
        Returns:
            Dictionary with counts of deleted records
        """
        with self.get_cursor() as cursor:
            # Get counts before deletion
            cursor.execute("SELECT COUNT(*) FROM photos")
            photo_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM lenses")
            lens_count = cursor.fetchone()[0]
            
            # Delete all data (order matters due to foreign keys)
            cursor.execute("DELETE FROM photos")
            cursor.execute("DELETE FROM sessions")
            cursor.execute("DELETE FROM lenses")
            
            # Reset auto-increment counters (SQLite specific)
            cursor.execute("DELETE FROM sqlite_sequence")
            
            self.conn.commit()
            
            logger.info(f"Database reset: {session_count} sessions, {photo_count} photos, {lens_count} lenses deleted")
            
            return {
                'sessions': session_count,
                'photos': photo_count,
                'lenses': lens_count
            }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
