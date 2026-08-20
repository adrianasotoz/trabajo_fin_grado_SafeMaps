-- Esquema base para la red viaria peatonal (OSM) enrutable con pgRouting.
-- Fuente de los datos: scripts/01_download_osm.py

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgrouting;

-- Nodos de la red (intersecciones / vértices)
CREATE TABLE IF NOT EXISTS nodes (
    osmid        BIGINT PRIMARY KEY,
    x            DOUBLE PRECISION NOT NULL,
    y            DOUBLE PRECISION NOT NULL,
    highway      TEXT,
    street_count INTEGER,
    geom         GEOMETRY(Point, 4326) NOT NULL
);

-- Tramos de la red (aristas), listos para pgr_dijkstra vía source/target
CREATE TABLE IF NOT EXISTS edges (
    id           BIGSERIAL PRIMARY KEY,
    osmid        TEXT,
    u            BIGINT NOT NULL REFERENCES nodes (osmid),
    v            BIGINT NOT NULL REFERENCES nodes (osmid),
    key          INTEGER NOT NULL,
    source       BIGINT NOT NULL,
    target       BIGINT NOT NULL,
    highway      TEXT,
    name         TEXT,
    oneway       BOOLEAN,
    length       DOUBLE PRECISION,
    cost         DOUBLE PRECISION,
    reverse_cost DOUBLE PRECISION,
    geom         GEOMETRY(LineString, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_geom ON nodes USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_edges_geom ON edges USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges (source);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges (target);
