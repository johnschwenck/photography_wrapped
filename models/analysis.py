"""
Analysis Model

Represents aggregated analysis results across sessions, groups, or categories.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import Counter
import json


@dataclass
class AggregatedStats:
    """
    Represents aggregated statistics across multiple sessions.
    
    This class stores pre-calculated statistics that can be cached in the
    database to avoid recalculation. It supports aggregation at various
    levels: session, group, category, or custom filters.
    
    Attributes:
        id: Unique identifier (database primary key)
        aggregation_type: Type of aggregation (session, group, category, custom)
        aggregation_id: ID of the entity being aggregated (if applicable)
        aggregation_name: Name of the aggregation (e.g., "running_sole_2025")
        filter_criteria: JSON string of filter criteria used
        total_sessions: Number of sessions included
        total_photos: Total number of photos
        total_raw_photos: Total RAW photos (if applicable)
        hit_rate: Overall hit rate percentage
        lens_statistics: JSON string of lens usage statistics
        camera_statistics: JSON string of camera usage statistics
        settings_statistics: JSON string of settings distributions
        calculated_at: When these stats were calculated
        created_at: When this record was created
    
    Example:
        >>> stats = AggregatedStats(
        ...     aggregation_type="group",
        ...     aggregation_name="running_sole",
        ...     total_sessions=30,
        ...     total_photos=2565
        ... )
    """
    
    aggregation_type: str  # 'session', 'group', 'category', 'custom'
    aggregation_name: str
    
    id: Optional[int] = None
    aggregation_id: Optional[int] = None
    filter_criteria: Optional[str] = None
    total_sessions: int = 0
    total_photos: int = 0
    total_raw_photos: Optional[int] = None
    hit_rate: Optional[float] = None
    
    # JSON-serialized statistics
    lens_statistics: Optional[str] = None
    camera_statistics: Optional[str] = None
    settings_statistics: Optional[str] = None
    
    calculated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def set_lens_statistics(self, stats: Dict[str, Any]):
        """
        Set lens statistics from dictionary.
        
        Args:
            stats: Dictionary containing lens usage data
        """
        self.lens_statistics = json.dumps(stats)
    
    def get_lens_statistics(self) -> Dict[str, Any]:
        """
        Get lens statistics as dictionary.
        
        Returns:
            Dictionary containing lens usage data
        """
        if self.lens_statistics:
            return json.loads(self.lens_statistics)
        return {}
    
    def set_camera_statistics(self, stats: Dict[str, Any]):
        """Set camera statistics from dictionary."""
        self.camera_statistics = json.dumps(stats)
    
    def get_camera_statistics(self) -> Dict[str, Any]:
        """Get camera statistics as dictionary."""
        if self.camera_statistics:
            return json.loads(self.camera_statistics)
        return {}
    
    def set_settings_statistics(self, stats: Dict[str, Any]):
        """Set settings statistics from dictionary."""
        self.settings_statistics = json.dumps(stats)
    
    def get_settings_statistics(self) -> Dict[str, Any]:
        """Get settings statistics as dictionary."""
        if self.settings_statistics:
            return json.loads(self.settings_statistics)
        return {}
    
    def to_dict(self) -> dict:
        """Convert aggregated stats to dictionary."""
        return {
            'id': self.id,
            'aggregation_type': self.aggregation_type,
            'aggregation_id': self.aggregation_id,
            'aggregation_name': self.aggregation_name,
            'filter_criteria': self.filter_criteria,
            'total_sessions': self.total_sessions,
            'total_photos': self.total_photos,
            'total_raw_photos': self.total_raw_photos,
            'hit_rate': self.hit_rate,
            'lens_statistics': self.get_lens_statistics(),
            'camera_statistics': self.get_camera_statistics(),
            'settings_statistics': self.get_settings_statistics(),
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        """String representation of AggregatedStats."""
        return (
            f"AggregatedStats(type='{self.aggregation_type}', "
            f"name='{self.aggregation_name}', sessions={self.total_sessions}, "
            f"photos={self.total_photos})"
        )


@dataclass
class Analysis:
    """
    Represents a complete analysis with all statistics and breakdowns.
    
    This class provides a high-level interface for working with analysis
    results, including filtering, aggregation, and reporting capabilities.
    
    Attributes:
        name: Analysis name/title
        sessions: List of session IDs included
        total_photos: Total photos analyzed
        hit_rate: Overall hit rate
        lens_freq: Counter of lens usage
        shutter_speed_freq: Counter of shutter speed distribution
        aperture_freq: Counter of aperture distribution
        iso_freq: Counter of ISO distribution
        exposure_program_freq: Counter of exposure program usage
        flash_mode_freq: Counter of flash mode usage
        focal_length_freq: Counter of focal length distribution
        lens_breakdowns: Detailed per-lens statistics
        prime_count: Number of photos with prime lenses
        zoom_count: Number of photos with zoom lenses
        metadata: Additional metadata about the analysis
    
    Example:
        >>> analysis = Analysis(name="Running Club 2025 Q1")
        >>> analysis.add_session_stats(session.calculate_statistics())
        >>> report = analysis.generate_report()
    """
    
    name: str
    sessions: List[int] = field(default_factory=list)
    total_photos: int = 0
    total_raw_photos: int = 0
    hit_rate: Optional[float] = None
    
    # Frequency distributions
    lens_freq: Counter = field(default_factory=Counter)
    camera_freq: Counter = field(default_factory=Counter)
    shutter_speed_freq: Counter = field(default_factory=Counter)
    aperture_freq: Counter = field(default_factory=Counter)
    iso_freq: Counter = field(default_factory=Counter)
    exposure_program_freq: Counter = field(default_factory=Counter)
    flash_mode_freq: Counter = field(default_factory=Counter)
    focal_length_freq: Counter = field(default_factory=Counter)
    exposure_bias_freq: Counter = field(default_factory=Counter)
    time_of_day_freq: Counter = field(default_factory=Counter)
    
    # Detailed breakdowns
    lens_breakdowns: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Lens type counts
    prime_count: int = 0
    zoom_count: int = 0
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_session_stats(self, session_stats: Dict[str, Any]):
        """
        Add statistics from a session to this analysis.
        
        Args:
            session_stats: Statistics dictionary from Session.calculate_statistics()
        """
        self.total_photos += session_stats.get('total_count', 0)
        
        # Merge frequency counters
        self.lens_freq.update(session_stats.get('lens_freq', Counter()))
        self.camera_freq.update(session_stats.get('camera_freq', Counter()))
        self.shutter_speed_freq.update(session_stats.get('shutter_speed_freq', Counter()))
        self.aperture_freq.update(session_stats.get('aperture_freq', Counter()))
        self.iso_freq.update(session_stats.get('iso_freq', Counter()))
        self.exposure_program_freq.update(session_stats.get('exposure_program_freq', Counter()))
        self.flash_mode_freq.update(session_stats.get('flash_mode_freq', Counter()))
        self.focal_length_freq.update(session_stats.get('focal_length_freq', Counter()))
        self.exposure_bias_freq.update(session_stats.get('exposure_bias_freq', Counter()))
        self.time_of_day_freq.update(session_stats.get('time_of_day_freq', Counter()))
        
        # Merge lens breakdowns
        for lens_name, breakdown in session_stats.get('lens_breakdowns', {}).items():
            if lens_name not in self.lens_breakdowns:
                self.lens_breakdowns[lens_name] = {
                    'Count': 0,
                    'ShutterSpeed': Counter(),
                    'Aperture': Counter(),
                    'ISO': Counter(),
                    'ExposureProgram': Counter(),
                    'FlashMode': Counter(),
                    'FocalLength': Counter(),
                }
            
            self.lens_breakdowns[lens_name]['Count'] += breakdown['Count']
            self.lens_breakdowns[lens_name]['ShutterSpeed'].update(breakdown['ShutterSpeed'])
            self.lens_breakdowns[lens_name]['Aperture'].update(breakdown['Aperture'])
            self.lens_breakdowns[lens_name]['ISO'].update(breakdown['ISO'])
            self.lens_breakdowns[lens_name]['ExposureProgram'].update(breakdown['ExposureProgram'])
            self.lens_breakdowns[lens_name]['FlashMode'].update(breakdown['FlashMode'])
            self.lens_breakdowns[lens_name]['FocalLength'].update(breakdown['FocalLength'])
        
        # Add prime/zoom counts
        self.prime_count += session_stats.get('prime_count', 0)
        self.zoom_count += session_stats.get('zoom_count', 0)
    
    def calculate_aggregated_hit_rate(self, total_raw: int):
        """
        Calculate overall hit rate for aggregated sessions.
        
        Args:
            total_raw: Total number of RAW photos across all sessions
        """
        if total_raw > 0:
            self.hit_rate = (self.total_photos / total_raw) * 100
    
    def to_dict(self) -> dict:
        """Convert analysis to dictionary representation."""
        return {
            'name': self.name,
            'total_photos': self.total_photos,
            'total_raw_photos': self.total_raw_photos,
            'hit_rate': self.hit_rate,
            'lens_freq': dict(self.lens_freq),
            'camera_freq': dict(self.camera_freq),
            'shutter_speed_freq': dict(self.shutter_speed_freq),
            'aperture_freq': dict(self.aperture_freq),
            'iso_freq': dict(self.iso_freq),
            'exposure_program_freq': dict(self.exposure_program_freq),
            'flash_mode_freq': dict(self.flash_mode_freq),
            'focal_length_freq': dict(self.focal_length_freq),
            'exposure_bias_freq': dict(self.exposure_bias_freq),
            'time_of_day_freq': dict(self.time_of_day_freq),
            'lens_breakdowns': self.lens_breakdowns,
            'prime_count': self.prime_count,
            'zoom_count': self.zoom_count,
            'metadata': self.metadata,
        }
    
    def __repr__(self) -> str:
        """String representation of Analysis."""
        return (
            f"Analysis(name='{self.name}', total_photos={self.total_photos}, "
            f"lenses={len(self.lens_freq)}, hit_rate={self.hit_rate})"
        )
