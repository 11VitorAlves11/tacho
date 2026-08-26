from app.main import health


def test_health_endpoint() -> None:
    assert health() == {"status": "healthy"}
