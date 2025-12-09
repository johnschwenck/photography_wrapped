"""
Lens Model

Represents a camera lens with its characteristics and usage statistics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any, TYPE_CHECKING
from collections import Counter
import re

if TYPE_CHECKING:
    from models.photo_metadata import PhotoMetadata


class LensType(Enum):
    """Enumeration of lens types."""
    PRIME = "prime"
    ZOOM = "zoom"
    UNKNOWN = "unknown"


@dataclass
class Lens:
    """
    Represents a camera lens and its usage statistics.
    
    This class encapsulates lens information including its type (prime vs zoom),
    usage counts, and aggregated settings across all photos taken with this lens.
    
    Attributes:
        id: Unique identifier (database primary key)
        name: Full lens model name
        lens_type: Type of lens (PRIME, ZOOM, or UNKNOWN)
        manufacturer: Lens manufacturer (Sony, Sigma, etc.)
        focal_length_min: Minimum focal length for zoom lenses, or fixed for prime
        focal_length_max: Maximum focal length for zoom lenses
        max_aperture: Maximum aperture (smallest f-number)
        usage_count: Total number of photos taken with this lens
        shutter_speeds: Counter of shutter speed usage
        apertures: Counter of aperture usage
        isos: Counter of ISO usage
        exposure_programs: Counter of exposure program usage
        flash_modes: Counter of flash mode usage
        focal_lengths: Counter of focal length usage (for zoom lenses)
    
    Example:
        >>> lens = Lens(
        ...     name="FE 135mm F1.8 GM",
        ...     lens_type=LensType.PRIME,
        ...     manufacturer="Sony",
        ...     focal_length_min=135,
        ...     max_aperture=1.8
        ... )
        >>> lens.classify_type()
        LensType.PRIME
    """
    
    name: str
    id: Optional[int] = None
    lens_type: LensType = LensType.UNKNOWN
    manufacturer: Optional[str] = None
    focal_length_min: Optional[float] = None
    focal_length_max: Optional[float] = None
    max_aperture: Optional[float] = None
    usage_count: int = 0
    
    # Usage statistics
    shutter_speeds: Counter = field(default_factory=Counter)
    apertures: Counter = field(default_factory=Counter)
    isos: Counter = field(default_factory=Counter)
    exposure_programs: Counter = field(default_factory=Counter)
    flash_modes: Counter = field(default_factory=Counter)
    focal_lengths: Counter = field(default_factory=Counter)
    
    def classify_type(self) -> LensType:
        """
        Automatically classify lens type based on name.
        
        Analyzes the lens name to determine if it's a prime (fixed focal length)
        or zoom (variable focal length) lens.
        
        Returns:
            LensType.PRIME, LensType.ZOOM, or LensType.UNKNOWN
        
        Example:
            >>> lens = Lens(name="FE 85mm F1.4 GM II")
            >>> lens.classify_type()
            LensType.PRIME
            >>> lens = Lens(name="24-70mm F2.8 DG DN | Art 019")
            >>> lens.classify_type()
            LensType.ZOOM
        """
        # Zoom lens pattern: contains "XX-YYmm"
        zoom_pattern = r'\d+-\d+mm'
        if re.search(zoom_pattern, self.name):
            self.lens_type = LensType.ZOOM
            
            # Extract focal length range
            match = re.search(r'(\d+)-(\d+)mm', self.name)
            if match:
                self.focal_length_min = float(match.group(1))
                self.focal_length_max = float(match.group(2))
            
            return LensType.ZOOM
        
        # Prime lens pattern: single focal length "XXmm"
        prime_pattern = r'(?<!\d)(\d+(?:\.\d+)?)mm(?!\s*-)'
        if re.search(prime_pattern, self.name):
            self.lens_type = LensType.PRIME
            
            # Extract fixed focal length
            match = re.search(r'(?<!\d)(\d+(?:\.\d+)?)mm', self.name)
            if match:
                self.focal_length_min = float(match.group(1))
                self.focal_length_max = self.focal_length_min
            
            return LensType.PRIME
        
        self.lens_type = LensType.UNKNOWN
        return LensType.UNKNOWN
    
    def extract_max_aperture(self) -> Optional[float]:
        """
        Extract maximum aperture from lens name.
        
        Returns:
            Maximum aperture (smallest f-number) or None if not found
        
        Example:
            >>> lens = Lens(name="FE 85mm F1.4 GM II")
            >>> lens.extract_max_aperture()
            1.4
        """
        # Pattern for aperture: F followed by number
        aperture_pattern = r'[Ff](\d+(?:\.\d+)?)'
        match = re.search(aperture_pattern, self.name)
        
        if match:
            self.max_aperture = float(match.group(1))
            return self.max_aperture
        
        return None
    
    def extract_manufacturer(self) -> Optional[str]:
        """
        Extract manufacturer from lens name.
        
        Returns:
            Manufacturer name or None if not determinable
        
        Example:
            >>> lens = Lens(name="FE 85mm F1.4 GM II")
            >>> lens.extract_manufacturer()
            'Sony'
            >>> lens = Lens(name="24-70mm F2.8 DG DN | Art 019")
            >>> lens.extract_manufacturer()
            'Sigma'
        """
        name_lower = self.name.lower()
        
        # Sony patterns
        if any(pattern in name_lower for pattern in ['fe ', 'gm', 'g master', 'zeiss']):
            self.manufacturer = 'Sony'
            return 'Sony'
        
        # Sigma patterns
        if any(pattern in name_lower for pattern in ['dg dn', 'art', 'contemporary', 'sports']):
            self.manufacturer = 'Sigma'
            return 'Sigma'
        
        # Canon patterns
        if any(pattern in name_lower for pattern in ['ef ', 'rf ', 'canon']):
            self.manufacturer = 'Canon'
            return 'Canon'
        
        # Nikon patterns
        if any(pattern in name_lower for pattern in ['nikkor', 'nikon']):
            self.manufacturer = 'Nikon'
            return 'Nikon'
        
        # Tamron patterns
        if 'tamron' in name_lower:
            self.manufacturer = 'Tamron'
            return 'Tamron'
        
        self.manufacturer = 'Unknown'
        return 'Unknown'
    
    def add_photo_stats(self, photo: 'PhotoMetadata'):
        """
        Add statistics from a photo taken with this lens.
        
        Args:
            photo: PhotoMetadata instance to aggregate stats from
        """
        from .photo_metadata import PhotoMetadata
        
        self.usage_count += 1
        
        if photo.shutter_speed:
            self.shutter_speeds[photo.shutter_speed] += 1
        if photo.aperture:
            self.apertures[photo.aperture] += 1
        if photo.iso:
            self.isos[photo.iso] += 1
        if photo.exposure_program:
            self.exposure_programs[photo.exposure_program] += 1
        if photo.flash_mode:
            self.flash_modes[photo.flash_mode] += 1
        if photo.focal_length and self.lens_type == LensType.ZOOM:
            self.focal_lengths[photo.focal_length] += 1
    
    def get_most_common_settings(self) -> Dict[str, Any]:
        """
        Get the most commonly used settings with this lens.
        
        Returns:
            Dictionary with most common shutter speed, aperture, ISO, etc.
        
        Example:
            >>> settings = lens.get_most_common_settings()
            >>> print(settings['shutter_speed'])
            ('1/200', 46)
        """
        return {
            'shutter_speed': self.shutter_speeds.most_common(1)[0] if self.shutter_speeds else None,
            'aperture': self.apertures.most_common(1)[0] if self.apertures else None,
            'iso': self.isos.most_common(1)[0] if self.isos else None,
            'exposure_program': self.exposure_programs.most_common(1)[0] if self.exposure_programs else None,
            'flash_mode': self.flash_modes.most_common(1)[0] if self.flash_modes else None,
        }
    
    def to_dict(self) -> dict:
        """
        Convert lens to dictionary representation.
        
        Returns:
            Dictionary with all lens fields
        """
        return {
            'id': self.id,
            'name': self.name,
            'lens_type': self.lens_type.value,
            'manufacturer': self.manufacturer,
            'focal_length_min': self.focal_length_min,
            'focal_length_max': self.focal_length_max,
            'max_aperture': self.max_aperture,
            'usage_count': self.usage_count,
            'shutter_speeds': dict(self.shutter_speeds),
            'apertures': dict(self.apertures),
            'isos': dict(self.isos),
            'exposure_programs': dict(self.exposure_programs),
            'flash_modes': dict(self.flash_modes),
            'focal_lengths': dict(self.focal_lengths),
        }
    
    def __repr__(self) -> str:
        """String representation of Lens."""
        return (
            f"Lens(name='{self.name}', type={self.lens_type.value}, "
            f"usage_count={self.usage_count})"
        )
