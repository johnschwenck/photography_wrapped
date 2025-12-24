"""
Photo Metadata Model

Represents EXIF metadata extracted from a single photograph.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from fractions import Fraction


@dataclass
class PhotoMetadata:
    """
    Represents EXIF metadata for a single photograph.
    
    This class encapsulates all relevant metadata extracted from a photo file,
    including camera settings, lens information, and exposure parameters.
    
    Attributes:
        id: Unique identifier (database primary key)
        session_id: Foreign key to the session this photo belongs to
        file_path: Full path or URI to the photo file
        file_name: Name of the photo file
        camera: Camera model name
        lens: Lens model name
        focal_length: Focal length in millimeters
        iso: ISO sensitivity value
        aperture: Aperture f-number (e.g., 2.8)
        shutter_speed: Shutter speed as string (e.g., "1/125")
        shutter_speed_decimal: Shutter speed as decimal for calculations
        exposure_program: Exposure mode (Manual, Aperture Priority, etc.)
        exposure_bias: Exposure compensation value
        flash_mode: Flash setting/status
        date_taken: Timestamp when photo was captured
        file_size: Size of file in bytes
        width: Image width in pixels
        height: Image height in pixels
        created_at: When this record was created in database
        updated_at: When this record was last updated
    
    Example:
        >>> photo = PhotoMetadata(
        ...     file_name="DSC05760.ARW",
        ...     camera="SONY ILCE-7SM3",
        ...     lens="FE 135mm F1.8 GM",
        ...     iso=3200,
        ...     aperture=1.8,
        ...     shutter_speed="1/125"
        ... )
    """
    
    # Required fields
    file_name: str
    camera: str
    lens: str
    
    # Optional fields with defaults
    id: Optional[int] = None
    session_id: Optional[int] = None
    file_path: Optional[str] = None
    focal_length: Optional[float] = None
    iso: Optional[int] = None
    aperture: Optional[float] = None
    shutter_speed: Optional[str] = None
    shutter_speed_decimal: Optional[float] = None
    exposure_program: Optional[str] = None
    exposure_bias: Optional[float] = None
    flash_mode: Optional[str] = None
    date_taken: Optional[datetime] = None
    date_only: Optional[str] = None
    time_only: Optional[str] = None
    day_of_week: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """
        Post-initialization processing.
        
        Converts shutter speed string to decimal if not already set.
        Populates date_only, time_only, and day_of_week from date_taken.
        """
        if self.shutter_speed and not self.shutter_speed_decimal:
            self.shutter_speed_decimal = self._convert_shutter_speed_to_decimal(
                self.shutter_speed
            )
        
        # Populate date/time fields from date_taken
        if self.date_taken and not self.date_only:
            self.date_only = self.date_taken.strftime('%Y-%m-%d')
            self.time_only = self.date_taken.strftime('%H:%M:%S')
            self.day_of_week = self.date_taken.strftime('%A')
    
    @staticmethod
    def _convert_shutter_speed_to_decimal(shutter_speed: str) -> Optional[float]:
        """
        Convert shutter speed string to decimal seconds.
        
        Args:
            shutter_speed: Shutter speed as string (e.g., "1/125", "2.5")
        
        Returns:
            Shutter speed in decimal seconds, or None if conversion fails
        
        Example:
            >>> PhotoMetadata._convert_shutter_speed_to_decimal("1/125")
            0.008
            >>> PhotoMetadata._convert_shutter_speed_to_decimal("2.5")
            2.5
        """
        if not shutter_speed or shutter_speed == "":
            return None
        
        try:
            # Handle fractional notation (e.g., "1/125")
            if "/" in shutter_speed:
                fraction = Fraction(shutter_speed)
                return float(fraction)
            # Handle decimal notation (e.g., "2.5")
            else:
                return float(shutter_speed)
        except (ValueError, ZeroDivisionError):
            return None
    
    def to_dict(self) -> dict:
        """
        Convert photo metadata to dictionary representation.
        
        Returns:
            Dictionary with all photo metadata fields
        """
        return {
            'id': self.id,
            'session_id': self.session_id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'camera': self.camera,
            'lens': self.lens,
            'focal_length': self.focal_length,
            'iso': self.iso,
            'aperture': self.aperture,
            'shutter_speed': self.shutter_speed,
            'shutter_speed_decimal': self.shutter_speed_decimal,
            'exposure_program': self.exposure_program,
            'exposure_bias': self.exposure_bias,
            'flash_mode': self.flash_mode,
            'date_taken': self.date_taken.isoformat() if self.date_taken else None,
            'file_size': self.file_size,
            'width': self.width,
            'height': self.height,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PhotoMetadata':
        """
        Create PhotoMetadata instance from dictionary.
        
        Args:
            data: Dictionary containing photo metadata fields
        
        Returns:
            PhotoMetadata instance
        """
        # Convert datetime strings to datetime objects
        if data.get('date_taken') and isinstance(data['date_taken'], str):
            data['date_taken'] = datetime.fromisoformat(data['date_taken'])
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at') and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)
    
    def __repr__(self) -> str:
        """String representation of PhotoMetadata."""
        return (
            f"PhotoMetadata(file_name='{self.file_name}', "
            f"lens='{self.lens}', iso={self.iso}, "
            f"aperture={self.aperture}, shutter_speed='{self.shutter_speed}')"
        )
