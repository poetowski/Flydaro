from fastapi import Request

from app.worker.opensky_client import OpenSkyClient


def get_opensky_client(request: Request) -> OpenSkyClient:
    return request.app.state.opensky_client
