import json
from collections import Counter
from fractions import Fraction

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

def analyze_metadata(analysis_name = ''):

    analysis_name = analysis_name.replace(' ','_')
    json_file_path = f"metadata_json\metadata_output_{analysis_name}.json"
    out_path = f"metadata_analysis\metadata_analysis_{analysis_name}.txt"

    # Read the JSON file
    with open(json_file_path, "r", encoding="utf-8") as f:
        metadata_list = json.load(f)

    # Initialize counters for each field
    lens_freq = Counter()
    shutter_speed_freq = Counter()
    aperture_freq = Counter()
    iso_freq = Counter()
    exposure_program_freq = Counter()
    flash_mode_freq = Counter()

    # Group metadata by lens for detailed breakdown
    lens_breakdowns = {}

    # Process each metadata entry
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

    # Print overall frequencies
    print(f"Overall Frequencies: {analysis_name}")
    print("\nLenses Used:")
    for lens, count in lens_freq.items():
        print(f"{lens}: {count} times ({count / len(metadata_list) * 100:.1f}%)")

    print("\nShutter Speeds Used:")
    for speed, count in sorted(shutter_speed_freq.items(), key=lambda x: parse_shutter_speed(x[0]) or 0):
        if speed:  # Skip empty strings
            print(f"{speed}: {count} times ({count / len(metadata_list) * 100:.1f}%)")

    print("\nApertures Used:")
    for aperture, count in sorted(aperture_freq.items(), key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
        if aperture and aperture != "":  # Skip empty strings
            print(f"{aperture}: {count} times ({count / len(metadata_list) * 100:.1f}%)")

    print("\nISOs Used:")
    for iso, count in sorted(iso_freq.items(), key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
        if iso and iso != "":  # Skip empty strings
            print(f"{iso}: {count} times ({count / len(metadata_list) * 100:.1f}%)")

    print("\nExposure Programs Used:")
    for program, count in exposure_program_freq.items():
        print(f"{program}: {count} times ({count / len(metadata_list) * 100:.1f}%)")

    print("\nFlash Modes Used:")
    for mode, count in flash_mode_freq.items():
        print(f"{mode}: {count} times ({count / len(metadata_list) * 100:.1f}%)")

    # Print detailed breakdowns by lens
    print("\nDetailed Breakdowns by Lens:")
    for lens, breakdown in lens_breakdowns.items():
        print(f"\nLens: {lens} (Used {breakdown['Count']} times)")
        print("Shutter Speeds:")
        for speed, count in sorted(breakdown["ShutterSpeed"].items(), key=lambda x: parse_shutter_speed(x[0]) or 0):
            if speed:  # Skip empty strings
                print(f"  {speed}: {count} times ({count / breakdown['Count'] * 100:.1f}%)")
        
        print("Apertures:")
        for aperture, count in sorted(breakdown["Aperture"].items(), key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
            if aperture and aperture != "":  # Skip empty strings
                print(f"  {aperture}: {count} times ({count / breakdown['Count'] * 100:.1f}%)")
        
        print("ISOs:")
        for iso, count in sorted(breakdown["ISO"].items(), key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
            if iso and iso != "":  # Skip empty strings
                print(f"  {iso}: {count} times ({count / breakdown['Count'] * 100:.1f}%)")
        
        print("Exposure Programs:")
        for program, count in breakdown["ExposureProgram"].items():
            print(f"  {program}: {count} times ({count / breakdown['Count'] * 100:.1f}%)")
        
        print("Flash Modes:")
        for mode, count in breakdown["FlashMode"].items():
            print(f"  {mode}: {count} times ({count / breakdown['Count'] * 100:.1f}%)")

    # Optionally, save the analysis to a file
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Overall Frequencies: {analysis_name}\n\n")
        f.write("Lenses Used:\n")
        for lens, count in lens_freq.items():
            f.write(f"{lens}: {count} times ({count / len(metadata_list) * 100:.1f}%)\n")
        
        f.write("\nShutter Speeds Used:\n")
        for speed, count in sorted(shutter_speed_freq.items(), key=lambda x: parse_shutter_speed(x[0]) or 0):
            if speed:
                f.write(f"{speed}: {count} times ({count / len(metadata_list) * 100:.1f}%)\n")
        
        f.write("\nApertures Used:\n")
        for aperture, count in sorted(aperture_freq.items(), key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
            if aperture and aperture != "":
                f.write(f"{aperture}: {count} times ({count / len(metadata_list) * 100:.1f}%)\n")
        
        f.write("\nISOs Used:\n")
        for iso, count in sorted(iso_freq.items(), key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
            if iso and iso != "":
                f.write(f"{iso}: {count} times ({count / len(metadata_list) * 100:.1f}%)\n")
        
        f.write("\nExposure Programs Used:\n")
        for program, count in exposure_program_freq.items():
            f.write(f"{program}: {count} times ({count / len(metadata_list) * 100:.1f}%)\n")
        
        f.write("\nFlash Modes Used:\n")
        for mode, count in flash_mode_freq.items():
            f.write(f"{mode}: {count} times ({count / len(metadata_list) * 100:.1f}%)\n")
        
        f.write("\nDetailed Breakdowns by Lens:\n")
        for lens, breakdown in lens_breakdowns.items():
            f.write(f"\nLens: {lens} (Used {breakdown['Count']} times)\n")
            f.write("Shutter Speeds:\n")
            for speed, count in sorted(breakdown["ShutterSpeed"].items(), key=lambda x: parse_shutter_speed(x[0]) or 0):
                if speed:
                    f.write(f"  {speed}: {count} times ({count / breakdown['Count'] * 100:.1f}%)\n")
            
            f.write("Apertures:\n")
            for aperture, count in sorted(breakdown["Aperture"].items(), key=lambda x: float(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
                if aperture and aperture != "":
                    f.write(f"  {aperture}: {count} times ({count / breakdown['Count'] * 100:.1f}%)\n")
            
            f.write("ISOs:\n")
            for iso, count in sorted(breakdown["ISO"].items(), key=lambda x: int(x[0]) if x[0] and isinstance(x[0], (int, float)) else float('inf')):
                if iso and iso != "":
                    f.write(f"  {iso}: {count} times ({count / breakdown['Count'] * 100:.1f}%)\n")
            
            f.write("Exposure Programs:\n")
            for program, count in breakdown["ExposureProgram"].items():
                f.write(f"  {program}: {count} times ({count / breakdown['Count'] * 100:.1f}%)\n")
            
            f.write("Flash Modes:\n")
            for mode, count in breakdown["FlashMode"].items():
                f.write(f"  {mode}: {count} times ({count / breakdown['Count'] * 100:.1f}%)\n")

    print(f"Analysis saved to 'metadata_analysis_{analysis_name}.txt'")

if __name__ == "__main__":
    analyze_metadata('idkhow_jpg')



# # metadata_analysis.py
# import json
# from collections import Counter
# from fractions import Fraction

# def parse_shutter_speed(speed_str):
#     if not speed_str or speed_str == "":
#         return None
#     try:
#         if '/' in speed_str:
#             num, denom = map(int, speed_str.split('/'))
#             return num / denom if denom != 0 else None
#         return float(speed_str)
#     except (ValueError, ZeroDivisionError):
#         return None

# def analyze_metadata(metadata_list):
#     # Initialize counters for each field
#     lens_freq = Counter()
#     shutter_speed_freq = Counter()
#     aperture_freq = Counter()
#     iso_freq = Counter()
#     exposure_program_freq = Counter()
#     flash_mode_freq = Counter()

#     # Group metadata by lens for detailed breakdown
#     lens_breakdowns = {}

#     # Process each metadata entry
#     for metadata in metadata_list:
#         lens = metadata.get("Lens", "Unknown")
#         shutter_speed = metadata.get("ShutterSpeed", "")
#         aperture = metadata.get("Aperture", "")
#         iso = metadata.get("ISO", "")
#         exposure_program = metadata.get("ExposureProgram", "Unknown")
#         flash_mode = metadata.get("FlashMode", "Unknown")

#         # Update overall frequencies
#         lens_freq[lens] += 1
#         shutter_speed_freq[shutter_speed] += 1
#         aperture_freq[aperture] += 1
#         iso_freq[iso] += 1
#         exposure_program_freq[exposure_program] += 1
#         flash_mode_freq[flash_mode] += 1

#         # Build lens-specific breakdowns
#         if lens not in lens_breakdowns:
#             lens_breakdowns[lens] = {
#                 "ShutterSpeed": Counter(),
#                 "Aperture": Counter(),
#                 "ISO": Counter(),
#                 "ExposureProgram": Counter(),
#                 "FlashMode": Counter(),
#                 "Count": 0
#             }
        
#         lens_breakdowns[lens]["ShutterSpeed"][shutter_speed] += 1
#         lens_breakdowns[lens]["Aperture"][aperture] += 1
#         lens_breakdowns[lens]["ISO"][iso] += 1
#         lens_breakdowns[lens]["ExposureProgram"][exposure_program] += 1
#         lens_breakdowns[lens]["FlashMode"][flash_mode] += 1
#         lens_breakdowns[lens]["Count"] += 1

#     # Prepare analysis data as dictionaries
#     analysis = {
#         "lens_freq": dict(lens_freq),
#         "shutter_speed_freq": dict(shutter_speed_freq),
#         "aperture_freq": dict(aperture_freq),
#         "iso_freq": dict(iso_freq),
#         "exposure_program_freq": dict(exposure_program_freq),
#         "flash_mode_freq": dict(flash_mode_freq),
#         "lens_breakdowns": lens_breakdowns
#     }

#     return analysis