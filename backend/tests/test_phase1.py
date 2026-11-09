import os, sys, tempfile, json, subprocess
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
os.environ['DB_PATH'] = ':memory:'
os.environ['ALLOW_LEGACY_SQLITE'] = '1'
os.environ.pop('DATABASE_URL',None)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import main as m
from fastapi.testclient import TestClient
import kafka

class Producer:
    def __init__(self, **kwargs): pass
    def send(self,*args): return self
    def get(self,**kwargs): return None
    def flush(self,**kwargs): pass
    def close(self,**kwargs): pass

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setattr(kafka,'KafkaProducer',Producer)
    m.DB.execute('DELETE FROM events'); m.DB.commit()

client=TestClient(m.app) # No lifespan: no real broker thread.
def payload(**kw):
    return dict(event_id=str(uuid4()),user_id='alice',product_id='p1',event_type='click',**kw)

@pytest.mark.parametrize('kind',['view','click','purchase'])
def test_valid(kind):
    x=payload();x['event_type']=kind
    r=client.post('/events',json=x)
    assert r.status_code==200 and r.json()['event']==dict(x,dwell_seconds=0)
    assert len(client.get('/events/alice').json())==1

@pytest.mark.parametrize('field,value,status',[
 ('user_id','',422),('user_id','  ',422),('user_id','x'*101,422),
 ('event_id','invalid',422),('event_type','invalid',422),('product_id','missing',404),
 ('dwell_seconds',-1,422),('dwell_seconds',36001,422),('dwell_seconds','NaN',422),
 ('dwell_seconds','Infinity',422),('user_id',None,422)])
def test_invalid(field,value,status):
    x=payload();x[field]=value
    assert client.post('/events',json=x).status_code==status
    assert not m.get_events('alice')

@pytest.mark.parametrize('field',['user_id','product_id','event_type'])
def test_missing(field):
    x=payload();del x[field]
    assert client.post('/events',json=x).status_code==422

def test_malformed():
    assert client.post('/events',content='{',headers={'Content-Type':'application/json'}).status_code==422

def test_retry_and_consumer_replay():
    x=payload()
    for _ in range(4): assert client.post('/events',json=x).status_code==200
    m.save_event(m.Event(**x))
    assert len(m.get_events('alice'))==1

def test_concurrent_retries():
    x=payload()
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes=list(pool.map(lambda _:client.post('/events',json=x).status_code,range(16)))
    assert codes==[200]*16 and len(m.get_events('alice'))==1

def test_conflict():
    x=payload();client.post('/events',json=x);x['product_id']='p2'
    assert client.post('/events',json=x).status_code==409
    assert len(m.get_events('alice'))==1

def test_legacy_generated_ids():
    x=payload();del x['event_id']
    a=client.post('/events',json=x).json();b=client.post('/events',json=x).json()
    assert a['event']['event_id']!=b['event']['event_id']
    assert len(m.get_events('alice'))==2

def test_failed_delivery(monkeypatch):
    def fail(self,**kw): raise RuntimeError('delivery failed')
    monkeypatch.setattr(Producer,'get',fail)
    r=client.post('/events',json=payload())
    assert r.status_code==200 and r.json()['published_to_broker'] is False
    assert len(m.get_events('alice'))==1

@pytest.mark.parametrize('counts',[{'p1':1,'p2':3},{'p5':4,'p2':1},{'p12':2,'p1':1}])
def test_popularity(counts):
    for pid,count in counts.items():
        for i in range(count):
            x=payload();x.update(product_id=pid,user_id=f'{pid}-{i}')
            client.post('/events',json=x)
    result=client.get('/recommendations/new').json()['recommendations']
    assert result[0]['id']==max(counts,key=counts.get)

def test_repeat_user_not_popularity():
    for _ in range(10):client.post('/events',json=payload())
    assert client.get('/recommendations/new').json()['recommendations'][0]['score']==0.01

def test_existing_routes():
    assert client.get('/health').json()['status']=='ok'
    assert len(client.get('/products').json())==12
    assert client.get('/events/unknown').json()==[]
    client.post('/events',json=payload())
    for limit,n in [(0,1),(5,5),(100,11)]:
        r=client.get(f'/recommendations/alice?limit={limit}').json()['recommendations']
        assert len(r)==n and all(p['id']!='p1' for p in r)
    assert client.get('/recommendations/alice?limit=bad').status_code==422

def test_hash_seeds():
    code='from app.main import engine; import json; es=[dict(product_id="p1",event_type="click"),dict(product_id="p3",event_type="purchase")]; print(json.dumps(engine.recommend(es),sort_keys=True))'
    outputs=[]
    for seed in [1,2,3,4,5,7,19,99]:
        env={**os.environ,'PYTHONHASHSEED':str(seed),'DB_PATH':':memory:','PYTHONPATH':str(Path(__file__).resolve().parents[1]),'OPENBLAS_NUM_THREADS':'1'}
        outputs.append(subprocess.check_output([sys.executable,'-c',code],env=env,text=True))
    assert len(set(outputs))==1
