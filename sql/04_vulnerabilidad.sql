-- Índice Iguala Madrid: vulnerabilidad territorial por distrito.
-- Fuente de los datos: scripts/05_load_vulnerabilidad.py
--
-- Tabla de referencia por distrito (sin geometría propia). Aún no está unida
-- a `edges`: falta cargar los polígonos de distritos de Madrid para hacer el
-- join espacial edge -> distrito. Mientras tanto se puede relacionar con
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
