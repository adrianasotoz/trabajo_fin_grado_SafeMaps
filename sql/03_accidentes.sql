-- Accidentes de tráfico (Datos Abiertos Madrid), un registro por accidente.
-- Fuente de los datos: scripts/04_load_accidentes.py

CREATE TABLE IF NOT EXISTS accidentes (
    id              BIGSERIAL PRIMARY KEY,
    num_expediente  TEXT UNIQUE NOT NULL,
    fecha           DATE,
    hora            TIME,
    cod_distrito    INTEGER,
    distrito        TEXT,
    tipo_accidente  TEXT,
    lesividad_max   TEXT,
    atropello_peaton BOOLEAN NOT NULL DEFAULT FALSE,
    geom            GEOMETRY(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accidentes_geom ON accidentes USING GIST (geom);

-- Indicador de siniestralidad por tramo: nº de accidentes (y de atropellos)
-- en un radio de BUFFER_M metros y su densidad normalizada por cada 100m.
ALTER TABLE edges ADD COLUMN IF NOT EXISTS num_accidentes INTEGER;
ALTER TABLE edges ADD COLUMN IF NOT EXISTS accidentes_100m DOUBLE PRECISION;
ALTER TABLE edges ADD COLUMN IF NOT EXISTS num_atropellos INTEGER;
