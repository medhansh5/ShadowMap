-- ═══════════════════════════════════════════════════════════════════════════
-- SHADOWMAP v1.4.0 MIGRATION: PHYSICS MODELING INTEGRATION
-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRATION: 002_add_physics_fields
-- DATE: 2026-05-09
-- AUTHOR: ShadowMap Core Team
-- PURPOSE: Add v1.4 Deep Physics fields to anomalies table
-- DEPENDENCIES: 001_create_anomalies_table.sql
-- ═══════════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════════
-- ADD PHYSICS COLUMNS TO ANOMALIES TABLE
-- ═══════════════════════════════════════════════════════════════════════════
-- These fields store the v1.4 Deep Physics measurements
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE anomalies 
ADD COLUMN estimated_depth REAL NULL COMMENT 'Pothole depth in mm from double integration (v1.4 physics)',
ADD COLUMN rider_id VARCHAR(50) NULL COMMENT 'Unique rider identifier from frontend (v1.4)',
ADD COLUMN is_bottomed_out BOOLEAN DEFAULT FALSE COMMENT 'Suspension bottom-out flag (Classic 350: 130mm/80mm)',
ADD COLUMN heading REAL NULL COMMENT 'Kalman-filtered heading in degrees (v1.4 precision)',
ADD COLUMN suspension_travel_percent REAL NULL COMMENT 'Suspension travel usage percentage (0-100%)',
ADD COLUMN physics_confidence REAL NULL COMMENT 'Physics model confidence score (0-1)';

-- ═══════════════════════════════════════════════════════════════════════════
-- ADD PHYSICS COLUMNS TO TELEMETRY BUFFER
-- ═══════════════════════════════════════════════════════════════════════════
-- High-frequency ingestion buffer with physics data
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE telemetry_buffer 
ADD COLUMN rider_id VARCHAR(50) NULL COMMENT 'Rider identifier from frontend',
ADD COLUMN heading REAL NULL COMMENT 'Kalman-filtered heading in degrees',
ADD COLUMN estimated_depth REAL NULL COMMENT 'Real-time depth estimation',
ADD COLUMN is_bottomed_out BOOLEAN DEFAULT FALSE COMMENT 'Bottom-out detection flag';

-- ═══════════════════════════════════════════════════════════════════════════
-- UPDATE CONSTRAINTS FOR PHYSICS FIELDS
-- ═══════════════════════════════════════════════════════════════════════════
-- Add validation constraints for physics measurements
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE anomalies 
ADD CONSTRAINT chk_estimated_depth_range 
    CHECK (estimated_depth IS NULL OR (estimated_depth >= 0 AND estimated_depth <= 1000)), -- Max 1m (unrealistic but safe)
ADD CONSTRAINT chk_rider_id_format 
    CHECK (rider_id IS NULL OR LENGTH(TRIM(rider_id)) >= 3),
ADD CONSTRAINT chk_heading_range 
    CHECK (heading IS NULL OR (heading >= 0 AND heading < 360)),
ADD CONSTRAINT chk_suspension_travel_range 
    CHECK (suspension_travel_percent IS NULL OR (suspension_travel_percent >= 0 AND suspension_travel_percent <= 100)),
ADD CONSTRAINT chk_physics_confidence_range 
    CHECK (physics_confidence IS NULL OR (physics_confidence >= 0 AND physics_confidence <= 1));

-- ═══════════════════════════════════════════════════════════════════════════
-- CREATE INDEXES FOR PHYSICS QUERIES
-- ═══════════════════════════════════════════════════════════════════════════
-- Optimize queries for rider-specific analytics and physics reporting
-- ═══════════════════════════════════════════════════════════════════════════

CREATE INDEX idx_anomalies_rider_id ON anomalies(rider_id) WHERE rider_id IS NOT NULL;
CREATE INDEX idx_anomalies_depth ON anomalies(estimated_depth DESC) WHERE estimated_depth IS NOT NULL;
CREATE INDEX idx_anomalies_bottom_out ON anomalies(is_bottomed_out) WHERE is_bottomed_out = TRUE;
CREATE INDEX idx_anomalies_physics_confidence ON anomalies(physics_confidence DESC) WHERE physics_confidence IS NOT NULL;

CREATE INDEX idx_telemetry_rider ON telemetry_buffer(rider_id, timestamp) WHERE rider_id IS NOT NULL;
CREATE INDEX idx_telemetry_bottom_out ON telemetry_buffer(is_bottomed_out, timestamp) WHERE is_bottomed_out = TRUE;

-- ═══════════════════════════════════════════════════════════════════════════
-- SENSOR SATURATION VALIDATION FUNCTION
-- ═══════════════════════════════════════════════════════════════════════════
-- Server-side validation for sensor saturation detection
-- Classic 350 has 130mm front travel, 80mm rear travel
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION validate_sensor_saturation(
    p_estimated_depth REAL,
    p_impact_magnitude REAL DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    max_travel_mm INTEGER := 130;  -- Classic 350 front travel
    saturation_threshold_mm INTEGER := 150;  -- 20mm buffer for safety
BEGIN
    -- Check for sensor saturation
    IF p_estimated_depth IS NOT NULL AND p_estimated_depth > saturation_threshold_mm THEN
        RETURN 'SENSOR_SATURATION';
    END IF;
    
    -- Check for impossible depth (negative or >1m)
    IF p_estimated_depth IS NOT NULL AND (p_estimated_depth < 0 OR p_estimated_depth > 1000) THEN
        RETURN 'INVALID_DEPTH';
    END IF;
    
    -- Check for extreme impact magnitude
    IF p_impact_magnitude IS NOT NULL AND p_impact_magnitude > 50.0 THEN
        RETURN 'EXTREME_IMPACT';
    END IF;
    
    -- All validations passed
    RETURN 'VALID';
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════
-- UPDATE CLUSTERING TRIGGER FOR PHYSICS DATA
-- ═══════════════════════════════════════════════════════════════════════════
-- Enhanced clustering with physics field handling
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION cluster_telemetry_points_v14()
RETURNS TRIGGER AS $$
DECLARE
    existing_anomaly RECORD;
    new_confidence FLOAT;
    validation_result TEXT;
BEGIN
    -- Validate sensor data
    validation_result := validate_sensor_saturation(NEW.estimated_depth, NEW.impact_magnitude);
    
    -- Only proceed if data is valid
    IF validation_result != 'VALID' THEN
        -- Log validation failure but still store with flag
        NEW.is_bottomed_out := TRUE;  -- Mark as potential saturation
    END IF;
    
    -- Check for existing anomaly within 2-meter radius
    SELECT id, hit_count, last_reported, estimated_depth, rider_id INTO existing_anomaly
    FROM anomalies
    WHERE is_active = TRUE
      AND ABS(latitude - NEW.latitude) < 0.00002  -- ~2 meters
      AND ABS(longitude - NEW.longitude) < 0.00002
    ORDER BY last_reported DESC
    LIMIT 1;
    
    IF FOUND THEN
        -- Update existing anomaly with physics data
        UPDATE anomalies
        SET 
            hit_count = hit_count + 1,
            last_reported = CURRENT_TIMESTAMP,
            confidence_score = calculate_confidence_decay(hit_count + 1, CURRENT_TIMESTAMP),
            impact_magnitude = GREATEST(COALESCE(impact_magnitude, 0), NEW.impact_magnitude),
            estimated_depth = GREATEST(COALESCE(estimated_depth, 0), COALESCE(NEW.estimated_depth, 0)),
            heading = COALESCE(NEW.heading, heading),
            suspension_travel_percent = GREATEST(
                COALESCE(suspension_travel_percent, 0), 
                COALESCE(NEW.estimated_depth, 0) / 1.3  -- Convert mm to percentage (130mm max)
            ),
            is_bottomed_out = COALESCE(is_bottomed_out, FALSE) OR NEW.is_bottomed_out,
            rider_id = COALESCE(NEW.rider_id, rider_id)
        WHERE id = existing_anomaly.id;
        
        RETURN NULL;  -- Don't insert new row
    ELSE
        -- Create new anomaly entity with physics data
        NEW.confidence_score := calculate_confidence_decay(1, CURRENT_TIMESTAMP);
        NEW.hit_count := 1;
        NEW.first_reported := CURRENT_TIMESTAMP;
        NEW.last_reported := CURRENT_TIMESTAMP;
        
        -- Calculate suspension travel percentage
        IF NEW.estimated_depth IS NOT NULL THEN
            NEW.suspension_travel_percent := (NEW.estimated_depth / 1.3);  -- 130mm = 100%
        END IF;
        
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════
-- DROP OLD TRIGGER AND CREATE NEW ONE
-- ═══════════════════════════════════════════════════════════════════════════

DROP TRIGGER IF EXISTS trigger_cluster_telemetry ON telemetry_buffer;

CREATE TRIGGER trigger_cluster_telemetry_v14
    AFTER INSERT ON telemetry_buffer
    FOR EACH ROW
    EXECUTE FUNCTION cluster_telemetry_points_v14();

-- ═══════════════════════════════════════════════════════════════════════════
-- MIGRATION COMPLETE
-- ═══════════════════════════════════════════════════════════════════════════
-- Next Steps:
-- 1. Update SQLAlchemy Anomaly model in app.py
-- 2. Enhance /api/event endpoint to parse physics JSON fields
-- 3. Test sensor saturation validation with depth > 150mm
-- 4. Update frontend to send rider_id and physics data
-- ═══════════════════════════════════════════════════════════════════════════
