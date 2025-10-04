-- Fix env_observations schema to prevent data loss from replacements
-- This changes PRIMARY KEY from (obs_id, service_name) to proper unique constraint

BEGIN TRANSACTION;

-- Create new table with fixed schema
CREATE TABLE env_observations_new (
    obs_id TEXT,
    cluster_id INTEGER,
    service_name TEXT,
    variable TEXT,
    value REAL,
    unit TEXT,
    time_stamp TEXT,
    lat REAL,
    lon REAL,
    -- New PRIMARY KEY includes cluster_id to prevent replacements across clusters
    PRIMARY KEY (cluster_id, service_name, variable, time_stamp, obs_id)
);

-- Copy existing data
INSERT INTO env_observations_new
SELECT * FROM env_observations;

-- Drop old table
DROP TABLE env_observations;

-- Rename new table
ALTER TABLE env_observations_new RENAME TO env_observations;

-- Recreate indexes
CREATE INDEX idx_env_cluster_service ON env_observations(cluster_id, service_name);
CREATE INDEX idx_env_service ON env_observations(service_name);
CREATE INDEX idx_env_cluster ON env_observations(cluster_id);

COMMIT;

-- Verify
SELECT COUNT(*) as total_rows FROM env_observations;
SELECT service_name, COUNT(*) as count FROM env_observations GROUP BY service_name;
