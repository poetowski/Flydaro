import httpx
import pytest

from app.worker.adsb_client import AdsbClient


@pytest.fixture
async def client():
    c = AdsbClient()
    yield c
    await c.aclose()


def _fake_get(json_body):
    async def fake_get(url, **kwargs):
        return httpx.Response(200, json=json_body, request=httpx.Request("GET", url))

    return fake_get


async def test_get_state_for_icao24_parses_ac_key(client, monkeypatch):
    """Regression test: /v2/hex/ wraps its result under "ac", not
    "aircraft" -- using the wrong key here silently made every on-demand
    landing check look like "aircraft not found" regardless of reality."""
    monkeypatch.setattr(
        client._http,
        "get",
        _fake_get(
            {
                "ac": [
                    {
                        "hex": "abc123",
                        "flight": "TST123 ",
                        "lat": 52.3,
                        "lon": 4.8,
                        "alt_baro": 1000,
                        "gs": 200.0,
                        "baro_rate": -500,
                        "t": "A320",
                    }
                ],
                "msg": "No error",
            }
        ),
    )

    state = await client.get_state_for_icao24("abc123")

    assert state is not None
    assert state.icao24 == "abc123"
    assert state.callsign == "TST123"
    assert state.on_ground is False
    assert state.aircraft_type_code == "A320"


async def test_get_state_for_icao24_returns_none_when_not_found(client, monkeypatch):
    monkeypatch.setattr(client._http, "get", _fake_get({"ac": [], "msg": "No error"}))

    assert await client.get_state_for_icao24("ffffff") is None


async def test_get_states_near_parses_aircraft_key(client, monkeypatch):
    """Companion test locking in the geo-radius endpoint's (already
    correct) top-level key, distinct from /v2/hex/'s "ac"."""
    monkeypatch.setattr(
        client._http,
        "get",
        _fake_get(
            {
                "aircraft": [
                    {
                        "hex": "abc123",
                        "flight": "TST123 ",
                        "lat": 52.3,
                        "lon": 4.8,
                        "alt_baro": "ground",
                        "gs": 0.0,
                    }
                ],
                "now": 0,
            }
        ),
    )

    states = await client.get_states_near(52.3, 4.8, 30.0)

    assert len(states) == 1
    assert states[0].icao24 == "abc123"
    assert states[0].on_ground is True
