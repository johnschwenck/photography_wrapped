"""
Comprehensive Photo Metadata Analyzer
Extracts EXIF data from photos, analyzes patterns, and aggregates statistics across multiple folders.

Two modes:
1. Interactive mode: Select folders one-by-one and assign group names
2. Batch mode: Crawl a parent directory with consistent subdirectory structure
"""

import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, simpledialog
from collections import defaultdict, Counter
from fractions import Fraction
from datetime import datetime
import exiftool
import re


# ============================================================================
# EXIF EXTRACTION
# ============================================================================

def extract_metadata(file_path):
    """Extract EXIF metadata from a single image file."""
    with exiftool.ExifTool() as et:
        output = et.execute("-j", file_path)
        
        try:
            metadata_list = json.loads(output)
            if not metadata_list:
                raise ValueError(f"No metadata found for: {file_path}")
            
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
            exposure_program_str = exposure_program_map.get(exposure_program, f"Unknown ({exposure_program})")
            
            # Map flash mode codes
            flash_mode_map = {
                0: "No flash", 1: "Flash fired", 5: "Flash fired, return not detected",
                7: "Flash fired, return detected", 9: "Flash on, compulsory flash mode",
                13: "Flash on, return not detected", 16: "Flash off, no flash function"
            }
            flash_mode = metadata.get("EXIF:Flash", "")
            flash_mode_str = flash_mode_map.get(flash_mode, f"Unknown ({flash_mode})")
            
            return {
                "File": os.path.basename(file_path),
                "Camera": metadata.get("EXIF:Make", "") + " " + metadata.get("EXIF:Model", ""),
                "Lens": metadata.get('EXIF:LensModel', "Unknown"),
                "FocalLength": metadata.get("EXIF:FocalLength", ""),
                "ISO": metadata.get("EXIF:ISO", ""),
                "Aperture": metadata.get("EXIF:FNumber", ""),
                "ShutterSpeed": exposure_time_str,
                "ExposureProgram": exposure_program_str,
                "ExposureBias": metadata.get("EXIF:ExposureBiasValue", ""),
                "FlashMode": flash_mode_str
            }
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse ExifTool output for {file_path}: {e}")


def count_image_files(folder_path):
    """Count only image files in a folder (excluding .xml and other non-image files)."""
    image_extensions = ('.arw', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    count = 0
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(image_extensions):
            count += 1
    
    return count


def calculate_hit_rate(edited_folder_path, raw_folder_path):
    """Calculate hit rate between Edited and RAW folders.
    
    Args:
        edited_folder_path: Path to the Edited folder
        raw_folder_path: Path to the RAW folder
    
    Returns:
        Dict with 'edited', 'raw', and 'percentage' keys, or None if RAW folder doesn't exist
    """
    if not os.path.exists(raw_folder_path):
        return None
    
    edited_count = count_image_files(edited_folder_path)
    raw_count = count_image_files(raw_folder_path)
    
    if raw_count == 0:
        return None
    
    percentage = (edited_count / raw_count) * 100
    
    return {
        'edited': edited_count,
        'raw': raw_count,
        'percentage': percentage
    }


def detect_raw_folder(edited_folder_path):
    """Try to find a corresponding RAW folder for an Edited folder.
    
    Checks for a sibling 'RAW' folder at the same level as the Edited folder.
    
    Args:
        edited_folder_path: Path to the Edited folder
    
    Returns:
        Path to RAW folder if found, None otherwise
    """
    parent_dir = os.path.dirname(edited_folder_path)
    
    # Check for common RAW folder names
    raw_folder_names = ['RAW', 'Raw', 'raw', 'RAW Files', 'Raws']
    
    for raw_name in raw_folder_names:
        raw_path = os.path.join(parent_dir, raw_name)
        if os.path.exists(raw_path) and os.path.isdir(raw_path):
            return raw_path
    
    return None


def process_folder(folder_path):
    """Extract metadata from all images in a folder."""
    all_metadata = []
    image_extensions = ('.arw', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(image_extensions):
            file_path = os.path.join(folder_path, filename)
            try:
                metadata = extract_metadata(file_path)
                all_metadata.append(metadata)
                print(f"  Processed: {filename}")
            except Exception as e:
                print(f"  Error processing {filename}: {e}")
    
    return all_metadata


# ============================================================================
# ANALYSIS
# ============================================================================

def parse_shutter_speed(speed_str):
    """Parse shutter speed string (e.g., '1/200') into a float for comparison."""
    if not speed_str or speed_str == "":
        return None
    try:
        if '/' in speed_str:
            num, denom = map(int, speed_str.split('/'))
            return num / denom if denom != 0 else None
        return float(speed_str)
    except (ValueError, ZeroDivisionError):
        return None


def analyze_metadata(metadata_list, analysis_name):
    """Analyze metadata and return frequency statistics."""
    # Overall counters
    lens_freq = Counter()
    shutter_speed_freq = Counter()
    aperture_freq = Counter()
    iso_freq = Counter()
    exposure_program_freq = Counter()
    flash_mode_freq = Counter()
    
    # Lens-specific breakdowns
    lens_breakdowns = {}
    
    for metadata in metadata_list:
        lens = metadata.get("Lens", "Unknown")
        shutter_speed = metadata.get("ShutterSpeed", "")
        aperture = metadata.get("Aperture", "")
        iso = metadata.get("ISO", "")
        exposure_program = metadata.get("ExposureProgram", "Unknown")
        flash_mode = metadata.get("FlashMode", "Unknown")
        
        # Update overall frequencies
        lens_freq[lens] += 1
        shutter_speed_freq[shutter_speed] += 1
        aperture_freq[aperture] += 1
        iso_freq[iso] += 1
        exposure_program_freq[exposure_program] += 1
        flash_mode_freq[flash_mode] += 1
        
        # Build lens-specific breakdowns
        if lens not in lens_breakdowns:
            lens_breakdowns[lens] = {
                "ShutterSpeed": Counter(),
                "Aperture": Counter(),
                "ISO": Counter(),
                "ExposureProgram": Counter(),
                "FlashMode": Counter(),
                "Count": 0
            }
        
        lens_breakdowns[lens]["ShutterSpeed"][shutter_speed] += 1
        lens_breakdowns[lens]["Aperture"][aperture] += 1
        lens_breakdowns[lens]["ISO"][iso] += 1
        lens_breakdowns[lens]["ExposureProgram"][exposure_program] += 1
        lens_breakdowns[lens]["FlashMode"][flash_mode] += 1
        lens_breakdowns[lens]["Count"] += 1
    
    return {
        'name': analysis_name,
        'total_count': len(metadata_list),
        'lens_freq': lens_freq,
        'shutter_speed_freq': shutter_speed_freq,
        'aperture_freq': aperture_freq,
        'iso_freq': iso_freq,
        'exposure_program_freq': exposure_program_freq,
        'flash_mode_freq': flash_mode_freq,
        'lens_breakdowns': lens_breakdowns
    }


def format_analysis_output(analysis_data, hit_rate=None):
    """Format analysis data into readable text output."""
    lines = []
    name = analysis_data['name']
    total = analysis_data['total_count']
    
    lines.append(f"Analysis: {name}")
    lines.append("=" * 80)
    lines.append(f"\nTotal photos analyzed: {total}")
    if hit_rate is not None:
        lines.append(f"Hit Rate (Edited/RAW): {hit_rate['edited']}/{hit_rate['raw']} = {hit_rate['percentage']:.1f}%")
    lines.append("\n" + "=" * 80)
    
    # Calculate prime vs zoom
    prime_count = 0
    zoom_count = 0
    prime_lenses = []
    zoom_lenses = []
    
    for lens, count in analysis_data['lens_freq'].items():
        if '-' in lens and 'mm' in lens:
            zoom_count += count
            zoom_lenses.append((lens, count))
        else:
            prime_count += count
            prime_lenses.append((lens, count))
    
    # Overall metrics
    lines.append("\nOVERALL METRICS")
    lines.append("-" * 80)
    
    lines.append(f"\nLens Type Distribution:")
    lines.append(f"  Prime Lenses: {prime_count} photos ({prime_count/total*100:.1f}%)")
    for lens, count in sorted(prime_lenses, key=lambda x: x[1], reverse=True):
        lines.append(f"    - {lens}: {count} photos")
    lines.append(f"  Zoom Lenses: {zoom_count} photos ({zoom_count/total*100:.1f}%)")
    for lens, count in sorted(zoom_lenses, key=lambda x: x[1], reverse=True):
        lines.append(f"    - {lens}: {count} photos")
    
    # Shutter Speeds
    lines.append(f"\nOverall Shutter Speed Distribution:")
    for speed, count in sorted(analysis_data['shutter_speed_freq'].items(), 
                                key=lambda x: parse_shutter_speed(x[0]) or 0):
        if speed:
            lines.append(f"  {speed}: {count} times ({count / total * 100:.1f}%)")
    
    # Apertures
    lines.append(f"\nOverall Aperture Distribution:")
    for aperture, count in sorted(analysis_data['aperture_freq'].items(), 
                                   key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
        if aperture and aperture != "":
            lines.append(f"  f/{aperture}: {count} times ({count / total * 100:.1f}%)")
    
    # ISOs
    lines.append(f"\nOverall ISO Distribution:")
    for iso, count in sorted(analysis_data['iso_freq'].items(), 
                            key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
        if iso and iso != "":
            lines.append(f"  ISO {iso}: {count} times ({count / total * 100:.1f}%)")
    
    # Exposure Programs
    lines.append(f"\nOverall Exposure Program Distribution:")
    for program, count in analysis_data['exposure_program_freq'].items():
        lines.append(f"  {program}: {count} times ({count / total * 100:.1f}%)")
    
    # Flash Modes
    lines.append(f"\nOverall Flash Mode Distribution:")
    for mode, count in analysis_data['flash_mode_freq'].items():
        lines.append(f"  {mode}: {count} times ({count / total * 100:.1f}%)")
    
    # Lens breakdowns
    lines.append("\n" + "=" * 80)
    lines.append("DETAILED BREAKDOWN BY LENS")
    lines.append("=" * 80)
    
    for lens, breakdown in analysis_data['lens_breakdowns'].items():
        lens_count = breakdown['Count']
        lines.append(f"\n{'-' * 80}")
        lines.append(f"Lens: {lens} (Used {lens_count} times)")
        lines.append(f"{'-' * 80}")
        
        lines.append("Shutter Speeds:")
        for speed, count in sorted(breakdown["ShutterSpeed"].items(), 
                                   key=lambda x: parse_shutter_speed(x[0]) or 0):
            if speed:
                lines.append(f"  {speed}: {count} times ({count / lens_count * 100:.1f}%)")
        
        lines.append("Apertures:")
        for aperture, count in sorted(breakdown["Aperture"].items(), 
                                      key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
            if aperture and aperture != "":
                lines.append(f"  f/{aperture}: {count} times ({count / lens_count * 100:.1f}%)")
        
        lines.append("ISOs:")
        for iso, count in sorted(breakdown["ISO"].items(), 
                                key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
            if iso and iso != "":
                lines.append(f"  ISO {iso}: {count} times ({count / lens_count * 100:.1f}%)")
        
        lines.append("Exposure Programs:")
        for program, count in breakdown["ExposureProgram"].items():
            lines.append(f"  {program}: {count} times ({count / lens_count * 100:.1f}%)")
        
        lines.append("Flash Modes:")
        for mode, count in breakdown["FlashMode"].items():
            lines.append(f"  {mode}: {count} times ({count / lens_count * 100:.1f}%)")
    
    return "\n".join(lines)


# ============================================================================
# AGGREGATION
# ============================================================================

def aggregate_analyses(analyses_list):
    """Aggregate multiple analysis results into one comprehensive summary."""
    aggregated = {
        'lenses': defaultdict(lambda: {
            'count': 0,
            'shutter_speeds': defaultdict(int),
            'apertures': defaultdict(float),
            'isos': defaultdict(int),
            'exposure_programs': defaultdict(int),
            'flash_modes': defaultdict(int)
        })
    }
    
    for analysis in analyses_list:
        for lens_name, lens_data in analysis['lens_breakdowns'].items():
            agg_lens = aggregated['lenses'][lens_name]
            agg_lens['count'] += lens_data['Count']
            
            for speed, count in lens_data['ShutterSpeed'].items():
                agg_lens['shutter_speeds'][speed] += count
            
            for aperture, count in lens_data['Aperture'].items():
                agg_lens['apertures'][float(aperture) if aperture else 0] += count
            
            for iso, count in lens_data['ISO'].items():
                agg_lens['isos'][int(iso) if iso else 0] += count
            
            for program, count in lens_data['ExposureProgram'].items():
                agg_lens['exposure_programs'][program] += count
            
            for mode, count in lens_data['FlashMode'].items():
                agg_lens['flash_modes'][mode] += count
    
    return aggregated


def format_aggregated_output(aggregated, folder_names, group_structure=None, analyses_list=None, hit_rate=None, individual_hit_rates=None):
    """Format aggregated data into readable text output.
    
    Args:
        aggregated: The aggregated lens data
        folder_names: List of folder names (for backward compatibility)
        group_structure: Optional dict of {group_name: [folder_names]} for hierarchical display
        analyses_list: Optional list of analysis data dicts containing photo counts
        hit_rate: Optional dict with 'edited', 'raw', and 'percentage' keys for overall hit rate display
        individual_hit_rates: Optional dict mapping folder names to their individual hit rates
    """
    lines = ["Aggregated Metadata Analysis", "=" * 80]
    
    # Create photo count lookup if analyses_list provided
    photo_counts = {}
    if analyses_list:
        for analysis in analyses_list:
            photo_counts[analysis['name']] = analysis['total_count']
    
    if group_structure:
        # Hierarchical display with groups
        total_folders = sum(len(folders) for folders in group_structure.values())
        lines.append(f"\nFolders analyzed: {total_folders}")
        if hit_rate is not None:
            lines.append(f"Hit Rate (Edited/RAW): {hit_rate['edited']}/{hit_rate['raw']} = {hit_rate['percentage']:.1f}%")
        lines.append(f"Groups: {len(group_structure)}")
        for group_name in sorted(group_structure.keys()):
            folders = group_structure[group_name]
            lines.append(f"  - {group_name}: {len(folders)} folder(s)")
            for folder in sorted(folders):
                line_parts = [f"      - {folder}"]
                if folder in photo_counts:
                    line_parts.append(f" ({photo_counts[folder]} photos")
                    if individual_hit_rates and folder in individual_hit_rates:
                        hr = individual_hit_rates[folder]
                        line_parts.append(f" | Hit Rate: {hr['percentage']:.1f}%)")
                    else:
                        line_parts[-1] += ")"
                lines.append("".join(line_parts))
    else:
        # Simple flat list (backward compatibility)
        lines.append(f"\nFolders analyzed: {len(folder_names)}")
        if hit_rate is not None:
            lines.append(f"Hit Rate (Edited/RAW): {hit_rate['edited']}/{hit_rate['raw']} = {hit_rate['percentage']:.1f}%")
        for name in sorted(folder_names):
            line_parts = [f"  - {name}"]
            if name in photo_counts:
                line_parts.append(f" ({photo_counts[name]} photos")
                if individual_hit_rates and name in individual_hit_rates:
                    hr = individual_hit_rates[name]
                    line_parts.append(f" | Hit Rate: {hr['percentage']:.1f}%)")
                else:
                    line_parts[-1] += ")"
            lines.append("".join(line_parts))
    
    lines.append("\n" + "=" * 80)
    
    # Calculate overall metrics across all lenses
    total_photos = sum(lens_data['count'] for lens_data in aggregated['lenses'].values())
    
    # Aggregate all settings across lenses
    overall_shutter_speeds = defaultdict(int)
    overall_apertures = defaultdict(int)
    overall_isos = defaultdict(int)
    overall_exposure_programs = defaultdict(int)
    overall_flash_modes = defaultdict(int)
    
    # Prime vs Zoom classification
    prime_count = 0
    zoom_count = 0
    prime_lenses = []
    zoom_lenses = []
    
    for lens_name, lens_data in aggregated['lenses'].items():
        # Aggregate settings
        for speed, count in lens_data['shutter_speeds'].items():
            overall_shutter_speeds[speed] += count
        for aperture, count in lens_data['apertures'].items():
            overall_apertures[aperture] += count
        for iso, count in lens_data['isos'].items():
            overall_isos[iso] += count
        for program, count in lens_data['exposure_programs'].items():
            overall_exposure_programs[program] += count
        for mode, count in lens_data['flash_modes'].items():
            overall_flash_modes[mode] += count
        
        # Classify as prime or zoom (zoom lenses typically have 'mm-' or 'mm F' in the name)
        if '-' in lens_name and 'mm' in lens_name:
            zoom_count += lens_data['count']
            zoom_lenses.append((lens_name, lens_data['count']))
        else:
            prime_count += lens_data['count']
            prime_lenses.append((lens_name, lens_data['count']))
    
    # Display overall metrics
    lines.append("\nOVERALL METRICS")
    lines.append("-" * 80)
    lines.append(f"Total photos analyzed: {total_photos}")
    lines.append(f"\nLens Type Distribution:")
    lines.append(f"  Prime Lenses: {prime_count} photos ({prime_count/total_photos*100:.1f}%)")
    for lens, count in sorted(prime_lenses, key=lambda x: x[1], reverse=True):
        lines.append(f"    - {lens}: {count} photos")
    lines.append(f"  Zoom Lenses: {zoom_count} photos ({zoom_count/total_photos*100:.1f}%)")
    for lens, count in sorted(zoom_lenses, key=lambda x: x[1], reverse=True):
        lines.append(f"    - {lens}: {count} photos")
    
    # Overall shutter speeds
    lines.append(f"\nOverall Shutter Speed Distribution:")
    sorted_speeds = sorted(overall_shutter_speeds.items(), 
                          key=lambda x: parse_shutter_speed(x[0]) or 0,
                          reverse=True)
    for speed, count in sorted_speeds:
        if speed:
            percentage = (count / total_photos) * 100
            lines.append(f"  {speed}: {count} times ({percentage:.1f}%)")
    
    # Overall apertures
    lines.append(f"\nOverall Aperture Distribution:")
    sorted_apertures = sorted(overall_apertures.items())
    for aperture, count in sorted_apertures:
        if aperture:
            percentage = (count / total_photos) * 100
            lines.append(f"  f/{aperture}: {int(count)} times ({percentage:.1f}%)")
    
    # Overall ISOs
    lines.append(f"\nOverall ISO Distribution:")
    sorted_isos = sorted(overall_isos.items())
    for iso, count in sorted_isos:
        if iso:
            percentage = (count / total_photos) * 100
            lines.append(f"  ISO {iso}: {count} times ({percentage:.1f}%)")
    
    # Overall exposure programs
    lines.append(f"\nOverall Exposure Program Distribution:")
    sorted_programs = sorted(overall_exposure_programs.items(), 
                            key=lambda x: x[1], 
                            reverse=True)
    for program, count in sorted_programs:
        percentage = (count / total_photos) * 100
        lines.append(f"  {program}: {count} times ({percentage:.1f}%)")
    
    # Overall flash modes
    lines.append(f"\nOverall Flash Mode Distribution:")
    sorted_modes = sorted(overall_flash_modes.items(), 
                         key=lambda x: x[1], 
                         reverse=True)
    for mode, count in sorted_modes:
        percentage = (count / total_photos) * 100
        lines.append(f"  {mode}: {count} times ({percentage:.1f}%)")
    
    lines.append("\n" + "=" * 80)
    lines.append("DETAILED BREAKDOWN BY LENS")
    lines.append("=" * 80)
    
    sorted_lenses = sorted(aggregated['lenses'].items(), 
                          key=lambda x: x[1]['count'], 
                          reverse=True)
    
    for lens_name, lens_data in sorted_lenses:
        lines.append(f"\n{'-' * 80}")
        lines.append(f"Lens: {lens_name} (Used {lens_data['count']} times)")
        lines.append(f"{'-' * 80}")
        
        lines.append("Shutter Speeds:")
        sorted_speeds = sorted(lens_data['shutter_speeds'].items(), 
                              key=lambda x: parse_shutter_speed(x[0]) or 0,
                              reverse=True)
        for speed, count in sorted_speeds:
            if speed:
                percentage = (count / lens_data['count']) * 100
                lines.append(f"  {speed}: {count} times ({percentage:.1f}%)")
        
        lines.append("Apertures:")
        sorted_apertures = sorted(lens_data['apertures'].items())
        for aperture, count in sorted_apertures:
            if aperture:
                percentage = (count / lens_data['count']) * 100
                lines.append(f"  f/{aperture}: {int(count)} times ({percentage:.1f}%)")
        
        lines.append("ISOs:")
        sorted_isos = sorted(lens_data['isos'].items())
        for iso, count in sorted_isos:
            if iso:
                percentage = (count / lens_data['count']) * 100
                lines.append(f"  ISO {iso}: {count} times ({percentage:.1f}%)")
        
        lines.append("Exposure Programs:")
        sorted_programs = sorted(lens_data['exposure_programs'].items(), 
                                key=lambda x: x[1], 
                                reverse=True)
        for program, count in sorted_programs:
            percentage = (count / lens_data['count']) * 100
            lines.append(f"  {program}: {count} times ({percentage:.1f}%)")
        
        lines.append("Flash Modes:")
        sorted_modes = sorted(lens_data['flash_modes'].items(), 
                             key=lambda x: x[1], 
                             reverse=True)
        for mode, count in sorted_modes:
            percentage = (count / lens_data['count']) * 100
            lines.append(f"  {mode}: {count} times ({percentage:.1f}%)")
    
    return "\n".join(lines)


# ============================================================================
# BATCH CRAWL MODE
# ============================================================================

def find_photo_folders(parent_dir, target_folder_name="edited"):
    """
    Recursively find all folders with a specific name (e.g., 'edited').
    Returns list of folder paths.
    """
    photo_folders = []
    target_lower = target_folder_name.lower()
    
    for root, dirs, files in os.walk(parent_dir):
        for dir_name in dirs:
            if dir_name.lower() == target_lower:
                photo_folders.append(os.path.join(root, dir_name))
    
    return photo_folders


def extract_group_name_from_path(folder_path, parent_dir):
    """
    Extract a meaningful group name from the folder path.
    For structure like: parent/Week 01/Photos/Edited
    Returns: "Week_01"
    """
    # Get relative path from parent
    rel_path = os.path.relpath(folder_path, parent_dir)
    path_parts = rel_path.split(os.sep)
    
    # Use the first meaningful part (skip generic folders like 'photos', 'edited')
    for part in path_parts:
        part_lower = part.lower()
        if part_lower not in ['photos', 'edited', 'raw', 'jpg', 'jpeg', 'images']:
            return part.replace(' ', '_')
    
    # Fallback to first part
    return path_parts[0].replace(' ', '_')


def batch_crawl_mode():
    """Batch mode: crawl a parent directory and process all matching subfolders."""
    
    # Initialize Tkinter
    root = tk.Tk()
    root.withdraw()
    
    # Get category name
    category_name = simpledialog.askstring(
        "Analysis Category", 
        "Enter the category name for this analysis (e.g., 'Running_TheSole', 'Weekly_Project'):"
    )
    
    if not category_name:
        print("No category name provided. Exiting.")
        return
    
    category_clean = category_name.replace(' ', '_').replace('-', '_').lower()
    print(f"\nBatch Crawl Mode - Category: {category_name}\n")
    
    # Select parent directory
    parent_dir = filedialog.askdirectory(title="Select parent directory to crawl")
    if not parent_dir:
        print("No directory selected. Exiting.")
        return
    
    # Ask for target folder name
    target_folder = simpledialog.askstring(
        "Target Folder Name",
        "Enter the folder name to look for (e.g., 'Edited', 'Photos'):",
        initialvalue="Edited"
    )
    
    if not target_folder:
        print("No target folder specified. Exiting.")
        return
    
    print(f"Crawling: {parent_dir}")
    print(f"Looking for folders named: '{target_folder}'\n")
    
    # Find all matching folders
    photo_folders = find_photo_folders(parent_dir, target_folder)
    
    if not photo_folders:
        print(f"No folders named '{target_folder}' found. Exiting.")
        return
    
    print(f"Found {len(photo_folders)} folders:\n")
    for folder in photo_folders:
        group_name = extract_group_name_from_path(folder, parent_dir)
        print(f"  {group_name}: {folder}")
    
    # Confirm processing
    proceed = simpledialog.askstring(
        "Confirm",
        f"Found {len(photo_folders)} folders. Proceed with analysis? (yes/no):"
    )
    
    if not proceed or proceed.lower() not in ['yes', 'y']:
        print("Analysis cancelled.")
        return
    
    # Setup output directories
    os.makedirs("metadata_json", exist_ok=True)
    os.makedirs("metadata_analysis", exist_ok=True)
    os.makedirs(os.path.join("metadata_json", category_clean), exist_ok=True)
    os.makedirs(os.path.join("metadata_analysis", category_clean), exist_ok=True)
    
    # Process all folders (each gets its own group based on path)
    print(f"\n{len(photo_folders)} folder(s) to process. Starting...\n")
    
    all_analyses = []
    group_structure = {}
    all_hit_rates = []  # Track hit rates across all folders
    individual_hit_rates = {}  # Map folder names to hit rates
    
    for folder_path in photo_folders:
        group_name = extract_group_name_from_path(folder_path, parent_dir)
        group_clean = group_name.lower()
        
        # Create group directory
        group_json_dir = os.path.join("metadata_json", category_clean, group_clean)
        group_analysis_dir = os.path.join("metadata_analysis", category_clean, group_clean)
        os.makedirs(group_json_dir, exist_ok=True)
        os.makedirs(group_analysis_dir, exist_ok=True)
        
        print(f"Processing: {group_name}")
        
        # Check if this is an Edited folder and look for RAW folder
        hit_rate = None
        if 'edited' in os.path.basename(folder_path).lower():
            raw_folder = detect_raw_folder(folder_path)
            if raw_folder:
                hit_rate = calculate_hit_rate(folder_path, raw_folder)
                if hit_rate:
                    print(f"  Hit Rate: {hit_rate['edited']}/{hit_rate['raw']} = {hit_rate['percentage']:.1f}%")
                    all_hit_rates.append(hit_rate)
                    individual_hit_rates[group_name] = hit_rate
        
        # Extract metadata
        metadata_list = process_folder(folder_path)
        
        if not metadata_list:
            print(f"  No images found\n")
            continue
        
        print(f"  Found {len(metadata_list)} images")
        
        # Save raw metadata JSON
        json_path = os.path.join(group_json_dir, f"metadata_{group_clean}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_list, f, indent=4)
        print(f"  Saved: {json_path}")
        
        # Analyze metadata
        analysis_data = analyze_metadata(metadata_list, group_name)
        all_analyses.append(analysis_data)
        
        # Track for group structure
        if category_name not in group_structure:
            group_structure[category_name] = []
        group_structure[category_name].append(group_name)
        
        # Save individual analysis
        analysis_text = format_analysis_output(analysis_data, hit_rate)
        analysis_path = os.path.join(group_analysis_dir, f"analysis_{group_clean}.txt")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            f.write(analysis_text)
        print(f"  Saved: {analysis_path}\n")
    
    # Create category-level aggregation
    if len(all_analyses) > 1:
        print(f"Creating category-level aggregation: {category_name}")
        category_aggregated = aggregate_analyses(all_analyses)
        folder_names = [a['name'] for a in all_analyses]
        
        # Calculate combined hit rate for category if applicable
        category_hit_rate = None
        if all_hit_rates:
            total_edited = sum(hr['edited'] for hr in all_hit_rates)
            total_raw = sum(hr['raw'] for hr in all_hit_rates)
            if total_raw > 0:
                category_hit_rate = {
                    'edited': total_edited,
                    'raw': total_raw,
                    'percentage': (total_edited / total_raw) * 100
                }
        
        category_text = format_aggregated_output(category_aggregated, folder_names, group_structure, all_analyses, category_hit_rate, individual_hit_rates)
        
        # Save category aggregation
        category_agg_path = os.path.join("metadata_analysis", category_clean, f"aggregated_{category_clean}_ALL.txt")
        with open(category_agg_path, 'w', encoding='utf-8') as f:
            f.write(category_text)
        print(f"Saved category aggregation: {category_agg_path}\n")
    
    # Display summary
    total_images = sum(a['total_count'] for a in all_analyses)
    print("\n" + "=" * 50)
    print("SUMMARY - BATCH CRAWL MODE")
    print("=" * 50)
    print(f"Category: {category_name}")
    print(f"Total folders processed: {len(all_analyses)}")
    print(f"Total images analyzed: {total_images}")
    print(f"\nOutput structure:")
    print(f"  metadata_json/{category_clean}/<group>/metadata_<group>.json")
    print(f"  metadata_analysis/{category_clean}/<group>/analysis_<group>.txt")
    if len(all_analyses) > 1:
        print(f"  metadata_analysis/{category_clean}/aggregated_{category_clean}_ALL.txt")
    
    print("\nAnalysis complete!")


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Main workflow: select folders, extract metadata, analyze, and aggregate."""
    
    # Initialize Tkinter
    root = tk.Tk()
    root.withdraw()
    
    # Get top-level category name
    from tkinter import simpledialog
    category_name = simpledialog.askstring(
        "Analysis Category", 
        "Enter the category name for this analysis (e.g., 'Concerts', 'Portraits', 'Events'):"
    )
    
    if not category_name:
        print("No category name provided. Exiting.")
        return
    
    category_clean = category_name.replace(' ', '_').replace('-', '_').lower()
    print(f"\nAnalysis Category: {category_name}\n")
    
    # Setup output directories
    os.makedirs("metadata_json", exist_ok=True)
    os.makedirs("metadata_analysis", exist_ok=True)
    os.makedirs(os.path.join("metadata_json", category_clean), exist_ok=True)
    os.makedirs(os.path.join("metadata_analysis", category_clean), exist_ok=True)
    
    # Select folders and assign group names
    print("Select folders one at a time. After each selection, assign a group name.")
    print("Use the same group name to aggregate multiple shoots together.\n")
    
    folder_data = []  # List of (folder_path, group_name, display_name)
    
    while True:
        folder = filedialog.askdirectory(title="Select a folder to analyze (Cancel when done)")
        if not folder:
            break
        
        # Ask for group name
        group_name = simpledialog.askstring(
            "Group Name",
            f"Enter group name for:\n{folder}\n\n(e.g., 'MA' for Modern Alibi, 'SLO' for Stop Light Observations)"
        )
        
        if not group_name:
            print(f"Skipped: {folder} (no group name provided)\n")
            continue
        
        # Create display name for this specific folder
        current_folder = os.path.basename(folder)
        if current_folder.lower() in ['edited', 'photos', 'raw', 'jpg', 'jpeg', 'images', 'rd1', 'rd2', 'rd3']:
            path_parts = []
            temp_path = folder
            for _ in range(3):
                parent = os.path.dirname(temp_path)
                if parent == temp_path:
                    break
                parent_name = os.path.basename(parent)
                if parent_name.lower() not in ['concerts', 'photos & videos', 'photos', 'videos', 'edited', 'raw']:
                    path_parts.insert(0, parent_name)
                temp_path = parent
                if len(path_parts) >= 1:
                    break
            path_parts.append(current_folder)
            display_name = '_'.join(path_parts)
        else:
            display_name = current_folder
        
        folder_data.append((folder, group_name.strip(), display_name))
        print(f"Added: {folder} -> Group: {group_name}")
    
    if not folder_data:
        print("\nNo folders selected. Exiting.")
        return
    
    print(f"\n{len(folder_data)} folder(s) selected. Processing...\n")
    
    # Group folders by group_name
    groups = defaultdict(list)
    for folder_path, group_name, display_name in folder_data:
        groups[group_name].append((folder_path, display_name))
    
    # Process each folder and organize by group
    all_group_analyses = {}  # {group_name: [analysis_data, ...]}
    all_individual_names = []  # Track all folder names for category-level aggregation
    all_individual_hit_rates = {}  # Track hit rates by folder name
    
    for group_name, folder_list in groups.items():
        group_clean = group_name.replace(' ', '_').replace('-', '_').lower()
        
        # Create group directories
        group_json_dir = os.path.join("metadata_json", category_clean, group_clean)
        group_analysis_dir = os.path.join("metadata_analysis", category_clean, group_clean)
        os.makedirs(group_json_dir, exist_ok=True)
        os.makedirs(group_analysis_dir, exist_ok=True)
        
        print(f"Processing Group: {group_name} ({len(folder_list)} folder(s))")
        
        group_analyses = []
        group_hit_rates = []  # Track hit rates for this group
        
        for folder_path, display_name in folder_list:
            clean_name = display_name.replace(' ', '_').replace('-', '_').replace('.', '_').lower()
            
            print(f"  Processing: {display_name}")
            
            # Check if this is an Edited folder and look for RAW folder
            hit_rate = None
            if 'edited' in os.path.basename(folder_path).lower():
                raw_folder = detect_raw_folder(folder_path)
                if raw_folder:
                    hit_rate = calculate_hit_rate(folder_path, raw_folder)
                    if hit_rate:
                        print(f"    Hit Rate: {hit_rate['edited']}/{hit_rate['raw']} = {hit_rate['percentage']:.1f}%")
                        group_hit_rates.append(hit_rate)
                        all_individual_hit_rates[display_name] = hit_rate
            
            # Extract metadata
            metadata_list = process_folder(folder_path)
            
            if not metadata_list:
                print(f"    No images found\n")
                continue
            
            print(f"    Found {len(metadata_list)} images")
            
            # Save raw metadata JSON in group folder
            json_path = os.path.join(group_json_dir, f"metadata_{clean_name}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_list, f, indent=4)
            print(f"    Saved: {json_path}")
            
            # Analyze metadata
            analysis_data = analyze_metadata(metadata_list, display_name)
            group_analyses.append(analysis_data)
            all_individual_names.append(display_name)
            
            # Save individual analysis in group folder
            analysis_text = format_analysis_output(analysis_data, hit_rate)
            analysis_path = os.path.join(group_analysis_dir, f"analysis_{clean_name}.txt")
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write(analysis_text)
            print(f"    Saved: {analysis_path}\n")
        
        # Aggregate within group if multiple folders
        if len(group_analyses) > 1:
            print(f"  Aggregating group: {group_name}")
            group_aggregated = aggregate_analyses(group_analyses)
            group_folder_names = [name for _, name in folder_list]
            
            # Calculate combined hit rate for group if applicable
            group_hit_rate = None
            if group_hit_rates:
                total_edited = sum(hr['edited'] for hr in group_hit_rates)
                total_raw = sum(hr['raw'] for hr in group_hit_rates)
                if total_raw > 0:
                    group_hit_rate = {
                        'edited': total_edited,
                        'raw': total_raw,
                        'percentage': (total_edited / total_raw) * 100
                    }
            
            group_text = format_aggregated_output(group_aggregated, group_folder_names, None, group_analyses, group_hit_rate)
            
            # Save group aggregation in the group folder
            group_agg_path = os.path.join(group_analysis_dir, f"aggregated_{group_clean}.txt")
            with open(group_agg_path, 'w', encoding='utf-8') as f:
                f.write(group_text)
            print(f"  Saved group aggregation: {group_agg_path}\n")
        
        all_group_analyses[group_name] = group_analyses
    
    # Create category-level aggregation (all groups combined)
    all_analyses = []
    for group_analyses in all_group_analyses.values():
        all_analyses.extend(group_analyses)
    
    if len(all_analyses) > 1:
        print(f"Creating category-level aggregation: {category_name}")
        category_aggregated = aggregate_analyses(all_analyses)
        
        # Build group structure for hierarchical display
        group_structure = {}
        for group_name, folder_list in groups.items():
            group_structure[group_name] = [name for _, name in folder_list]
        
        # Calculate combined hit rate for category if applicable
        category_hit_rate = None
        if all_individual_hit_rates:
            total_edited = sum(hr['edited'] for hr in all_individual_hit_rates.values())
            total_raw = sum(hr['raw'] for hr in all_individual_hit_rates.values())
            if total_raw > 0:
                category_hit_rate = {
                    'edited': total_edited,
                    'raw': total_raw,
                    'percentage': (total_edited / total_raw) * 100
                }
        
        category_text = format_aggregated_output(category_aggregated, all_individual_names, group_structure, all_analyses, category_hit_rate, all_individual_hit_rates)
        
        # Save category aggregation in the category folder root
        category_agg_path = os.path.join("metadata_analysis", category_clean, f"aggregated_{category_clean}_ALL.txt")
        with open(category_agg_path, 'w', encoding='utf-8') as f:
            f.write(category_text)
        print(f"Saved category aggregation: {category_agg_path}\n")
    
    # Display summary
    total_images = sum(a['total_count'] for a in all_analyses)
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Category: {category_name}")
    print(f"Total groups: {len(groups)}")
    print(f"Total folders processed: {len(folder_data)}")
    print(f"Total images analyzed: {total_images}")
    print(f"\nOutput structure:")
    print(f"  metadata_json/{category_clean}/<group>/metadata_<folder>.json")
    print(f"  metadata_analysis/{category_clean}/<group>/analysis_<folder>.txt")
    if len(groups) > 0:
        print(f"  metadata_analysis/{category_clean}/<group>/aggregated_<group>.txt")
    if len(all_analyses) > 1:
        print(f"  metadata_analysis/{category_clean}/aggregated_{category_clean}_ALL.txt")
    
    print("\nAnalysis complete!")


# ============================================================================
# COMBINE EXISTING ANALYSES MODE
# ============================================================================

def parse_analysis_file(filepath):
    """Parse an existing analysis text file and extract lens breakdown data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lens_breakdowns = {}
    
    # Split into lens sections - look for detailed breakdown section
    if "DETAILED BREAKDOWN BY LENS" in content:
        content = content.split("DETAILED BREAKDOWN BY LENS")[1]
    elif "Detailed Breakdowns by Lens:" in content:
        content = content.split("Detailed Breakdowns by Lens:")[1]
    
    # Split by lens headers (lines with dashes followed by "Lens:")
    lens_sections = re.split(r'-{20,}\s*\nLens: (.+?) \(Used (\d+) times\)', content)
    
    # Process each lens section
    for i in range(1, len(lens_sections), 3):
        if i+2 >= len(lens_sections):
            break
            
        lens_name = lens_sections[i]
        lens_count = int(lens_sections[i+1])
        lens_content = lens_sections[i+2]
        
        lens_data = {
            'count': lens_count,
            'shutter_speeds': Counter(),
            'apertures': Counter(),
            'isos': Counter(),
            'exposure_programs': Counter(),
            'flash_modes': Counter()
        }
        
        # Parse shutter speeds
        shutter_match = re.search(r'Shutter Speeds:(.*?)(?=Apertures:|$)', lens_content, re.DOTALL)
        if shutter_match:
            for line in shutter_match.group(1).strip().split('\n'):
                match = re.match(r'\s+(.+?):\s+(\d+)\s+times', line)
                if match:
                    speed, count = match.groups()
                    lens_data['shutter_speeds'][speed] += int(count)
        
        # Parse apertures
        aperture_match = re.search(r'Apertures:(.*?)(?=ISOs:|$)', lens_content, re.DOTALL)
        if aperture_match:
            for line in aperture_match.group(1).strip().split('\n'):
                match = re.match(r'\s+f/(.+?):\s+(\d+)\s+times', line)
                if match:
                    aperture, count = match.groups()
                    lens_data['apertures'][float(aperture)] += int(count)
        
        # Parse ISOs
        iso_match = re.search(r'ISOs:(.*?)(?=Exposure Programs:|$)', lens_content, re.DOTALL)
        if iso_match:
            for line in iso_match.group(1).strip().split('\n'):
                match = re.match(r'\s+ISO (.+?):\s+(\d+)\s+times', line)
                if match:
                    iso, count = match.groups()
                    lens_data['isos'][int(iso)] += int(count)
        
        # Parse exposure programs
        program_match = re.search(r'Exposure Programs:(.*?)(?=Flash Modes:|$)', lens_content, re.DOTALL)
        if program_match:
            for line in program_match.group(1).strip().split('\n'):
                match = re.match(r'\s+(.+?):\s+(\d+)\s+times', line)
                if match:
                    program, count = match.groups()
                    lens_data['exposure_programs'][program] += int(count)
        
        # Parse flash modes
        flash_match = re.search(r'Flash Modes:(.*?)$', lens_content, re.DOTALL)
        if flash_match:
            for line in flash_match.group(1).strip().split('\n'):
                match = re.match(r'\s+(.+?):\s+(\d+)\s+times', line)
                if match:
                    mode, count = match.groups()
                    lens_data['flash_modes'][mode] += int(count)
        
        lens_breakdowns[lens_name] = lens_data
    
    return lens_breakdowns


def combine_existing_analyses():
    """Combine multiple existing analysis text files into one aggregated analysis."""
    
    # Initialize Tkinter
    root = tk.Tk()
    root.withdraw()
    
    # Get output name
    output_name = simpledialog.askstring(
        "Combined Analysis Name",
        "Enter name for combined analysis (e.g., 'run_clubs', 'all_concerts'):"
    )
    
    if not output_name:
        print("No output name provided. Exiting.")
        return
    
    output_clean = output_name.replace(' ', '_').replace('-', '_').lower()
    
    # Select analysis files to combine - keep selecting until cancel
    print("\nSelect analysis files to combine. Click Cancel when done.\n")
    filepaths = []
    
    while True:
        filepath = filedialog.askopenfilename(
            title="Select an analysis file to combine (Cancel when done)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            break
        
        filepaths.append(filepath)
        print(f"Added: {os.path.basename(filepath)}")
    
    if not filepaths:
        print("\nNo files selected. Exiting.")
        return
    
    print(f"\n{len(filepaths)} file(s) selected. Processing...\n")
    
    # Parse all selected files and aggregate
    aggregated = {
        'lenses': defaultdict(lambda: {
            'count': 0,
            'shutter_speeds': defaultdict(int),
            'apertures': defaultdict(float),
            'isos': defaultdict(int),
            'exposure_programs': defaultdict(int),
            'flash_modes': defaultdict(int)
        })
    }
    
    file_names = []
    
    for filepath in filepaths:
        filename = os.path.basename(filepath)
        file_names.append(filename.replace('.txt', '').replace('aggregated_', '').replace('analysis_', ''))
        print(f"  Processing: {filename}")
        
        try:
            lens_data = parse_analysis_file(filepath)
            
            # Merge into aggregated data
            for lens_name, data in lens_data.items():
                agg_lens = aggregated['lenses'][lens_name]
                agg_lens['count'] += data['count']
                
                for speed, count in data['shutter_speeds'].items():
                    agg_lens['shutter_speeds'][speed] += count
                
                for aperture, count in data['apertures'].items():
                    agg_lens['apertures'][aperture] += count
                
                for iso, count in data['isos'].items():
                    agg_lens['isos'][iso] += count
                
                for program, count in data['exposure_programs'].items():
                    agg_lens['exposure_programs'][program] += count
                
                for mode, count in data['flash_modes'].items():
                    agg_lens['flash_modes'][mode] += count
        
        except Exception as e:
            print(f"    Error parsing {filename}: {e}")
            continue
    
    if not aggregated['lenses']:
        print("\nNo data was successfully parsed. Exiting.")
        return
    
    print(f"\nGenerating combined analysis...")
    
    # Format output
    combined_text = format_aggregated_output(aggregated, file_names)
    
    # Save combined analysis
    output_dir = "metadata_analysis"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"combined_{output_clean}.txt")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(combined_text)
    
    print(f"\nCombined analysis saved to: {output_path}")
    print(f"Total source files: {len(filepaths)}")
    print(f"Total lenses found: {len(aggregated['lenses'])}")
    print("\nAnalysis complete!")


def quick_single_folder_mode():
    """Quick mode: Select one folder, provide name, choose group, generate analysis."""
    root = tk.Tk()
    root.withdraw()
    
    print("\n" + "=" * 50)
    print("QUICK SINGLE FOLDER ANALYSIS")
    print("=" * 50)
    
    # Select single folder
    folder = filedialog.askdirectory(title="Select a folder to analyze")
    
    if not folder:
        print("\nNo folder selected. Exiting.")
        return
    
    print(f"\nSelected folder: {folder}")
    
    # Ask for analysis name
    analysis_name = simpledialog.askstring(
        "Analysis Name",
        "Enter a name for this analysis:"
    )
    
    if not analysis_name:
        print("\nNo name provided. Exiting.")
        return
    
    # Ask for category name
    category_name = simpledialog.askstring(
        "Category Name",
        "Enter a category name (e.g., 'Concerts', 'Travel'):"
    )
    
    if not category_name:
        print("\nNo category provided. Exiting.")
        return
    
    # Ask for group name
    group_name = simpledialog.askstring(
        "Group Name",
        "Enter a group name to save in (e.g., 'Running', 'Hiking'):"
    )
    
    if not group_name:
        print("\nNo group provided. Exiting.")
        return
    
    category_clean = category_name.replace(' ', '_').replace('-', '_').lower()
    analysis_clean = analysis_name.replace(' ', '_').replace('-', '_').lower()
    
    # Create category directories
    category_json_dir = os.path.join("metadata_json", category_clean)
    category_analysis_dir = os.path.join("metadata_analysis", category_clean)
    os.makedirs(category_json_dir, exist_ok=True)
    os.makedirs(category_analysis_dir, exist_ok=True)
    
    print(f"\nProcessing: {analysis_name}")
    
    # Check if this is an Edited folder and look for RAW folder
    hit_rate = None
    if 'edited' in os.path.basename(folder).lower():
        raw_folder = detect_raw_folder(folder)
        if raw_folder:
            hit_rate = calculate_hit_rate(folder, raw_folder)
            if hit_rate:
                print(f"  Hit Rate: {hit_rate['edited']}/{hit_rate['raw']} = {hit_rate['percentage']:.1f}%")
    
    # Extract metadata
    metadata_list = process_folder(folder)
    
    if not metadata_list:
        print(f"  No images found. Exiting.")
        return
    
    print(f"  Found {len(metadata_list)} images")
    print(f"  Found {len(metadata_list)} images")
    
    # Save raw metadata JSON
    json_path = os.path.join(category_json_dir, f"metadata_{analysis_clean}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, indent=4)
    print(f"  Saved: {json_path}")
    
    # Analyze metadata
    analysis_data = analyze_metadata(metadata_list, analysis_name)
    
    # Save individual analysis
    analysis_text = format_analysis_output(analysis_data, hit_rate)
    analysis_path = os.path.join(category_analysis_dir, f"analysis_{analysis_clean}.txt")
    with open(analysis_path, 'w', encoding='utf-8') as f:
        f.write(analysis_text)
    print(f"  Saved: {analysis_path}")
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Analysis: {analysis_name}")
    print(f"Category: {category_name}")
    print(f"Total images: {len(metadata_list)}")
    if hit_rate:
        print(f"Hit Rate: {hit_rate['percentage']:.1f}%")
    print("\nAnalysis complete!")


if __name__ == "__main__":
    # Ask user which mode to run
    root = tk.Tk()
    root.withdraw()
    
    mode = simpledialog.askstring(
        "Analysis Mode",
        "Choose analysis mode:\n\n"
        "1. Interactive Mode - Select folders one-by-one and assign groups\n"
        "2. Batch Crawl Mode - Automatically process all subfolders\n"
        "3. Combine Existing Analyses - Merge multiple analysis text files\n"
        "4. Quick Single Folder - Analyze one folder with manual naming\n\n"
        "Enter 1, 2, 3, or 4:"
    )
    
    if mode == "2":
        batch_crawl_mode()
    elif mode == "1":
        main()
    elif mode == "3":
        combine_existing_analyses()
    elif mode == "4":
        quick_single_folder_mode()
    else:
        print("Invalid selection. Exiting.")
        sys.exit(0)
