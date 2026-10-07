from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from chiron.api.main import app
from chiron.db.base import Base
from chiron.db.models import Player
from chiron.db.session import get_db, normalize_database_url

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_endpoint_structure():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"chiron_http" in response.content or b"python" in response.content


def test_list_players_empty():
    response = client.get("/api/v1/players")
    assert response.status_code == 200
    assert response.json() == []


def test_pipeline_status_empty():
    response = client.get("/api/v1/pipeline/status")
    assert response.status_code == 200
    assert response.json() == []


def test_dashboard_home():
    response = client.get("/")
    assert response.status_code == 200
    assert b"Chiron" in response.content
    assert b"/docs" in response.content


def test_dashboard_player_page():
    session = TestingSessionLocal()
    session.add(Player(id=2544, full_name="LeBron James", team_abbrev="LAL", position="F"))
    session.commit()
    session.close()

    response = client.get("/players/2544")
    assert response.status_code == 200
    assert b"LeBron James" in response.content

    listed = client.get("/api/v1/players")
    assert listed.status_code == 200
    names = [row["full_name"] for row in listed.json()]
    assert "LeBron James" in names


def test_dashboard_player_not_found():
    response = client.get("/players/999999")
    assert response.status_code == 404


def test_normalize_database_url_render():
    url = normalize_database_url("postgres://user:pass@dpg-abc.oregon-postgres.render.com/chiron")
    assert url.startswith("postgresql://")
    assert "sslmode=require" in url


def test_normalize_database_url_local():
    local = normalize_database_url("postgresql://chiron:chiron@localhost:5432/chiron")
    compose = normalize_database_url("postgresql://chiron:chiron@postgres:5432/chiron")
    assert "sslmode" not in local
    assert "sslmode" not in compose
