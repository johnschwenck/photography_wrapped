"""
Text Reporter

Generates text-format analysis reports maintaining backward compatibility
with existing report format.
"""

import os
import logging
from typing import Optional
from fractions import Fraction

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Analysis

logger = logging.getLogger(__name__)


class TextReporter:
    """
    Generates text-format analysis reports.
    
    Maintains backward compatibility with existing text report format,
    ensuring smooth transition from legacy system.
    
    Attributes:
        output_directory: Base directory for text reports
    
    Example:
        >>> reporter = TextReporter('metadata_analysis/')
        >>> report_path = reporter.generate_report(analysis, 'running_sole/weekly')
    """
    
    def __init__(self, output_directory: str = 'metadata_analysis'):
        """
        Initialize text reporter.
        
        Args:
            output_directory: Base directory for saving reports
        """
        self.output_directory = output_directory
    
    @classmethod
    def from_config(cls, config_path: str = 'config.yaml') -> 'TextReporter':
        """Create TextReporter from configuration file."""
        import yaml
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        output_dir = config.get('reporting', {}).get('text_reports_path', 'metadata_analysis')
        return cls(output_directory=output_dir)
    
    @staticmethod
    def _parse_shutter_speed(speed_str: str) -> Optional[float]:
        """Parse shutter speed string into float for sorting."""
        if not speed_str or speed_str == "":
            return None
        try:
            if '/' in speed_str:
                num, denom = map(int, speed_str.split('/'))
                return num / denom if denom != 0 else None
            return float(speed_str)
        except (ValueError, ZeroDivisionError):
            return None
    
    def generate_report(self, analysis: Analysis, 
                       subdirectory: Optional[str] = None,
                       filename: Optional[str] = None) -> str:
        """
        Generate text report from analysis.
        
        Args:
            analysis: Analysis instance to report
            subdirectory: Optional subdirectory within output_directory
            filename: Optional custom filename (defaults to analysis_<name>.txt)
        
        Returns:
            Path to generated report file
        
        Example:
            >>> reporter = TextReporter()
            >>> path = reporter.generate_report(
            ...     analysis,
            ...     subdirectory='running_sole',
            ...     filename='aggregated_running_sole_ALL.txt'
            ... )
        """
        # Format the report text
        report_text = self._format_analysis(analysis)
        
        # Determine output path
        if subdirectory:
            output_dir = os.path.join(self.output_directory, subdirectory)
        else:
            output_dir = self.output_directory
        
        os.makedirs(output_dir, exist_ok=True)
        
        if not filename:
            # Sanitize analysis name for filename
            safe_name = analysis.name.replace(' ', '_').replace('/', '_')
            filename = f"analysis_{safe_name}.txt"
        
        output_path = os.path.join(output_dir, filename)
        
        # Write report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"Generated text report: {output_path}")
        return output_path
    
    def _format_analysis(self, analysis: Analysis) -> str:
        """
        Format analysis as text report.
        
        Args:
            analysis: Analysis instance
        
        Returns:
            Formatted text report
        """
        lines = []
        total = analysis.total_photos
        
        # Header
        lines.append(f"Analysis: {analysis.name}")
        lines.append("=" * 80)
        
        # Category and Group info if available
        if 'category' in analysis.metadata:
            lines.append(f"Category: {analysis.metadata['category']}")
        if 'group' in analysis.metadata:
            lines.append(f"Group: {analysis.metadata['group']}")
        
        lines.append(f"\nTotal photos analyzed: {total}")
        lines.append("\n" + "=" * 80)
        
        # Calculate prime vs zoom
        prime_count = analysis.prime_count
        zoom_count = analysis.zoom_count
        
        prime_lenses = []
        zoom_lenses = []
        
        for lens, count in analysis.lens_freq.items():
            if '-' in lens and 'mm' in lens:
                zoom_lenses.append((lens, count))
            else:
                prime_lenses.append((lens, count))
        
        # Overall metrics
        lines.append("\nOVERALL METRICS")
        lines.append("-" * 80)
        
        # Hit rate section - always show, even if unable to calculate
        if analysis.hit_rate is not None and analysis.total_raw_photos > 0:
            edited_photos = analysis.total_photos
            raw_photos = analysis.total_raw_photos
            lines.append(f"\nHit Rate: {analysis.hit_rate:.2f}%")
            lines.append(f"  Total: {edited_photos}")
            lines.append(f"  RAW: {raw_photos}")
            lines.append(f"  Edited: {edited_photos}")
        else:
            lines.append(f"\nHit Rate: Unable to calculate")
            lines.append(f"  Total: {analysis.total_photos}")
            lines.append(f"  RAW: N/A")
            lines.append(f"  Edited: {analysis.total_photos}")
        
        if prime_count or zoom_count:
            lines.append(f"\nLens Type Distribution:")
            if prime_count > 0:
                lines.append(f"  Prime Lenses: {prime_count} photos ({prime_count/total*100:.1f}%)")
                for lens, count in sorted(prime_lenses, key=lambda x: x[1], reverse=True):
                    lines.append(f"    - {lens}: {count} photos")
            if zoom_count > 0:
                lines.append(f"  Zoom Lenses: {zoom_count} photos ({zoom_count/total*100:.1f}%)")
                for lens, count in sorted(zoom_lenses, key=lambda x: x[1], reverse=True):
                    lines.append(f"    - {lens}: {count} photos")
        
        # Shutter Speeds
        if analysis.shutter_speed_freq:
            lines.append(f"\nOverall Shutter Speed Distribution:")
            for speed, count in sorted(analysis.shutter_speed_freq.items(),
                                      key=lambda x: self._parse_shutter_speed(x[0]) or 0):
                if speed:
                    lines.append(f"  {speed}: {count} times ({count / total * 100:.1f}%)")
        
        # Apertures
        if analysis.aperture_freq:
            lines.append(f"\nOverall Aperture Distribution:")
            for aperture, count in sorted(analysis.aperture_freq.items(),
                                         key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
                if aperture != "":
                    lines.append(f"  f/{aperture}: {count} times ({count / total * 100:.1f}%)")
        
        # ISOs
        if analysis.iso_freq:
            lines.append(f"\nOverall ISO Distribution:")
            for iso, count in sorted(analysis.iso_freq.items(),
                                    key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
                if iso != "":
                    lines.append(f"  ISO {iso}: {count} times ({count / total * 100:.1f}%)")
        
        # Exposure Programs
        if analysis.exposure_program_freq:
            lines.append(f"\nOverall Exposure Program Distribution:")
            for program, count in analysis.exposure_program_freq.items():
                if program:
                    lines.append(f"  {program}: {count} times ({count / total * 100:.1f}%)")
        
        # Flash Modes
        if analysis.flash_mode_freq:
            lines.append(f"\nOverall Flash Mode Distribution:")
            for mode, count in analysis.flash_mode_freq.items():
                if mode:
                    lines.append(f"  {mode}: {count} times ({count / total * 100:.1f}%)")
        
        # Lens breakdowns
        if analysis.lens_breakdowns:
            lines.append("\n" + "=" * 80)
            lines.append("DETAILED BREAKDOWN BY LENS")
            lines.append("=" * 80)
            
            for lens, breakdown in analysis.lens_breakdowns.items():
                lens_count = breakdown['Count']
                lines.append(f"\n{'-' * 80}")
                lines.append(f"Lens: {lens} (Used {lens_count} times)")
                lines.append(f"{'-' * 80}")
                
                if breakdown["ShutterSpeed"]:
                    lines.append("Shutter Speeds:")
                    for speed, count in sorted(breakdown["ShutterSpeed"].items(),
                                              key=lambda x: self._parse_shutter_speed(x[0]) or 0):
                        if speed:
                            lines.append(f"  {speed}: {count} times ({count / lens_count * 100:.1f}%)")
                
                if breakdown["Aperture"]:
                    lines.append("Apertures:")
                    for aperture, count in sorted(breakdown["Aperture"].items(),
                                                  key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
                        if aperture != "":
                            lines.append(f"  f/{aperture}: {count} times ({count / lens_count * 100:.1f}%)")
                
                if breakdown["ISO"]:
                    lines.append("ISOs:")
                    for iso, count in sorted(breakdown["ISO"].items(),
                                            key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
                        if iso != "":
                            lines.append(f"  ISO {iso}: {count} times ({count / lens_count * 100:.1f}%)")
                
                if breakdown["ExposureProgram"]:
                    lines.append("Exposure Programs:")
                    for program, count in breakdown["ExposureProgram"].items():
                        if program:
                            lines.append(f"  {program}: {count} times ({count / lens_count * 100:.1f}%)")
                
                if breakdown["FlashMode"]:
                    lines.append("Flash Modes:")
                    for mode, count in breakdown["FlashMode"].items():
                        if mode:
                            lines.append(f"  {mode}: {count} times ({count / lens_count * 100:.1f}%)")
        
        return "\n".join(lines)
