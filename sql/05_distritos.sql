-- Límites administrativos de los 21 distritos de Madrid (Geoportal Madrid).
-- Fuente de los datos: scripts/06_load_distritos.py
--
-- Permite el join espacial tramo -> distrito (edges.cod_distrito) y, a través
-- de él, relacionar cada tramo con `vulnerabilidad_distritos`.

CREATE TABLE IF NOT EXISTS distritos (
    cod_distrito INTEGER PRIMARY KEY,
    nombre       TEXT NOT NULL,
    area_m2      DOUBLE PRECISION,
    geom         GEOMETRY(Polygon, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_distritos_geom ON distritos USING GIST (geom);

ALTER TABLE edges ADD COLUMN IF NOT EXISTS cod_distrito INTEGER REFERENCES distritos (cod_distrito);
