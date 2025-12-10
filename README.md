# Photographer Wrapped

Analyze your photography metadata and see your year in review - like Spotify Wrapped, but for photographers.

## What It Does

Extract EXIF data from your photos, analyze your shooting patterns, and get insights about your photography progression over time.

**Key Features:**
- **Modern Web UI** with real-time extraction and database management
- Extract metadata from RAW and JPG files (supports all ExifTool formats)
- Calculate hit rate (edited photos / total RAW photos)
- **Smart date extraction** from folder paths and filenames
- Analyze lens usage, camera settings, shooting patterns
- Temporal trend analysis (see your progression throughout the year)
- Generate "Wrapped" style year-in-review reports
- Local processing (photos never leave your computer)
- Clean OOP architecture with centralized SQLite database

## Project Structure

```
photography_wrapped/
├── analyzers/           # Statistical analysis engine
│   ├── statistics_analyzer.py
│   └── analyze_temporal_trends.py  # "Wrapped" generator
├── database/           # SQLite database manager & schema
├── extractors/         # EXIF metadata extraction with date heuristics
├── migrations/         # Database migration scripts
├── models/            # Data models (Photo, Session, Lens, Analysis)
├── reporters/         # Report generation (text, JSON)
├── static/            # Web UI (HTML, CSS, JavaScript)
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── storage/           # Storage providers (local, S3, etc.)
├── cli.py            # Command-line interface
├── run_local.py      # Flask web server for local UI
├── config.yaml       # Configuration
├── requirements.txt  # Python dependencies
└── metadata.db       # SQLite database (generated)
```

## Requirements

- Python 3.8+
- ExifTool (must be installed separately)
  - Windows: Download from https://exiftool.org/
  - Mac: `brew install exiftool`
  - Linux: `sudo apt install exiftool`
- Dependencies: PyYAML, pyexiftool

Optional for cloud storage:
- boto3 (AWS S3)
- azure-storage-blob (Azure)
- google-cloud-storage (GCS)

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/johnschwenck/photography_wrapped.git
cd photography_wrapped

# Install dependencies
pip install -r requirements.txt
```

### Web Interface (Recommended)

The easiest way to use Photographer Wrapped is through the web interface:

```bash
# Start the local web server
python run_local.py
```

Then open your browser to `http://localhost:5000`

**Features:**
- Single folder or crawl mode extraction
- Automatic date detection from folder paths and filenames
- Real-time extraction progress
- Database management with edit/delete capabilities
- Analysis and "Wrapped" report generation
- Clean, modern UI

### CLI Usage (Alternative)

For automation or scripting, use the command-line interface:

```bash
# Extract metadata from a single folder
python cli.py extract "C:\Photos\2025" --category personal --group year_2025

# Analyze and generate report
python cli.py analyze personal/year_2025 --report

# Generate temporal trends ("Wrapped" report)
python analyzers/analyze_temporal_trends.py
```

## Date Extraction

Photographer Wrapped intelligently extracts dates from your photo organization:

### Automatic Date Detection

The system uses a **hierarchical approach** to find session dates:

1. **Manual Input**: Use the date field if you want to specify a date
2. **Folder Path Heuristics**: Automatically detects dates in folder names (e.g., `2025-04-03`, `04-03-2025`, `20250403`)
3. **Filename Fallback**: Scans photo filenames if no date found in path
   - If 1 unique date: Uses that date
   - If multiple dates: Uses the most common (mode)
   - Example: `IMG_20250403_123456.jpg` → `2025-04-03`

### Supported Date Formats

- `YYYY-MM-DD`: 2025-04-03
- `MM-DD-YYYY`: 04-03-2025
- `MM-DD-YY`: 04-03-25
- `YY-MM-DD`: 25-04-03
- `YYYYMMDD`: 20250403 (compact)

**Note**: The system will show you how the date was determined (path, filename with details, or not found).

## Folder Structure & RAW Detection

**IMPORTANT**: This system is designed to work with **final edited photos only**. Point the extraction to your edited/exported photos folder, NOT the parent directory containing RAW files.

### Recommended Folder Structure

The system works best with this structure:
```
E:\Photos\Session Name\
├── Edited\          # Point extraction HERE (your final JPGs/TIFFs)
└── RAW\             # System automatically detects this one level up
```

### How RAW Detection Works

1. **You point to**: The folder containing your **final edited photos**
2. **System automatically looks**: One level up for a folder named `RAW`, `Raw`, `raw`, `RAW Files`, or `Raws`
3. **If RAW folder found**: Calculates hit rate (edited photos / RAW photos)
4. **If no RAW folder**: Sets hit rate to `-` (null) and focuses on edited photos only

### Common Mistakes to Avoid

**❌ WRONG - Don't point to parent directory:**
```
E:\Photos\2025-07-19 - Costa\    # Contains multiple subfolders
├── Photos\
│   ├── Edited\    # 28 JPGs (what you want)
│   └── RAW\       # 767 ARW files
└── Videos\        # 377 MP4 files

Pointing here will scan EVERYTHING recursively = wrong totals!
```

**✅ CORRECT - Point to the edited folder:**
```
E:\Photos\2025-07-19 - Costa\Photos\Edited\    # ← Extract from here!

System will automatically look for:
E:\Photos\2025-07-19 - Costa\Photos\RAW\       # ← Found! Calculate hit rate
```

### Example Scenarios

#### Scenario 1: With RAW Files (Hit Rate Calculation)
```
Session Folder/
├── Edited/         # 25 JPGs ← Point here
└── RAW/           # 250 RAW files ← Auto-detected

Result: 25 photos, Hit rate: 10.0% (25/250)
```

#### Scenario 2: Without RAW Files (Edits Only)
```
Session Folder/
└── Edited/        # 40 JPGs ← Point here

Result: 40 photos, Hit rate: - (no RAW folder found)
```

#### Scenario 3: Flat Structure (No RAW Files)
```
Session Folder/    # 100 JPGs directly here ← Point here
Result: 100 photos, Hit rate: - (no RAW folder found)
```

## Walkthrough Example: The Sole Running Club

Here's a complete walkthrough using photos from "The Sole" running club as an example:

### Step 1: Organize Your Photos

Assume you have a folder structure like this:
```
E:\Photos\The Sole\
├── 01 - 2025-04-03\
│   ├── Edited\          # Your edited JPGs ← Extraction targets these
│   └── RAW\             # Auto-detected for hit rate
├── 02 - 2025-04-10\
│   ├── Edited\
│   └── RAW\
└── ... (more weeks)
```

### Step 2: Crawl and Extract All Sessions

Use the `crawl` command to process all folders automatically:

```bash
python cli.py crawl "E:\Photos\The Sole" --category running --group thesole --target-folder Edited
```

This command:
- Recursively finds all folders named "Edited"
- Extracts EXIF metadata from each edited photo
- Automatically detects RAW folders one level up from each Edited folder
- Calculates hit rate if RAW folder exists
- Creates separate sessions for each week
- Names sessions based on folder structure (e.g., "01_-_2025-04-03")

### Step 3: Analyze the Group

```bash
# Analyze all sessions in the group
python cli.py analyze running/thesole --type group --report
```

This generates a comprehensive report showing:
- Total photos across all sessions
- Overall hit rate
- Lens usage patterns
- Camera settings distributions
- Top combinations of settings

### Step 4: Generate Temporal Trends

```bash
python analyzers/analyze_temporal_trends.py
```

This shows your progression throughout the year:
```
THE SOLE 2025: TEMPORAL TRENDS ANALYSIS
Total Sessions: 29
Date Range: 2025-04-03 to 2025-12-04

Monthly Average Hit Rate:
  2025-04: 31.73% (1 sessions)
  2025-05: 20.08% (5 sessions)
  2025-11: 40.01% (4 sessions)

85mm F1.4 GM II Usage Over Time:
  2025-04: 33 photos (11.7%)
  2025-11: 276 photos (87.6%)
  You found your favorite lens!

Wide Open (f/1.4 or f/1.8) Usage:
  2025-04: 46.6%
  2025-12: 90.6%
  You committed to bokeh!
```

### Step 5: Query Specific Insights

```bash
# See all sessions
python cli.py list sessions --category running

# Query specific lens usage
python cli.py query --lens "FE 85mm F1.4 GM II"

# List all categories and groups
python cli.py list categories
```

## 📖 Detailed Usage

### Extract Metadata
```bash
# From local folder
python cli.py extract /photos/event --category concerts --group idkhow --name "IDKHOW 2025"

# Without hit rate calculation
python cli.py extract /photos/event --category travel --group europe --no-hit-rate
```

### Analyze Sessions
```bash
# Single session
python cli.py analyze 1 --type session --report

# Entire group
python cli.py analyze running_sole/weekly --type group --report

# All sessions in category
python cli.py analyze concerts --type category --report
```

### List & Query
```bash
# List all categories
python cli.py list categories

# List sessions in category
python cli.py list sessions --category running_sole

# Query specific lens
python cli.py query --lens "FE 85mm F1.4 GM II"
```

## Configuration

The system uses `config.yaml` for configuration. Here's the default local setup:

```yaml
database:
  type: sqlite
  path: metadata.db

storage:
  type: local
  base_path: .

extraction:
  exiftool_path: null  # Auto-detects exiftool installation
  default_category: personal
  default_group: ungrouped
```

### Local-First Approach

Photographer Wrapped is designed to run locally on your machine:
- **No cloud costs**: Everything runs on your computer
- **Privacy first**: Your photos never leave your machine
- **Fast processing**: Direct access to local files
- **Offline capable**: No internet required

### Advanced: Cloud Storage (Optional)

For advanced users who want cloud-based storage, you can configure alternative backends:

<details>
<summary>Click to expand cloud configuration examples</summary>

#### AWS S3
```yaml
storage:
  type: s3
  bucket: your-bucket-name
  region: us-east-1
  credentials:
    access_key_id: YOUR_ACCESS_KEY
    secret_access_key: YOUR_SECRET_KEY
```

#### PostgreSQL Database
```yaml
database:
  type: postgres
  host: localhost
  port: 5432
  name: photo_metadata
  user: your_username
  password: your_password
```

</details>

**Note**: Cloud features are optional and not required for core functionality.

## Database Schema

The SQLite database maintains the following structure:

- **categories**: Top-level organization (concerts, running, weddings)
- **groups**: Sub-categories within categories
- **sessions**: Individual photography events
- **photos**: Photo metadata records with EXIF data
- **lenses**: Lens information and usage statistics

## Python API

You can also use Photographer Wrapped directly in Python:

```python
from extractors import ExifExtractor
from analyzers import StatisticsAnalyzer
from reporters import TextReporter

# Extract metadata
extractor = ExifExtractor.from_config()
session = extractor.extract_folder(
    folder_path='C:\Photos\Wedding_2025',
    session_name='Smith_Wedding',
    category='weddings',
    group='2025'
)

# Analyze results
analyzer = StatisticsAnalyzer.from_config()
analysis = analyzer.analyze_session(session.id)

# Generate report
reporter = TextReporter.from_config()
reporter.generate_report(analysis)
```

## Advanced Features

### Migration from Legacy System

If you have existing JSON metadata files, you can import them:

```bash
# Migrate all existing JSON files
python cli.py migrate --json-dir metadata_json/

# Verify migration
python cli.py list sessions
```

### Cloud Deployment (Optional)

For advanced users who need cloud deployment, the system supports:

<details>
<summary>Click to expand deployment options</summary>

#### AWS S3 + PostgreSQL
```yaml
database:
  type: postgresql
  postgresql:
    connection_string: ${DATABASE_URL}

storage:
  type: s3
  s3:
    bucket: my-photos-bucket
    region: us-east-1
```

#### Azure Blob Storage + MySQL
```yaml
database:
  type: mysql
  mysql:
    host: ${AZURE_DB_HOST}

storage:
  type: azure
  azure:
    account_name: ${AZURE_STORAGE_ACCOUNT}
    container: photos
```

</details>

**Note**: Cloud deployment is entirely optional. The local-only version provides full functionality.

## Example Output

Here's what a temporal trends analysis looks like:

```
THE SOLE 2025: TEMPORAL TRENDS ANALYSIS
================================================================================
Total Sessions: 29
Date Range: 2025-04-03 to 2025-12-04

SECTION 1: MONTHLY AVERAGE HIT RATE
2025-04: 31.73% (1 sessions)
2025-05: 20.08% (5 sessions)
2025-06: 26.02% (4 sessions)
2025-07: 27.78% (3 sessions)
2025-08: 33.15% (3 sessions)
2025-09: 28.44% (2 sessions)
2025-10: 32.39% (7 sessions)
2025-11: 40.01% (4 sessions)

SECTION 2: LENS USAGE EVOLUTION
85mm F1.4 GM II:
  2025-04: 33 photos (11.7%)
  2025-12: 125 photos (87.6%)
  You found your favorite lens!

SECTION 3: HIT RATE PROGRESSION
April: 31.73%
November: 40.01%
Improvement: +8.28 percentage points

SECTION 4: APERTURE EVOLUTION
Wide Open (f/1.4 or f/1.8):
  2025-04: 46.6%
  2025-12: 90.6%
  You committed to bokeh!

SECTION 5: FLASH USAGE
Overall: 62.5% of photos use flash
Most consistent months: October-December (72.0%)

SECTION 6: MOST CONSISTENT SETTINGS
ISO 800 + 1/320s: Used in 18 sessions
Your "go-to" combo for running events
```

## Contributing

Photographer Wrapped is open source and welcomes contributions! Areas for improvement:

- Image classification (ML-based, not keyword-based)
- Additional analysis features (gear recommendations, time-of-day patterns, etc.)
- Performance optimizations for large libraries
- Mobile-responsive UI enhancements
- Cloud deployment guides (Vercel, AWS, etc.)

## License

MIT License - see LICENSE file for details

## Support

For questions or issues:
- Open an issue on GitHub
- Check existing documentation
- Review the walkthrough example above

---

Built for photographers who want to understand their craft through data.