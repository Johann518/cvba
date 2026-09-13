DROP TABLE IF EXISTS vacant_buildings;

CREATE TABLE vacant_buildings (
    service_request_number TEXT PRIMARY KEY,
    date_received           DATE,
    location_on_lot         TEXT,
    is_dangerous            INTEGER,   -- 0/1
    open_or_boarded         TEXT,
    entry_point             TEXT,
    vacant_or_occupied      TEXT,
    vacant_due_to_fire      INTEGER,   -- 0/1
    people_using_property   INTEGER,   -- 0/1
    street_number           TEXT,
    street_direction        TEXT,
    street_name             TEXT,
    street_suffix           TEXT,
    zip_code                TEXT,
    ward                    INTEGER,
    police_district         INTEGER,
    community_area          INTEGER,
    latitude                REAL,
    longitude               REAL
);

CREATE INDEX idx_vb_community_area ON vacant_buildings (community_area);
CREATE INDEX idx_vb_date ON vacant_buildings (date_received);

-- Chicago community area number -> name lookup, used to make charts readable.
DROP TABLE IF EXISTS community_areas;
CREATE TABLE community_areas (
    area_number INTEGER PRIMARY KEY,
    area_name   TEXT
);
