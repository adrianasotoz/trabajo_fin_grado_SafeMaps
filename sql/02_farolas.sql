-- Iluminación pública (Geoportal Madrid, unidades luminosas).
-- Fuente de los datos: scripts/03_load_farolas.py

CREATE TABLE IF NOT EXISTS farolas (
    id          BIGSERIAL PRIMARY KEY,
    tipo_bloque TEXT,
    via_clase   TEXT,
    via_nombre  TEXT,
    numero      INTEGER,
    distrito    INTEGER,
    barrio      INTEGER,
    geom        GEOMETRY(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_farolas_geom ON farolas USING GIST (geom);

-- Indicador de iluminación por tramo: nº de farolas en un radio de BUFFER_M
-- metros y su densidad normalizada por cada 100m de tramo.
ALTER TABLE edges ADD COLUMN IF NOT EXISTS num_farolas INTEGER;
ALTER TABLE edges ADD COLUMN IF NOT EXISTS farolas_100m DOUBLE PRECISION;
