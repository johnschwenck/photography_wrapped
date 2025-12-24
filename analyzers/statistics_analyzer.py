"""
Statistics Analyzer

Calculates comprehensive statistics from database and caches results.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import Counter

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Analysis, Session, AggregatedStats, Lens, LensType
from database import DatabaseManager

logger = logging.getLogger(__name__)


class StatisticsAnalyzer:
    """
    Analyzes photo metadata and generates comprehensive statistics.
    
    Calculates metrics from database, supports caching for performance,
    and provides flexible aggregation at session, group, or category level.
    
    Attributes:
        db: DatabaseManager instance
        enable_caching: Whether to cache aggregated statistics
    
    Example:
        >>> analyzer = StatisticsAnalyzer.from_config('config.yaml')
        >>> analysis = analyzer.analyze_sessions([session1.id, session2.id])
        >>> print(analysis.to_dict())
    """
    
    def __init__(self, db: DatabaseManager, enable_caching: bool = True):
        """
        Initialize statistics analyzer.
        
        Args:
            db: DatabaseManager instance
            enable_caching: Enable caching of aggregated statistics
        """
        self.db = db
        self.enable_caching = enable_caching
    
    @classmethod
    def from_config(cls, config_path: str = 'config.yaml') -> 'StatisticsAnalyzer':
        """Create StatisticsAnalyzer from configuration file."""
        import yaml
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        db = DatabaseManager.from_config(config_path)
        enable_caching = config.get('analysis', {}).get('enable_caching', True)
        
        return cls(db=db, enable_caching=enable_caching)
    
    def analyze_session(self, session_id: int) -> Analysis:
        """
        Analyze a single session.
        
        Args:
            session_id: Session ID to analyze
        
        Returns:
            Analysis instance with calculated statistics
        """
        session = self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Get all photos for session
        photos = self.db.get_photos_by_session(session_id)
        session.photos = photos
        
        # Calculate statistics
        stats = session.calculate_statistics()
        
        # Create Analysis object
        analysis = Analysis(name=session.name)
        analysis.add_session_stats(stats)
        analysis.hit_rate = session.hit_rate
        analysis.total_raw_photos = session.total_raw_photos or 0
        
        return analysis
    
    def analyze_sessions(self, session_ids: List[int], name: str = "Combined Analysis", include_photos: bool = True) -> Analysis:
        """
        Analyze multiple sessions together.
        
        Args:
            session_ids: List of session IDs to analyze
            name: Name for the combined analysis
        
        Returns:
            Analysis instance with aggregated statistics
        """
        analysis = Analysis(name=name)
        total_raw = 0
        all_photos = []
        
        # Get session info map (name, category, group)
        session_map = {}
        for session_id in session_ids:
            session_row = self.db.conn.execute(
                "SELECT name, category, group_name FROM sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if session_row:
                session_map[session_id] = {
                    'name': session_row['name'],
                    'category': session_row['category'],
                    'group': session_row['group_name']
                }
        
        for session_id in session_ids:
            session = self.db.get_session(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}")
                continue
            
            photos = self.db.get_photos_by_session(session_id)
            session.photos = photos
            all_photos.extend(photos)
            
            stats = session.calculate_statistics()
            analysis.add_session_stats(stats)
            
            analysis.sessions.append(session_id)
            
            if session.total_raw_photos:
                total_raw += session.total_raw_photos
        
        # Calculate overall hit rate
        analysis.total_raw_photos = total_raw
        if total_raw > 0:
            analysis.calculate_aggregated_hit_rate(total_raw)
        
        if include_photos:
            # Build photo details array
            photo_details = []
            for photo in all_photos:
                session_info = session_map.get(photo.session_id, {'name': 'Unknown', 'category': None, 'group': None})
                photo_details.append({
                    'date_taken': photo.date_taken.strftime('%Y-%m-%d') if photo.date_taken else None,
                    'date_only': photo.date_only,
                    'time_only': photo.time_only,
                    'day_of_week': photo.day_of_week,
                    'category': session_info['category'] or 'Uncategorized',
                    'group': session_info['group'] or 'Ungrouped',
                    'session_name': session_info['name'],
                    'camera': photo.camera or 'Unknown',
                    'lens': photo.lens or 'Unknown',
                    'aperture': str(photo.aperture) if photo.aperture else None,
                    'shutter_speed': photo.shutter_speed,
                    'iso': str(photo.iso) if photo.iso else None,
                    'focal_length': str(photo.focal_length) if photo.focal_length else None,
                    'filename': photo.file_name,
                    'file_path': photo.file_path
                })

            analysis.photos = photo_details
        
        return analysis
    
    def analyze_group(self, group_name: str, category_name: str = None) -> Analysis:
        """
        Analyze all sessions in a group.
        
        Args:
            group_name: Name of the group
            category_name: Optional name of the category to filter by
        
        Returns:
            Analysis instance for the group
        """
        if category_name:
            sessions = self.db.list_sessions(category=category_name, group=group_name)
        else:
            # Get all sessions with this group name regardless of category
            sessions = [s for s in self.db.list_sessions() if s.group == group_name]
        
        session_ids = [s.id for s in sessions if s.id is not None]
        
        name_parts = [category_name, group_name] if category_name else [group_name]
        analysis = self.analyze_sessions(
            session_ids,
            name=" - ".join(name_parts)
        )
        
        # Store metadata
        if category_name:
            analysis.metadata['category'] = category_name
        analysis.metadata['group'] = group_name
        
        # Cache if enabled
        if self.enable_caching:
            self._cache_aggregated_stats(analysis, 'group', group_name)
        
        return analysis
    
    def analyze_category(self, category_name: str) -> Analysis:
        """
        Analyze all sessions in a category.
        
        Args:
            category_name: Name of the category
        
        Returns:
            Analysis instance for the category
        """
        sessions = self.db.list_sessions(category=category_name)
        session_ids = [s.id for s in sessions if s.id is not None]
        
        analysis = self.analyze_sessions(
            session_ids,
            name=f"{category_name} - All"
        )
        
        # Store category metadata
        analysis.metadata['category'] = category_name
        
        # Add groups breakdown
        groups = {}
        for session in sessions:
            grp = session.group or 'Ungrouped'
            if grp not in groups:
                groups[grp] = {'sessions': 0, 'photos': 0}
            groups[grp]['sessions'] += 1
            groups[grp]['photos'] += session.total_photos
        analysis.metadata['groups'] = groups
        
        # Cache if enabled
        if self.enable_caching:
            self._cache_aggregated_stats(analysis, 'category', category_name)
        
        return analysis
    
    def _cache_aggregated_stats(self, analysis: Analysis, 
                                aggregation_type: str, aggregation_name: str):
        """
        Cache aggregated statistics to database.
        
        Args:
            analysis: Analysis instance to cache
            aggregation_type: Type of aggregation ('session', 'group', 'category')
            aggregation_name: Name of the aggregation
        """
        try:
            # Convert analysis to aggregated stats format
            lens_stats = {}
            for lens_name, breakdown in analysis.lens_breakdowns.items():
                lens_stats[lens_name] = {
                    'count': breakdown['Count'],
                    'shutter_speeds': dict(breakdown['ShutterSpeed']),
                    'apertures': dict(breakdown['Aperture']),
                    'isos': dict(breakdown['ISO']),
                    'exposure_programs': dict(breakdown['ExposureProgram']),
                    'flash_modes': dict(breakdown['FlashMode']),
                }
            
            settings_stats = {
                'lens_freq': dict(analysis.lens_freq),
                'shutter_speed_freq': dict(analysis.shutter_speed_freq),
                'aperture_freq': dict(analysis.aperture_freq),
                'iso_freq': dict(analysis.iso_freq),
                'exposure_program_freq': dict(analysis.exposure_program_freq),
                'flash_mode_freq': dict(analysis.flash_mode_freq),
                'prime_count': analysis.prime_count,
                'zoom_count': analysis.zoom_count,
            }
            
            aggregated = AggregatedStats(
                aggregation_type=aggregation_type,
                aggregation_name=aggregation_name,
                total_sessions=len(analysis.sessions),
                total_photos=analysis.total_photos,
                hit_rate=analysis.hit_rate,
                calculated_at=datetime.now()
            )
            
            aggregated.set_lens_statistics(lens_stats)
            aggregated.set_settings_statistics(settings_stats)
            
            # TODO: Implement save/update in db_manager
            logger.info(f"Cached statistics for {aggregation_type}: {aggregation_name}")
        
        except Exception as e:
            logger.error(f"Failed to cache statistics: {e}")
    
    def get_lens_usage_summary(self) -> Dict[str, Any]:
        """
        Get overall lens usage summary across all sessions.
        
        Returns:
            Dictionary with lens usage statistics
        """
        lenses = self.db.list_lenses()
        
        summary = {
            'total_lenses': len(lenses),
            'prime_lenses': [],
            'zoom_lenses': [],
            'by_manufacturer': Counter(),
            'most_used': [],
        }
        
        for lens in lenses:
            if lens.lens_type == LensType.PRIME:
                summary['prime_lenses'].append({
                    'name': lens.name,
                    'usage_count': lens.usage_count
                })
            elif lens.lens_type == LensType.ZOOM:
                summary['zoom_lenses'].append({
                    'name': lens.name,
                    'usage_count': lens.usage_count
                })
            
            if lens.manufacturer:
                summary['by_manufacturer'][lens.manufacturer] += lens.usage_count
        
        # Sort by usage
        summary['prime_lenses'].sort(key=lambda x: x['usage_count'], reverse=True)
        summary['zoom_lenses'].sort(key=lambda x: x['usage_count'], reverse=True)
        
        # Most used overall
        all_lenses = [(l.name, l.usage_count) for l in lenses]
        all_lenses.sort(key=lambda x: x[1], reverse=True)
        summary['most_used'] = all_lenses[:10]
        
        return summary
    
    def analyze_with_filters(self, session_ids: List[int], filters: dict, name: str = "Filtered Analysis", include_photos: bool = True) -> Analysis:
        """
        Analyze photos with metadata filters applied.
        
        Args:
            session_ids: List of session IDs to analyze
            filters: Dict of metadata filters (camera, lens, aperture, shutter_speed, iso, focal_length, time_of_day)
            name: Name for the filtered analysis
        
        Returns:
            Analysis instance with filtered statistics
        """
        if not session_ids:
            raise ValueError("No session IDs provided")
        
        # Get session info for session names, category, and group
        session_map = {}
        for session_id in session_ids:
            session_row = self.db.conn.execute(
                "SELECT name, category, group_name FROM sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if session_row:
                session_map[session_id] = {
                    'name': session_row['name'],
                    'category': session_row['category'],
                    'group': session_row['group_name']
                }
        
        # Get all photos from specified sessions
        all_photos = self.db.get_photos_by_sessions(session_ids)
        analysis, _filtered_photos = self.analyze_photos_with_filters_from_photos(
            all_photos,
            filters,
            name=name,
            include_photos=include_photos,
            session_map=session_map,
        )

        return analysis

    def _filter_photos(self, photos: List[Any], filters: dict) -> List[Any]:
        def _values_as_set(value) -> set:
            if value is None:
                return set()
            if isinstance(value, (list, tuple, set)):
                return set(value)
            return {value}

        def _values_as_str_set(value) -> set:
            return {str(v) for v in _values_as_set(value) if v is not None}

        filtered_photos = photos

        if 'camera' in filters:
            cameras = _values_as_set(filters['camera'])
            filtered_photos = [p for p in filtered_photos if p.camera in cameras]

        if 'lens' in filters:
            lenses = _values_as_set(filters['lens'])
            filtered_photos = [p for p in filtered_photos if p.lens in lenses]

        if 'aperture' in filters:
            apertures = _values_as_str_set(filters['aperture'])
            filtered_photos = [p for p in filtered_photos if p.aperture and str(p.aperture) in apertures]

        if 'shutter_speed' in filters:
            speeds = _values_as_set(filters['shutter_speed'])
            filtered_photos = [p for p in filtered_photos if p.shutter_speed in speeds]

        if 'iso' in filters:
            isos = _values_as_str_set(filters['iso'])
            filtered_photos = [p for p in filtered_photos if p.iso and str(p.iso) in isos]

        if 'focal_length' in filters:
            focal_values = []
            for v in _values_as_set(filters['focal_length']):
                try:
                    focal_values.append(float(v))
                except (TypeError, ValueError):
                    continue
            if focal_values:
                filtered_photos = [
                    p for p in filtered_photos
                    if p.focal_length and any(abs(float(p.focal_length) - fv) < 0.1 for fv in focal_values)
                ]

        if 'time_of_day' in filters:
            times = _values_as_set(filters['time_of_day'])
            filtered_photos = [p for p in filtered_photos if p.time_of_day in times]

        if 'lens_type' in filters:
            lens_type = filters['lens_type']
            if lens_type == 'prime':
                filtered_photos = [p for p in filtered_photos if p.lens and '-' not in p.lens]
            elif lens_type == 'zoom':
                filtered_photos = [p for p in filtered_photos if p.lens and '-' in p.lens]

        return filtered_photos

    def analyze_photos_with_filters_from_photos(
        self,
        photos: List[Any],
        filters: dict,
        name: str = "Filtered Analysis",
        include_photos: bool = False,
        session_map: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> (Analysis, List[Any]):
        """Analyze an in-memory photo list with filters applied.

        Returns both the Analysis and the filtered photo list (useful for faceting/metadata).
        """
        filtered_photos = self._filter_photos(photos, filters)

        from models.session import Session
        temp_session = Session(
            name=name,
            category="Filtered",
            group="Filtered"
        )
        temp_session.photos = filtered_photos
        temp_session.total_photos = len(filtered_photos)

        stats = temp_session.calculate_statistics()

        analysis = Analysis(name=name)
        analysis.add_session_stats(stats)

        if include_photos:
            photo_details = []
            smap = session_map or {}
            for photo in filtered_photos:
                session_info = smap.get(photo.session_id, {'name': 'Unknown', 'category': None, 'group': None})
                photo_details.append({
                    'date_taken': photo.date_taken.strftime('%Y-%m-%d') if photo.date_taken else None,
                    'date_only': photo.date_only,
                    'time_only': photo.time_only,
                    'day_of_week': photo.day_of_week,
                    'category': session_info['category'] or 'Uncategorized',
                    'group': session_info['group'] or 'Ungrouped',
                    'session_name': session_info['name'],
                    'camera': photo.camera or 'Unknown',
                    'lens': photo.lens or 'Unknown',
                    'aperture': str(photo.aperture) if photo.aperture else None,
                    'shutter_speed': photo.shutter_speed,
                    'iso': str(photo.iso) if photo.iso else None,
                    'focal_length': str(photo.focal_length) if photo.focal_length else None,
                    'filename': photo.file_name,
                    'file_path': photo.file_path
                })

            analysis.photos = photo_details

        return analysis, filtered_photos
