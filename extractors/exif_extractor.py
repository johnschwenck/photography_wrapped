"""
EXIF Extractor

Extracts EXIF metadata from photo files and stores them in the database.
Supports local and cloud storage providers.
"""

import os
import json
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from fractions import Fraction
try:
    import exiftool  # type: ignore
except ImportError:
    raise ImportError("exiftool is required. Install with: pip install pyexiftool")

# Import local modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import PhotoMetadata, Session
from database import DatabaseManager
from storage import StorageProvider, create_storage_provider

logger = logging.getLogger(__name__)


class ExifExtractor:
    """
    Extracts EXIF metadata from photos and stores in database.
    
    Uses exiftool to extract comprehensive metadata from various image formats
    and persists the data to the database with proper relationships.
    
    Attributes:
        db: DatabaseManager instance
        storage: StorageProvider instance
        supported_extensions: List of supported file extensions
    
    Example:
        >>> extractor = ExifExtractor.from_config('config.yaml')
        >>> session = extractor.extract_folder(
        ...     '/photos/2025/running_sole/01_-_2025-04-03',
        ...     session_name='01_-_2025-04-03',
        ...     category='running_sole',
        ...     group='running_sole'
        ... )
    """
    
    def __init__(self, db: DatabaseManager, storage: StorageProvider,
                 supported_extensions: Optional[List[str]] = None):
        """
        Initialize EXIF extractor.
        
        Args:
            db: DatabaseManager instance
            storage: StorageProvider instance
            supported_extensions: List of file extensions to process
        """
        self.db = db
        self.storage = storage
        self.supported_extensions = supported_extensions or [
            '.arw', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
        ]
    
    @classmethod
    def from_config(cls, config_path: str = 'config.yaml') -> 'ExifExtractor':
        """
        Create ExifExtractor from configuration file.
        
        Args:
            config_path: Path to YAML configuration file
        
        Returns:
            Configured ExifExtractor instance
        """
        import yaml
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        db = DatabaseManager.from_config(config_path)
        storage = create_storage_provider(config_path)
        
        extraction_config = config.get('extraction', {})
        supported_extensions = extraction_config.get('supported_extensions', None)
        
        return cls(db=db, storage=storage, supported_extensions=supported_extensions)
    
    def extract_date_from_session_name(self, session_name: str) -> Optional[datetime]:
        """
        Extract date from session name using heuristics.
        
        Supports various date formats commonly used in photography session names:
        - YYYY-MM-DD or YYYY.MM.DD (ISO format)
        - MM-DD-YYYY, MM-DD-YY, MM.DD.YY, MM.DD.YYYY
        - DD-MM-YYYY, DD-MM-YY, DD.MM.YY, DD.MM.YYYY
        - Partial year formats like 25 (assumed 2025 if 20-40, else 19XX)
        
        If multiple dates found, returns the last (rightmost) one as it's closest to the target folder.
        
        Args:
            session_name: The session name to extract date from
        
        Returns:
            datetime object if date found, None otherwise
        
        Examples:
            >>> extractor.extract_date_from_session_name("01_-_2025-04-03")
            datetime(2025, 4, 3)
            >>> extractor.extract_date_from_session_name("concert_12.31.25")
            datetime(2025, 12, 31)
            >>> extractor.extract_date_from_session_name("running_04-03-25")
            datetime(2025, 4, 3)
        """
        if not session_name:
            return None
        
        # Pattern 1: YYYY-MM-DD or YYYY.MM.DD (ISO format)
        patterns = [
            (r'(\d{4})[-.]?(\d{1,2})[-.]?(\d{1,2})', 'YMD'),  # 2025-04-03 or 20250403
            (r'(\d{1,2})[-.]?(\d{1,2})[-.]?(\d{4})', 'MDY'),  # 04-03-2025 or 04.03.2025
            (r'(\d{1,2})[-.]?(\d{1,2})[-.]?(\d{2})(?!\d)', 'MDy'),  # 04-03-25 or 04.03.25
            (r'(\d{2})[-.]?(\d{1,2})[-.]?(\d{1,2})(?!\d)', 'yMD'),  # 25-04-03 or 25.04.03
        ]
        
        # Collect all valid dates found
        valid_dates = []
        
        for pattern, format_type in patterns:
            # Find all matches (not just first)
            for match in re.finditer(pattern, session_name):
                try:
                    if format_type == 'YMD':
                        year, month, day = match.groups()
                        year, month, day = int(year), int(month), int(day)
                    elif format_type == 'MDY':
                        month, day, year = match.groups()
                        month, day, year = int(month), int(day), int(year)
                    elif format_type == 'MDy':
                        month, day, year = match.groups()
                        month, day, year = int(month), int(day), int(year)
                        # Convert 2-digit year to 4-digit (20-40 = 20XX, else 19XX)
                        year = 2000 + year if year <= 40 else 1900 + year
                    elif format_type == 'yMD':
                        year, month, day = match.groups()
                        year, month, day = int(year), int(month), int(day)
                        # Convert 2-digit year to 4-digit
                        year = 2000 + year if year <= 40 else 1900 + year
                    
                    # Validate date components
                    if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                        date = datetime(year, month, day)
                        # Store with position for sorting (rightmost = closest to folder)
                        valid_dates.append((match.end(), date))
                except (ValueError, TypeError) as e:
                    # Invalid date, try next pattern
                    continue
        
        # Return the rightmost (closest to end of path) valid date
        if valid_dates:
            # Sort by position (descending) and return the date from the rightmost match
            valid_dates.sort(key=lambda x: x[0], reverse=True)
            selected_date = valid_dates[0][1]
            logger.info(f"Extracted date from '{session_name}': {selected_date.strftime('%Y-%m-%d')} (rightmost of {len(valid_dates)} found)")
            return selected_date
        
        logger.debug(f"No valid date found in session name: {session_name}")
        return None
    
    def extract_metadata_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract EXIF metadata from a single image file.
        
        Args:
            file_path: Path or URI to image file
        
        Returns:
            Dictionary with extracted metadata, or None if extraction fails
        
        Example:
            >>> metadata = extractor.extract_metadata_from_file('/photos/DSC05760.ARW')
            >>> print(metadata['Camera'])
            'SONY ILCE-7SM3'
        """
        try:
            with exiftool.ExifTool() as et:
                output = et.execute("-j", file_path)
                
                metadata_list = json.loads(output)
                if not metadata_list:
                    logger.warning(f"No metadata found for: {file_path}")
                    return None
                
                metadata = metadata_list[0]
                
                # Convert exposure time to fraction
                exposure_time = metadata.get("EXIF:ExposureTime", "")
                if exposure_time and isinstance(exposure_time, (int, float, str)):
                    try:
                        exposure_time_float = float(exposure_time)
                        exposure_time_fraction = Fraction(exposure_time_float).limit_denominator()
                        exposure_time_str = f"{exposure_time_fraction.numerator}/{exposure_time_fraction.denominator}"
                    except (ValueError, ZeroDivisionError):
                        exposure_time_str = str(exposure_time)
                else:
                    exposure_time_str = ""
                
                # Map exposure program codes
                exposure_program_map = {
                    0: "Not defined", 1: "Manual", 2: "Normal program",
                    3: "Aperture priority", 4: "Shutter priority", 5: "Creative program",
                    6: "Action program", 7: "Portrait mode", 8: "Landscape mode"
                }
                exposure_program = metadata.get("EXIF:ExposureProgram", "")
                exposure_program_str = exposure_program_map.get(
                    exposure_program, 
                    f"Unknown ({exposure_program})" if exposure_program else ""
                )
                
                # Map flash mode codes
                flash_mode_map = {
                    0: "Flash off, no flash function", 1: "Flash fired", 
                    5: "Flash fired, return not detected",
                    7: "Flash fired, return detected", 
                    9: "Flash on, compulsory flash mode",
                    13: "Flash on, return not detected", 
                    16: "Flash off, no flash function"
                }
                flash_mode = metadata.get("EXIF:Flash", "")
                flash_mode_str = flash_mode_map.get(
                    flash_mode, 
                    f"Unknown ({flash_mode})" if flash_mode != "" else ""
                )
                
                # Extract date taken
                date_taken = None
                date_str = metadata.get("EXIF:DateTimeOriginal") or metadata.get("EXIF:CreateDate")
                if date_str:
                    try:
                        date_taken = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass
                
                # Get file info
                file_size = metadata.get("File:FileSize")
                if isinstance(file_size, str) and "bytes" in file_size:
                    file_size = int(file_size.split()[0])
                
                return {
                    "File": os.path.basename(file_path),
                    "FilePath": file_path,
                    "Camera": (metadata.get("EXIF:Make", "") + " " + 
                              metadata.get("EXIF:Model", "")).strip(),
                    "Lens": metadata.get('EXIF:LensModel', "Unknown"),
                    "FocalLength": metadata.get("EXIF:FocalLength", ""),
                    "ISO": metadata.get("EXIF:ISO", ""),
                    "Aperture": metadata.get("EXIF:FNumber", ""),
                    "ShutterSpeed": exposure_time_str,
                    "ExposureProgram": exposure_program_str,
                    "ExposureBias": metadata.get("EXIF:ExposureBiasValue", ""),
                    "FlashMode": flash_mode_str,
                    "DateTaken": date_taken,
                    "FileSize": file_size,
                    "Width": metadata.get("EXIF:ImageWidth") or metadata.get("File:ImageWidth"),
                    "Height": metadata.get("EXIF:ImageHeight") or metadata.get("File:ImageHeight"),
                }
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ExifTool output for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return None
    
    def count_raw_photos(self, raw_folder_path: str) -> Optional[int]:
        """
        Count RAW photos in a folder.
        
        Args:
            raw_folder_path: Path to RAW folder
        
        Returns:
            Count of RAW files, or None if folder doesn't exist
        """
        try:
            raw_files = self.storage.list_files(raw_folder_path, self.supported_extensions)
            return len(raw_files)
        except Exception as e:
            logger.warning(f"Could not count RAW files in {raw_folder_path}: {e}")
            return None
    
    def detect_raw_folder(self, edited_folder_path: str) -> Optional[str]:
        """
        Try to find a corresponding RAW folder one level above the edited folder.
        
        Checks if the parent directory (one level up) contains RAW files.
        This assumes structure like: /session/RAW/ and /session/Edits/
        
        Args:
            edited_folder_path: Path to the edited folder
        
        Returns:
            Path to RAW folder if found, None otherwise
        """
        # Get the parent directory (one level up from edits folder)
        parent_dir = os.path.dirname(edited_folder_path)
        
        # Check for common RAW folder names in the parent directory
        raw_folder_names = ['RAW', 'Raw', 'raw', 'RAW Files', 'Raws']
        
        for raw_name in raw_folder_names:
            raw_path = os.path.join(parent_dir, raw_name)
            if self.storage.file_exists(raw_path):
                logger.info(f"Found RAW folder: {raw_path}")
                return raw_path
        
        logger.info(f"No RAW folder found for {edited_folder_path} - will skip hit rate calculation")
        return None
    
    def extract_folder(self, folder_path: str, session_name: str,
                      category: str, group: str,
                      raw_folder_path: Optional[str] = None,
                      description: Optional[str] = None,
                      calculate_hit_rate: bool = True,
                      date: Optional[datetime] = None,
                      use_date_heuristics: bool = True) -> Optional[Session]:
        """
        Extract metadata from all photos in a folder and create session.
        
        Args:
            folder_path: Path to folder containing photos
            session_name: Name for the session
            category: Category name
            group: Group name within category
            description: Optional session description
            calculate_hit_rate: Whether to calculate hit rate (requires RAW folder)
            date: Optional explicit date for the session
            use_date_heuristics: Whether to extract date from session name if not provided
        
        Returns:
            Created Session instance with all photos
        
        Example:
            >>> session = extractor.extract_folder(
            ...     '/photos/running_sole/01_-_2025-04-03',
            ...     session_name='01_-_2025-04-03',
            ...     category='running_sole',
            ...     group='running_sole'
            ... )
            >>> print(f"Extracted {session.total_photos} photos")
        """
        logger.info(f"Extracting metadata from: {folder_path}")
        
        # Check if session already exists
        existing_session = self.db.get_session_by_name(session_name, category, group)
        if existing_session:
            logger.info(f"Session already exists: {session_name}")
            return existing_session
        
        # Get list of image files
        image_files = self.storage.list_files(folder_path, self.supported_extensions)
        logger.info(f"Found {len(image_files)} image files")
        
        if not image_files:
            logger.warning(f"No image files found in {folder_path}")
            return None
        
        # Extract date using heuristics if enabled and no explicit date provided
        # Use folder path (which is more likely to contain dates) rather than custom session name
        session_date = date
        if not session_date and use_date_heuristics:
            # Try to extract date from the full folder path
            # First try the immediate folder name, then work backwards through parent folders
            logger.info(f"Date heuristics enabled. Analyzing path: '{folder_path}'")
            
            # Try extracting from full path first (most specific to least specific)
            session_date = self.extract_date_from_session_name(folder_path)
            
            if session_date:
                logger.info(f"Date successfully extracted from path: {session_date.strftime('%Y-%m-%d')}")
            else:
                logger.info(f"No date pattern found in path: '{folder_path}'")
        
        logger.info(f"Creating Session object with date: {session_date} (type: {type(session_date)})")
        
        # Create session
        session = Session(
            name=session_name,
            category=category,
            group=group,
            description=description,
            folder_path=folder_path,
            total_photos=len(image_files),
            date=session_date
        )
        
        # Try to detect and count RAW folder (optional feature)
        # Only calculates if RAW folder exists one level above
        if calculate_hit_rate:
            raw_folder = self.detect_raw_folder(folder_path)
            if raw_folder:
                session.raw_folder_path = raw_folder
                raw_count = self.count_raw_photos(raw_folder)
                if raw_count and raw_count > 0:
                    session.total_raw_photos = raw_count
                    session.calculate_hit_rate(raw_count)
                    logger.info(f"Hit rate: {session.hit_rate:.1f}% ({session.total_photos}/{raw_count})")
            else:
                # No RAW folder found - set to None (will be NULL in database)
                session.raw_folder_path = None
                session.total_raw_photos = None
                session.hit_rate = None
                logger.info(f"No RAW folder - focusing on {session.total_photos} final edits only")
        
        # Save session to database
        session = self.db.create_session(session)
        logger.info(f"Created session: {session.name} (ID: {session.id})")
        
        # Extract and save photo metadata
        photo_count = 0
        for file_path in image_files:
            try:
                metadata_dict = self.extract_metadata_from_file(file_path)
                if not metadata_dict:
                    continue
                
                # Create PhotoMetadata instance
                photo = PhotoMetadata(
                    session_id=session.id,
                    file_path=metadata_dict['FilePath'],
                    file_name=metadata_dict['File'],
                    camera=metadata_dict['Camera'],
                    lens=metadata_dict['Lens'],
                    focal_length=metadata_dict['FocalLength'],
                    iso=metadata_dict['ISO'],
                    aperture=metadata_dict['Aperture'],
                    shutter_speed=metadata_dict['ShutterSpeed'],
                    exposure_program=metadata_dict['ExposureProgram'],
                    exposure_bias=metadata_dict['ExposureBias'],
                    flash_mode=metadata_dict['FlashMode'],
                    date_taken=metadata_dict['DateTaken'],
                    file_size=metadata_dict['FileSize'],
                    width=metadata_dict['Width'],
                    height=metadata_dict['Height'],
                )
                
                # Save to database
                photo = self.db.create_photo(photo)
                session.add_photo(photo)
                photo_count += 1
                
                logger.debug(f"  Processed: {photo.file_name}")
            
            except Exception as e:
                logger.error(f"  Error processing {file_path}: {e}")
        
        logger.info(f"Successfully extracted {photo_count} photos for session {session.name}")
        
        # Update session photo count
        session.total_photos = photo_count
        self.db.update_session(session)
        
        return session
    
    def extract_multiple_folders(self, folder_configs: List[Dict[str, str]]) -> List[Session]:
        """
        Extract metadata from multiple folders.
        
        Args:
            folder_configs: List of dicts with keys: folder_path, session_name, category, group
        
        Returns:
            List of created Session instances
        
        Example:
            >>> configs = [
            ...     {
            ...         'folder_path': '/photos/session1',
            ...         'session_name': 'session1',
            ...         'category': 'running',
            ...         'group': 'weekly'
            ...     },
            ...     {
            ...         'folder_path': '/photos/session2',
            ...         'session_name': 'session2',
            ...         'category': 'running',
            ...         'group': 'weekly'
            ...     }
            ... ]
            >>> sessions = extractor.extract_multiple_folders(configs)
        """
        sessions = []
        
        for i, config in enumerate(folder_configs, 1):
            logger.info(f"Processing folder {i}/{len(folder_configs)}")
            
            session = self.extract_folder(
                folder_path=config['folder_path'],
                session_name=config['session_name'],
                category=config['category'],
                group=config['group'],
                description=config.get('description'),  # type: ignore
                calculate_hit_rate=bool(config.get('calculate_hit_rate', True))
            )
            
            if session:
                sessions.append(session)
        
        logger.info(f"Completed extraction of {len(sessions)} sessions")
        return sessions
