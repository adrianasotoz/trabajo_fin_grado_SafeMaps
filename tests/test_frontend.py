"""ST1-ST2: pruebas de caja negra del visor frontend (Sección 6.5, ST1-ST2)."""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

CONTAR_FETCH_JS = """
window.__callCounts = {geocode: 0, ruta: 0};
const origFetch = window.fetch;
window.fetch = function(url, ...args) {
    const s = String(url);
    if (s.includes('/api/geocode')) window.__callCounts.geocode++;
    if (s.includes('/api/ruta')) window.__callCounts.ruta++;
    return origFetch(url, ...args);
};
"""


def esperar_hasta(driver, condicion, timeout=10, intervalo=0.25):
    """Sondea `condicion(driver)` hasta que sea verdadera o expire `timeout`."""
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion(driver):
            return True
        time.sleep(intervalo)
    return False


def seleccionar_sugerencia(driver, campo, texto):
    input_ = driver.find_element(By.ID, f"input-{campo}")
    input_.click()
    input_.send_keys(texto)

    ok = esperar_hasta(
        driver,
        lambda d: len(d.find_elements(By.CSS_SELECTOR, f"#sugerencias-{campo} li.sugerencia")) > 0,
        timeout=10,
    )
    assert ok, f"no llegaron sugerencias para '{texto}' en el campo {campo}"
    driver.find_elements(By.CSS_SELECTOR, f"#sugerencias-{campo} li.sugerencia")[0].click()


@pytest.fixture
def driver(live_server):
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,900")
    drv = webdriver.Chrome(options=opts)
    drv.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": CONTAR_FETCH_JS})
    drv.get(live_server)
    esperar_hasta(drv, lambda d: d.find_elements(By.ID, "input-origen"), timeout=10)
    yield drv
    drv.quit()


def test_debounce_limita_peticiones_de_geocode(driver):
    """ST1: escribir una dirección completa dispara una única petición a
    /api/geocode (debounce de 400 ms), no una por cada pulsación de tecla."""
    origen = driver.find_element(By.ID, "input-origen")
    texto = "Puerta del Sol"
    origen.click()
    origen.send_keys(texto)

    ok = esperar_hasta(driver, lambda d: d.execute_script("return window.__callCounts.geocode;") >= 1)
    assert ok, "no se lanzó ninguna petición a /api/geocode tras escribir"

    time.sleep(1)  # margen para descartar peticiones adicionales tardías
    conteos = driver.execute_script("return window.__callCounts;")
    assert conteos["geocode"] == 1
    assert conteos["geocode"] < len(texto)


def test_cambio_de_modo_no_repite_peticion_a_api_ruta(driver):
    """ST2: alternar entre modo simple y detallado reutiliza la última
    respuesta de /api/ruta en el cliente, sin llamadas adicionales al backend."""
    seleccionar_sugerencia(driver, "origen", "Puerta del Sol")
    seleccionar_sugerencia(driver, "destino", "Estacion de Atocha")

    ok = esperar_hasta(driver, lambda d: d.execute_script("return window.__callCounts.ruta;") >= 1, timeout=15)
    assert ok, "no se lanzó ninguna petición a /api/ruta tras fijar origen y destino"

    time.sleep(1)
    conteos = driver.execute_script("return window.__callCounts;")
    assert conteos["ruta"] == 1

    for modo in ("detallado", "simple", "detallado"):
        driver.find_element(By.ID, f"modo-{modo}").click()
        time.sleep(0.3)

    conteos = driver.execute_script("return window.__callCounts;")
    assert conteos["ruta"] == 1
