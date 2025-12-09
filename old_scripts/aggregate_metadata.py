import os
import re
import tkinter as tk
from tkinter import filedialog
from collections import defaultdict
from fractions import Fraction

def parse_metadata_file(filepath):
    """Parse a metadata analysis text file and extract the data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {
        'lenses': defaultdict(lambda: {
            'count': 0,
            'shutter_speeds': defaultdict(int),
            'apertures': defaultdict(float),
            'isos': defaultdict(int),
            'exposure_programs': defaultdict(int),
            'flash_modes': defaultdict(int)
        })
    }
    
    # Split into lens sections
    lens_sections = re.split(r'\nLens: (.+?) \(Used (\d+) times\)\n', content)
    
    # Process each lens section (skip first element which is the overall summary)
    for i in range(1, len(lens_sections), 3):
        if i+2 >= len(lens_sections):
            break
            
        lens_name = lens_sections[i]
        lens_count = int(lens_sections[i+1])
        lens_content = lens_sections[i+2]
        
        lens_data = data['lenses'][lens_name]
        lens_data['count'] += lens_count
        
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
                match = re.match(r'\s+(.+?):\s+(\d+)\s+times', line)
                if match:
                    aperture, count = match.groups()
                    lens_data['apertures'][float(aperture)] += int(count)
        
        # Parse ISOs
        iso_match = re.search(r'ISOs:(.*?)(?=Exposure Programs:|$)', lens_content, re.DOTALL)
        if iso_match:
            for line in iso_match.group(1).strip().split('\n'):
                match = re.match(r'\s+(.+?):\s+(\d+)\s+times', line)
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
    
    return data

def aggregate_files(directory=None, specific_files=None):
    """Aggregate data from metadata analysis files.
    
    Args:
        directory: Directory containing files (will process all files if specific_files not provided)
        specific_files: List of specific file paths to aggregate
    """
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
    
    files_processed = []
    
    # Determine which files to process
    if specific_files:
        # Process only specific files
        filepaths = specific_files
    elif directory:
        # Find all metadata analysis files in directory
        filepaths = []
        for filename in os.listdir(directory):
            if filename.startswith('metadata_analysis_') and filename.endswith('.txt'):
                filepaths.append(os.path.join(directory, filename))
    else:
        raise ValueError("Either directory or specific_files must be provided")
    
    # Process each file
    for filepath in filepaths:
        filename = os.path.basename(filepath)
        print(f"Processing: {filename}")
        
        data = parse_metadata_file(filepath)
        files_processed.append(filename)
        
        # Merge data
        for lens_name, lens_data in data['lenses'].items():
            agg_lens = aggregated['lenses'][lens_name]
            agg_lens['count'] += lens_data['count']
            
            for speed, count in lens_data['shutter_speeds'].items():
                agg_lens['shutter_speeds'][speed] += count
            
            for aperture, count in lens_data['apertures'].items():
                agg_lens['apertures'][aperture] += count
            
            for iso, count in lens_data['isos'].items():
                agg_lens['isos'][iso] += count
            
            for program, count in lens_data['exposure_programs'].items():
                agg_lens['exposure_programs'][program] += count
            
            for mode, count in lens_data['flash_modes'].items():
                agg_lens['flash_modes'][mode] += count
    
    return aggregated, files_processed

def format_output(aggregated, files_processed):
    """Format the aggregated data into a readable text output."""
    output = ["Aggregated Metadata Analysis"]
    output.append("=" * 50)
    output.append(f"\nFiles processed: {len(files_processed)}")
    for filename in sorted(files_processed):
        output.append(f"  - {filename}")
    output.append("\n" + "=" * 50)
    
    # Sort lenses by count (descending)
    sorted_lenses = sorted(aggregated['lenses'].items(), 
                          key=lambda x: x[1]['count'], 
                          reverse=True)
    
    for lens_name, lens_data in sorted_lenses:
        output.append(f"\nLens: {lens_name} (Used {lens_data['count']} times)")
        
        # Shutter speeds
        output.append("Shutter Speeds:")
        sorted_speeds = sorted(lens_data['shutter_speeds'].items(), 
                              key=lambda x: eval(x[0]) if '/' in x[0] else float(x[0]),
                              reverse=True)
        for speed, count in sorted_speeds:
            percentage = (count / lens_data['count']) * 100
            output.append(f"  {speed}: {count} times ({percentage:.1f}%)")
        
        # Apertures
        output.append("Apertures:")
        sorted_apertures = sorted(lens_data['apertures'].items())
        for aperture, count in sorted_apertures:
            percentage = (count / lens_data['count']) * 100
            output.append(f"  {aperture}: {int(count)} times ({percentage:.1f}%)")
        
        # ISOs
        output.append("ISOs:")
        sorted_isos = sorted(lens_data['isos'].items())
        for iso, count in sorted_isos:
            percentage = (count / lens_data['count']) * 100
            output.append(f"  {iso}: {count} times ({percentage:.1f}%)")
        
        # Exposure programs
        output.append("Exposure Programs:")
        sorted_programs = sorted(lens_data['exposure_programs'].items(), 
                                key=lambda x: x[1], 
                                reverse=True)
        for program, count in sorted_programs:
            percentage = (count / lens_data['count']) * 100
            output.append(f"  {program}: {count} times ({percentage:.1f}%)")
        
        # Flash modes
        output.append("Flash Modes:")
        sorted_modes = sorted(lens_data['flash_modes'].items(), 
                             key=lambda x: x[1], 
                             reverse=True)
        for mode, count in sorted_modes:
            percentage = (count / lens_data['count']) * 100
            output.append(f"  {mode}: {count} times ({percentage:.1f}%)")
    
    return "\n".join(output)

def main():
    # Directory containing metadata analysis files
    analysis_dir = "metadata_analysis"
    
    # Create root window (hidden)
    root = tk.Tk()
    root.withdraw()
    
    # Ask user whether to process all files or select specific ones
    print("Choose aggregation mode:")
    print("1. Process all metadata analysis files in the 'metadata_analysis' directory")
    print("2. Select specific files to aggregate")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "2":
        # Let user select specific files
        print("\nSelect metadata analysis files to aggregate...")
        filepaths = filedialog.askopenfilenames(
            title="Select Metadata Analysis Files",
            initialdir=analysis_dir if os.path.exists(analysis_dir) else ".",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepaths:
            print("No files selected. Exiting.")
            return
        
        print(f"\nSelected {len(filepaths)} files")
        
        # Aggregate the selected files
        aggregated, files_processed = aggregate_files(specific_files=list(filepaths))
        output_file = os.path.join(analysis_dir if os.path.exists(analysis_dir) else ".", 
                                   "aggregated_metadata_analysis_selected.txt")
    else:
        # Process all files in directory
        if not os.path.exists(analysis_dir):
            print(f"Error: Directory '{analysis_dir}' not found!")
            return
        
        print("\nAggregating metadata from all concert files...\n")
        
        # Aggregate all files in directory
        aggregated, files_processed = aggregate_files(directory=analysis_dir)
        output_file = os.path.join(analysis_dir, "aggregated_metadata_analysis.txt")
    
    if not files_processed:
        print("No metadata analysis files found!")
        return
    
    # Format and display output
    output_text = format_output(aggregated, files_processed)
    print("\n" + output_text)
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_text)
    
    print(f"\n\nAggregated analysis saved to: {output_file}")

if __name__ == "__main__":
    main()
