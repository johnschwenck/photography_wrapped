"""
Session Model

Represents a photography session with associated photos and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from collections import Counter

if TYPE_CHECKING:
    from models.photo_metadata import PhotoMetadata


@dataclass
class Session:
    """
    Represents a photography session (event).
    
    A session is a collection of photos taken during a single event, shoot,
    or occasion. It tracks all metadata about the session and provides
    methods to calculate statistics.
    
    Attributes:
        id: Unique identifier (database primary key)
        name: Session name (e.g., "01_-_2025-04-03")
        category: Category this session belongs to (e.g., "running_sole")
        group: Group within category (e.g., "running_sole")
        date: Date of the session
        location: Optional location information
        description: Optional description
        folder_path: Path to folder containing photos
        raw_folder_path: Path to folder containing RAW files (for hit rate)
        photos: List of PhotoMetadata objects in this session
        total_photos: Total number of edited photos
        total_raw_photos: Total number of RAW photos (if applicable)
        hit_rate: Percentage of RAW photos that were edited
        created_at: When this record was created
        updated_at: When this record was last updated
    
    Example:
        >>> session = Session(
        ...     name="01_-_2025-04-03",
        ...     category="running_sole",
        ...     group="running_sole",
        ...     date=datetime(2025, 4, 3)
        ... )
        >>> session.add_photo(photo1)
        >>> session.add_photo(photo2)
        >>> stats = session.calculate_statistics()
    """
    
    name: str
    category: str
    group: str
    
    id: Optional[int] = None
    date: Optional[datetime] = None
    date_detected: Optional[str] = None  # How date was determined (e.g., "path", "filename (2 different dates, using most common (3/5 files))")
    location: Optional[str] = None
    description: Optional[str] = None
    folder_path: Optional[str] = None
    raw_folder_path: Optional[str] = None
    
    photos: List['PhotoMetadata'] = field(default_factory=list)
    total_photos: int = 0
    total_raw_photos: Optional[int] = None
    hit_rate: Optional[float] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def add_photo(self, photo: 'PhotoMetadata'):
        """
        Add a photo to this session.
        
        Args:
            photo: PhotoMetadata instance to add
        """
        from .photo_metadata import PhotoMetadata
        
        self.photos.append(photo)
        self.total_photos = len(self.photos)
    
    def calculate_hit_rate(self, raw_count: Optional[int] = None) -> Optional[float]:
        """
        Calculate the hit rate (edited photos / total RAW photos).
        
        Args:
            raw_count: Number of RAW photos. If None, uses total_raw_photos
        
        Returns:
            Hit rate as percentage (0-100), or None if RAW count unavailable
        
        Example:
            >>> session.total_photos = 168
            >>> session.calculate_hit_rate(500)
            33.6
        """
        if raw_count is not None:
            self.total_raw_photos = raw_count
        
        if self.total_raw_photos and self.total_raw_photos > 0:
            self.hit_rate = (self.total_photos / self.total_raw_photos) * 100
            return self.hit_rate
        
        return None
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for this session.
        
        Returns:
            Dictionary containing all calculated statistics including:
            - Total photo count
            - Lens frequency and breakdown
            - Shutter speed distribution
            - Aperture distribution
            - ISO distribution
            - Exposure program frequency
            - Flash mode frequency
            - Prime vs zoom counts
        
        Example:
            >>> stats = session.calculate_statistics()
            >>> print(stats['total_count'])
            168
            >>> print(stats['lens_freq'].most_common(1))
            [('FE 135mm F1.8 GM', 86)]
        """
        stats = {
            'name': self.name,
            'category': self.category,
            'group': self.group,
            'date': self.date,
            'total_count': self.total_photos,
            'hit_rate': self.hit_rate,
            'lens_freq': Counter(),
            'camera_freq': Counter(),
            'shutter_speed_freq': Counter(),
            'aperture_freq': Counter(),
            'iso_freq': Counter(),
            'exposure_program_freq': Counter(),
            'flash_mode_freq': Counter(),
            'focal_length_freq': Counter(),
            'exposure_bias_freq': Counter(),
            # 'time_of_day_freq': Counter(),  # Not yet implemented in PhotoMetadata
            'lens_breakdowns': {},
            'prime_count': 0,
            'zoom_count': 0,
        }
        
        # Import here to avoid circular imports
        from .lens import Lens, LensType
        
        # Aggregate statistics from all photos
        for photo in self.photos:
            # Overall frequency counters
            if photo.lens:
                stats['lens_freq'][photo.lens] += 1
            if photo.camera:
                stats['camera_freq'][photo.camera] += 1
            if photo.shutter_speed:
                stats['shutter_speed_freq'][photo.shutter_speed] += 1
            if photo.aperture:
                stats['aperture_freq'][photo.aperture] += 1
            if photo.iso:
                stats['iso_freq'][photo.iso] += 1
            if photo.exposure_program:
                stats['exposure_program_freq'][photo.exposure_program] += 1
            if photo.flash_mode:
                stats['flash_mode_freq'][photo.flash_mode] += 1
            if photo.focal_length:
                stats['focal_length_freq'][photo.focal_length] += 1
            if photo.exposure_bias:
                stats['exposure_bias_freq'][photo.exposure_bias] += 1
            # Note: time_of_day not available in PhotoMetadata model yet
            
            # Lens-specific breakdown
            if photo.lens:
                if photo.lens not in stats['lens_breakdowns']:
                    stats['lens_breakdowns'][photo.lens] = {
                        'Count': 0,
                        'ShutterSpeed': Counter(),
                        'Aperture': Counter(),
                        'ISO': Counter(),
                        'ExposureProgram': Counter(),
                        'FlashMode': Counter(),
                        'FocalLength': Counter(),
                    }
                
                breakdown = stats['lens_breakdowns'][photo.lens]
                breakdown['Count'] += 1
                
                if photo.shutter_speed:
                    breakdown['ShutterSpeed'][photo.shutter_speed] += 1
                if photo.aperture:
                    breakdown['Aperture'][photo.aperture] += 1
                if photo.iso:
                    breakdown['ISO'][photo.iso] += 1
                if photo.exposure_program:
                    breakdown['ExposureProgram'][photo.exposure_program] += 1
                if photo.flash_mode:
                    breakdown['FlashMode'][photo.flash_mode] += 1
                if photo.focal_length:
                    breakdown['FocalLength'][photo.focal_length] += 1
                
                # Classify as prime or zoom
                lens = Lens(name=photo.lens)
                lens_type = lens.classify_type()
                
                if lens_type == LensType.PRIME:
                    stats['prime_count'] += 1
                elif lens_type == LensType.ZOOM:
                    stats['zoom_count'] += 1
        
        return stats
    
    def get_lens_summary(self) -> Dict[str, int]:
        """
        Get summary of lens usage in this session.
        
        Returns:
            Dictionary mapping lens names to usage counts
        
        Example:
            >>> summary = session.get_lens_summary()
            >>> print(summary)
            {'FE 135mm F1.8 GM': 86, 'FE 85mm F1.4 GM II': 56, ...}
        """
        lens_counts = Counter()
        for photo in self.photos:
            if photo.lens:
                lens_counts[photo.lens] += 1
        
        return dict(lens_counts)
    
    def to_dict(self) -> dict:
        """
        Convert session to dictionary representation.
        
        Returns:
            Dictionary with all session fields
        """
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'group': self.group,
            'date': self.date.isoformat() if self.date else None,
            'location': self.location,
            'description': self.description,
            'folder_path': self.folder_path,
            'raw_folder_path': self.raw_folder_path,
            'total_photos': self.total_photos,
            'total_raw_photos': self.total_raw_photos,
            'hit_rate': self.hit_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Session':
        """
        Create Session instance from dictionary.
        
        Args:
            data: Dictionary containing session fields
        
        Returns:
            Session instance
        """
        # Convert datetime strings to datetime objects
        if data.get('date') and isinstance(data['date'], str):
            data['date'] = datetime.fromisoformat(data['date'])
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at') and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Remove photos list if present (loaded separately)
        data.pop('photos', None)
        
        return cls(**data)
    
    def __repr__(self) -> str:
        """String representation of Session."""
        return (
            f"Session(name='{self.name}', category='{self.category}', "
            f"total_photos={self.total_photos}, hit_rate={self.hit_rate})"
        )
