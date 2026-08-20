-- Índice de peligrosidad por tramo e índice de coste seguro para pgRouting.
-- Fuente: scripts/07_calcular_indice_seguridad.py
--
-- indice_peligrosidad combina, en una escala [0, ~1], siniestralidad general,
-- atropellos, vulnerabilidad territorial del distrito e iluminación (esta
-- última como factor protector). cost_seguro/reverse_cost_seguro son el
-- coste que usa pgr_dijkstra: la longitud del tramo penalizada según su
-- peligrosidad, para que la ruta "segura" prefiera rodear zonas de riesgo.

ALTER TABLE edges ADD COLUMN IF NOT EXISTS indice_peligrosidad DOUBLE PRECISION;
ALTER TABLE edges ADD COLUMN IF NOT EXISTS cost_seguro DOUBLE PRECISION;
ALTER TABLE edges ADD COLUMN IF NOT EXISTS reverse_cost_seguro DOUBLE PRECISION;
