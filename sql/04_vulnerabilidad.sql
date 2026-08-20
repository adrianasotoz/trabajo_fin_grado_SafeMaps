-- Índice Iguala Madrid: vulnerabilidad territorial por distrito.
-- Fuente de los datos: scripts/05_load_vulnerabilidad.py
--
-- Tabla de referencia por distrito (sin geometría propia). Se relaciona con
-- `edges` a través de `edges.cod_distrito` (ver sql/05_distritos.sql) y con
-- `accidentes` por `cod_distrito`.

CREATE TABLE IF NOT EXISTS vulnerabilidad_distritos (
    cod_distrito                    INTEGER PRIMARY KEY,
    nombre_distrito                 TEXT,
    anio                             INTEGER,
    ivt_agregado                     DOUBLE PRECISION,
    ivt_bienestar_social_igualdad    DOUBLE PRECISION,
    ivt_medio_ambiente_movilidad     DOUBLE PRECISION,
    ivt_educacion_cultura            DOUBLE PRECISION,
    ivt_economia_empleo              DOUBLE PRECISION,
    ivt_salud                        DOUBLE PRECISION
);
