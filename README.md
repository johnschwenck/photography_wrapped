# Photo Metadata Analysis System

A comprehensive, object-oriented system for analyzing EXIF metadata from photography sessions with support for local and cloud storage, centralized database, and flexible reporting.

## 🌟 Features

### Core Capabilities
- **EXIF Extraction**: Extract comprehensive metadata from various image formats (.arw, .jpg, .png, etc.)
- **Centralized Database**: SQLite with easy migration to PostgreSQL/MySQL for cloud deployments
- **Cloud Storage Support**: Seamless integration with AWS S3, Azure Blob Storage, and Google Cloud Storage
- **OOP Architecture**: Clean, maintainable code with proper separation of concerns
- **Flexible Analysis**: Analyze at session, group, or category levels with automatic aggregation
- **Hit Rate Calculation**: Track editing efficiency (edited photos / RAW photos)
- **Comprehensive Statistics**: Lens usage, camera settings distributions, exposure patterns
- **Backward Compatible**: Maintains existing text report format

### New in v2.0 (Refactored Architecture)
- ✨ Object-oriented design with clear domain models
- 🗄️ Centralized SQLite database (cloud-ready)
- ☁️ Cloud storage abstraction layer (S3, Azure, GCS)
- 📊 Pre-calculated statistics with caching
- 🔍 Flexible querying and filtering
- 🚀 Command-line interface for automation
- 📦 Modular architecture for easy extension
- 📝 Comprehensive documentation with type hints

## 🏗️ Architecture

```
RunClubSocialHub/
├── models/              # Domain models (PhotoMetadata, Session, Lens, etc.)
├── database/            # Database schema and manager (SQLite/PostgreSQL/MySQL)
├── storage/             # Storage providers (Local, S3, Azure, GCS)
├── extractors/          # EXIF extraction from images
├── analyzers/           # Statistical analysis and aggregation
├── reporters/           # Report generation (text, JSON, CSV)
├── migrations/          # Data migration tools
├── cli.py              # Command-line interface
├── config.yaml         # Configuration file
└── requirements.txt    # Python dependencies
```

## 📋 Requirements

- Python 3.8+
- [exiftool](https://exiftool.org/) installed and accessible in PATH
- PyYAML, pyexiftool
- Optional: boto3 (S3), azure-storage-blob (Azure), google-cloud-storage (GCS)

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
Edit `config.yaml` to match your setup (local vs cloud storage)

### 3. Migrate Existing Data (if applicable)
```bash
python cli.py migrate --json-dir metadata_json/
```

### 4. Extract New Photos
```bash
python cli.py extract /path/to/photos --category running --group weekly --name "2025-04-03"
python cli.py extract /path/to/photos --category running --group weekly --name "2025-04-03"
```

### 5. Analyze & Report
```bash
python cli.py analyze running/weekly --type group --report
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

## 🔧 Configuration

### Database Options
```yaml
database:
  type: sqlite  # or postgresql, mysql
  sqlite:
    path: metadata.db
```

### Storage Options
```yaml
storage:
  type: local  # or s3, azure, gcs
  
  s3:
    bucket: ${S3_BUCKET}
    region: us-east-1
```

### Analysis Options
```yaml
analysis:
  enable_caching: true
  calculate_hit_rate: true
  metrics:
    - lens_frequency
    - shutter_speed_distribution
    - iso_distribution
```

## 📊 Database Schema

- **categories**: Top-level organization (concerts, running, weddings)
- **groups**: Sub-categories within categories
- **sessions**: Individual photography events
- **photos**: Photo metadata records
- **lenses**: Lens information and usage stats
- **aggregated_stats**: Cached analysis results

## 🔄 Migration from Legacy System

The new system maintains backward compatibility:

1. Existing JSON files in `metadata_json/` can be migrated
2. Text reports are generated in the same format
3. Folder structure is preserved
4. All historical data is imported

```bash
# Migrate all existing JSON files
python cli.py migrate --json-dir metadata_json/

# Verify migration
python cli.py list sessions
```

## 🌐 Cloud Deployment

### AWS S3 + PostgreSQL
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

### Azure
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

## 🔌 Python API

```python
from extractors import ExifExtractor
from analyzers import StatisticsAnalyzer
from reporters import TextReporter

# Extract
extractor = ExifExtractor.from_config()
session = extractor.extract_folder(
    folder_path='/photos/event',
    session_name='event_2025',
    category='concerts',
    group='rock'
)

# Analyze
analyzer = StatisticsAnalyzer.from_config()
analysis = analyzer.analyze_session(session.id)

# Report
reporter = TextReporter.from_config()
reporter.generate_report(analysis)
```

## 📈 Example Output

```
Analysis: running_sole - weekly
================================================================================

Total photos analyzed: 2565
Hit Rate: 29.8%

OVERALL METRICS
--------------------------------------------------------------------------------
Lens Type Distribution:
  Prime Lenses: 1701 photos (66.3%)
    - FE 85mm F1.4 GM II: 1185 photos
    - FE 135mm F1.8 GM: 516 photos
  Zoom Lenses: 864 photos (33.7%)
    - 24-70mm F2.8 DG DN | Art 019: 864 photos

Overall Shutter Speed Distribution:
  1/200: 1089 times (42.5%)
  1/250: 567 times (22.1%)
  ...
```

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- ExifTool by Phil Harvey
- All the photographers using this tool to analyze their work