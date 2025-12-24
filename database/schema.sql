-- Photo Metadata Analysis System Database Schema
-- =================================================
-- This schema supports SQLite, PostgreSQL, and MySQL with minor modifications
-- For PostgreSQL/MySQL: Replace AUTOINCREMENT with AUTO_INCREMENT or SERIAL

-- Categories Table
-- Represents top-level organization (concerts, running, weddings, etc.)
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    total_groups INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    total_photos INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Groups Table
-- Represents sub-categories or series within a category
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    description TEXT,
    total_sessions INTEGER DEFAULT 0,
    total_photos INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(name, category_id)
);

-- Sessions Table
-- Represents individual photography sessions/events
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    group_name TEXT NOT NULL,
    category_id INTEGER,
    group_id INTEGER,
    date TIMESTAMP,
    date_detected TEXT,
    location TEXT,
    description TEXT,
    folder_path TEXT,
    raw_folder_path TEXT,
    total_photos INTEGER DEFAULT 0,
    total_raw_photos INTEGER,
    hit_rate REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL,
    UNIQUE(name, category, group_name)
);

-- Lenses Table
-- Represents camera lenses and their characteristics
CREATE TABLE IF NOT EXISTS lenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    lens_type TEXT CHECK(lens_type IN ('prime', 'zoom', 'unknown')),
    manufacturer TEXT,
    focal_length_min REAL,
    focal_length_max REAL,
    max_aperture REAL,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Photos Table
-- Represents individual photos with their EXIF metadata
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    lens_id INTEGER,
    file_path TEXT,
    file_name TEXT NOT NULL,
    camera TEXT,
    lens_name TEXT,
    focal_length REAL,
    iso INTEGER,
    aperture REAL,
    shutter_speed TEXT,
    shutter_speed_decimal REAL,
    exposure_program TEXT,
    exposure_bias REAL,
    flash_mode TEXT,
    date_taken TIMESTAMP,
    date_only TEXT,
    time_only TEXT,
    day_of_week TEXT,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    file_modified_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (lens_id) REFERENCES lenses(id) ON DELETE SET NULL
);

-- Aggregated Statistics Table
-- Stores pre-calculated statistics for fast retrieval
CREATE TABLE IF NOT EXISTS aggregated_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregation_type TEXT NOT NULL CHECK(aggregation_type IN ('session', 'group', 'category', 'custom')),
    aggregation_id INTEGER,
    aggregation_name TEXT NOT NULL,
    filter_criteria TEXT,
    total_sessions INTEGER DEFAULT 0,
    total_photos INTEGER DEFAULT 0,
    total_raw_photos INTEGER,
    hit_rate REAL,
    lens_statistics TEXT,
    camera_statistics TEXT,
    settings_statistics TEXT,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(aggregation_type, aggregation_name, filter_criteria)
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_photos_session_id ON photos(session_id);
CREATE INDEX IF NOT EXISTS idx_photos_lens_id ON photos(lens_id);
CREATE INDEX IF NOT EXISTS idx_photos_date_taken ON photos(date_taken);
CREATE INDEX IF NOT EXISTS idx_photos_lens_name ON photos(lens_name);
CREATE INDEX IF NOT EXISTS idx_sessions_category ON sessions(category);
CREATE INDEX IF NOT EXISTS idx_sessions_group ON sessions(group_name);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_groups_category_id ON groups(category_id);
CREATE INDEX IF NOT EXISTS idx_aggregated_stats_type ON aggregated_stats(aggregation_type);

-- Triggers for automatic timestamp updates (SQLite)
CREATE TRIGGER IF NOT EXISTS update_categories_timestamp 
AFTER UPDATE ON categories
BEGIN
    UPDATE categories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_groups_timestamp 
AFTER UPDATE ON groups
BEGIN
    UPDATE groups SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_sessions_timestamp 
AFTER UPDATE ON sessions
BEGIN
    UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_lenses_timestamp 
AFTER UPDATE ON lenses
BEGIN
    UPDATE lenses SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_photos_timestamp 
AFTER UPDATE ON photos
BEGIN
    UPDATE photos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Views for Common Queries

-- View: Session Summary with Photo Counts
CREATE VIEW IF NOT EXISTS v_session_summary AS
SELECT 
    s.id,
    s.name,
    s.category,
    s.group_name,
    s.date,
    s.total_photos,
    s.total_raw_photos,
    s.hit_rate,
    COUNT(DISTINCT p.lens_name) as unique_lenses,
    c.name as category_name,
    g.name as group_full_name
FROM sessions s
LEFT JOIN photos p ON s.id = p.session_id
LEFT JOIN categories c ON s.category_id = c.id
LEFT JOIN groups g ON s.group_id = g.id
GROUP BY s.id;

-- View: Lens Usage Statistics
CREATE VIEW IF NOT EXISTS v_lens_usage AS
SELECT 
    l.id,
    l.name,
    l.lens_type,
    l.manufacturer,
    COUNT(p.id) as photo_count,
    COUNT(DISTINCT p.session_id) as session_count,
    MIN(p.date_taken) as first_used,
    MAX(p.date_taken) as last_used
FROM lenses l
LEFT JOIN photos p ON l.id = p.lens_id
GROUP BY l.id;

-- View: Category Statistics
CREATE VIEW IF NOT EXISTS v_category_stats AS
SELECT 
    c.id,
    c.name,
    COUNT(DISTINCT g.id) as total_groups,
    COUNT(DISTINCT s.id) as total_sessions,
    COUNT(p.id) as total_photos,
    COALESCE(AVG(s.hit_rate), 0) as avg_hit_rate
FROM categories c
LEFT JOIN groups g ON c.id = g.category_id
LEFT JOIN sessions s ON g.id = s.group_id
LEFT JOIN photos p ON s.id = p.session_id
GROUP BY c.id;
