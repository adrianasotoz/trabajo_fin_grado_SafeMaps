import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine
import os

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "scripts"))

load_dotenv(BASE / ".env")

BASE_URL = "http://127.0.0.1:5000"


@pytest.fixture(scope="session")
def base_dir():
    return BASE


@pytest.fixture(scope="session")
def engine():
    return create_engine(
        "postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}".format(
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            dbname=os.environ["DB_NAME"],
        )
    )


@pytest.fixture(scope="session")
def live_server():
    """Arranca `web/app.py` para las pruebas de integración/caja negra si no
    hay ya un servidor escuchando en el puerto 5000, y lo detiene al terminar
    la sesión de tests si fue este fixture quien lo arrancó."""
    try:
        requests.get(BASE_URL, timeout=1)
        yield BASE_URL
        return
    except requests.RequestException:
        pass

    proc = subprocess.Popen(
        [sys.executable, str(BASE / "web/app.py")],
        cwd=BASE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(60):
        try:
            requests.get(BASE_URL, timeout=1)
            break
        except requests.RequestException:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("El servidor Flask no arrancó a tiempo para los tests.")

    yield BASE_URL

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
