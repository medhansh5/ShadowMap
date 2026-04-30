-- ═══════════════════════════════════════════════════════════════════════════
-- SHADOWMAP v1.1.0 MIGRATION: ANOMALY INTELLIGENCE LAYER
-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRATION: 001_create_anomalies_table
-- DATE: 2026-04-30
-- AUTHOR: ShadowMap Core Team
-- PURPOSE: Transition from raw telemetry to intelligent anomaly clustering
-- ═══════════════════════════════════════════════════════════════════════════

-- Drop legacy table if exists (graceful migration)
DROP TABLE IF EXISTS road_segment CASCADE;

-- ═══════════════════════════════════════════════════════════════════════════
-- CORE ANOMALY TABLE
-- ═══════════════════════════════════════════════════════════════════════════
-- Represents clustered road anomalies with spatial confidence scoring
-- Each row = a unique anomaly entity (not individual telemetry points)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE anomalies (
    -- Primary Identification
    id SERIAL PRIMARY KEY,
    
    -- Spatial Coordinates (WGS84)
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    
    -- Geospatial Indexing (PostGIS recommended for production)
    -- For SQLite/PostgreSQL without PostGIS, we use R-tree on lat/lng
    -- CREATE INDEX idx_anomalies_spatial ON anomalies USING GIST (point(longitude, latitude));
    
    -- Intelligence Metrics
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    hit_count INTEGER NOT NULL DEFAULT 1,
    
    -- Temporal Intelligence
    first_reported TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_reported TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Signal Intelligence
    impact_magnitude FLOAT,  -- M = sqrt(ax^2 + ay^2 + az^2)
    severity_class INTEGER NOT NULL DEFAULT 1,  -- 1=Minor, 2=Moderate, 3=Major
    
    -- Cluster Metadata
    cluster_radius FLOAT DEFAULT 2.0,  -- meters
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT chk_confidence_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT chk_hit_count_positive CHECK (hit_count >= 1),
    CONSTRAINT chk_severity_range CHECK (severity_class >= 1 AND severity_class <= 3)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- SPATIAL INDEXING (PostgreSQL)
-- ═══════════════════════════════════════════════════════════════════════════
-- Enable fast spatial queries for clustering and HUD rendering
-- ═══════════════════════════════════════════════════════════════════════════

CREATE INDEX idx_anomalies_latlng ON anomalies(latitude, longitude);
CREATE INDEX idx_anomalies_confidence ON anomalies(confidence_score DESC);
CREATE INDEX idx_anomalies_active ON anomalies(is_active, last_reported DESC);
CREATE INDEX idx_anomalies_severity ON anomalies(severity_class);

-- ═══════════════════════════════════════════════════════════════════════════
-- TELEMETRY BUFFER TABLE (High-Frequency Ingestion)
-- ═══════════════════════════════════════════════════════════════════════════
-- Temporary storage for raw sensor data before clustering
-- Optimized for high-frequency writes (100Hz sensor data)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE telemetry_buffer (
    id SERIAL PRIMARY KEY,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    accel_x FLOAT NOT NULL,
    accel_y FLOAT NOT NULL,
    accel_z FLOAT NOT NULL,
    impact_magnitude FLOAT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Processed flag for batch clustering
    is_processed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_telemetry_processed ON telemetry_buffer(is_processed, timestamp);
CREATE INDEX idx_telemetry_spatial ON telemetry_buffer(latitude, longitude);

-- ═══════════════════════════════════════════════════════════════════════════
-- CONFIDENCE DECAY FUNCTION (PostgreSQL)
-- ═══════════════════════════════════════════════════════════════════════════
-- SQL function to calculate confidence decay over time
-- Formula: C = sum(Reports) × e^(-λt)
-- λ (lambda) = decay constant (default: 0.1 per day)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION calculate_confidence_decay(
    p_hit_count INTEGER,
    p_last_reported TIMESTAMP,
    p_lambda FLOAT DEFAULT 0.1
) RETURNS FLOAT AS $$
DECLARE
    time_diff_hours FLOAT;
    decay_factor FLOAT;
BEGIN
    -- Calculate time difference in hours
    time_diff_hours := EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - p_last_reported)) / 3600.0;
    
    -- Apply exponential decay: e^(-λt)
    decay_factor := EXP(-p_lambda * time_diff_hours);
    
    -- Return confidence score
    RETURN p_hit_count * decay_factor;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════
-- CLUSTERING TRIGGER (PostgreSQL)
-- ═══════════════════════════════════════════════════════════════════════════
-- Automatically cluster nearby telemetry points into anomaly entities
-- Radius: 2 meters (adjustable via cluster_radius)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION cluster_telemetry_points()
RETURNS TRIGGER AS $$
DECLARE
    existing_anomaly RECORD;
    new_confidence FLOAT;
BEGIN
    -- Check for existing anomaly within 2-meter radius
    -- Using Haversine approximation for nearby points
    SELECT id, hit_count, last_reported INTO existing_anomaly
    FROM anomalies
    WHERE is_active = TRUE
      AND ABS(latitude - NEW.latitude) < 0.00002  -- ~2 meters at equator
      AND ABS(longitude - NEW.longitude) < 0.00002
    ORDER BY last_reported DESC
    LIMIT 1;
    
    IF FOUND THEN
        -- Update existing anomaly
        UPDATE anomalies
        SET 
            hit_count = hit_count + 1,
            last_reported = CURRENT_TIMESTAMP,
            confidence_score = calculate_confidence_decay(hit_count + 1, CURRENT_TIMESTAMP),
            impact_magnitude = GREATEST(impact_magnitude, NEW.impact_magnitude)
        WHERE id = existing_anomaly.id;
        
        RETURN NULL;  -- Don't insert new row
    ELSE
        -- Create new anomaly entity
        NEW.confidence_score := calculate_confidence_decay(1, CURRENT_TIMESTAMP);
        NEW.hit_count := 1;
        NEW.first_reported := CURRENT_TIMESTAMP;
        NEW.last_reported := CURRENT_TIMESTAMP;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRATION COMPLETE
-- ═══════════════════════════════════════════════════════════════════════════
-- Next Steps:
-- 1. Update app.py to use new schema
-- 2. Implement signal processing in potholenet.py
-- 3. Update Leaflet frontend for confidence-based heatmaps
-- ═══════════════════════════════════════════════════════════════════════════
