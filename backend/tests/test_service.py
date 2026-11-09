import os,importlib
from unittest.mock import Mock
from fastapi.testclient import TestClient

def module(monkeypatch,role):
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://test:test@localhost/test')
    monkeypatch.setenv('APP_ROLE',role)
    import app.service as s
    s.role=role
    return s

def test_recommendation_cache_fallback(monkeypatch):
    s=module(monkeypatch,'recommendation');store=Mock();store.model_snapshot.return_value=(1,[],[]);cache=Mock();cache.get.return_value=None;cache.key.return_value='v1'
    monkeypatch.setattr(s,'store',store);monkeypatch.setattr(s,'cache',cache)
    r=TestClient(s.app).get('/recommendations/a');assert r.status_code==200 and len(r.json()['recommendations'])==5;cache.put.assert_called_once()
def test_gateway_communication_failure(monkeypatch):
    s=module(monkeypatch,'api')
    def fail(*a,**kw):raise s.httpx.ConnectError('unavailable')
    monkeypatch.setattr(s.httpx,'get',fail)
    assert TestClient(s.app).get('/recommendations/a').status_code==503
