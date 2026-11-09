"""Use dedicated disposable TEST_DATABASE_URL and TEST_REDIS_URL only."""
import os,sys
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.storage import Store,outbox,events,processed,signals
from app.cache import Cache
from sqlalchemy import select,func,update

def payload():return dict(event_id=str(uuid4()),user_id=str(uuid4()),product_id='p1',event_type='click',dwell_seconds=0)
@pytest.fixture
def store():
    url=os.getenv('TEST_DATABASE_URL')
    if not url:pytest.skip('Real PostgreSQL TEST_DATABASE_URL not provided')
    return Store(url)
def test_atomic_duplicate_concurrency(store):
    p=payload()
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:store.accept(p),range(8)))
    assert results.count(True)==1
    with store.engine.connect() as c:
        assert c.execute(select(func.count()).select_from(outbox).where(outbox.c.event_id==p['event_id'])).scalar()==1
    assert store.apply(p) is True
    assert store.apply(p) is False
    with store.engine.connect() as c:assert c.execute(select(signals.c.weight).where(signals.c.user_id==p['user_id'])).scalar()==2

def test_cache_version_and_recovery(store):
    url=os.getenv('TEST_REDIS_URL')
    if not url:pytest.skip('Real Redis TEST_REDIS_URL not provided')
    cache=Cache(url);cache.client.ping();p=payload()
    v,_,_=store.snapshot(p['user_id']);key=cache.key(p['user_id'],5,v)
    cache.put(key,{'old':True});assert cache.get(key)=={'old':True}
    store.accept(p);v2,_,_=store.snapshot(p['user_id']);assert v2>v
    assert cache.get(cache.key(p['user_id'],5,v2)) is None
    broken=Cache('redis://127.0.0.1:1/0');assert broken.get(key) is None;broken.put(key,{})
    assert cache.get(key)=={'old':True}

def test_lease_expiry_fences_old_owner(store):
    p=payload();store.accept(p)
    # Run against an otherwise empty dedicated test database.
    first=store.claim(seconds=-1);assert first is not None
    second=store.claim();assert second['event_id']==first['event_id']
    assert store.finish(first) is False
    assert store.finish(second) is True
