from fastapi import Request

from app.worker.adsb_client import AdsbClient


def get_adsb_client(request: Request) -> AdsbClient:
    return request.app.state.adsb_client
