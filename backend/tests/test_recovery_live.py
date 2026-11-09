"""Destructive tests restricted to dedicated Compose integration database."""
import os,sys,json,time
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace as NS
import pytest
from sqlalchemy import text,select,func,update
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.storage import Store,events,outbox,processed,signals
from app.worker import relay_once,consume_once
from app.cache import Cache
from kafka import KafkaProducer,KafkaConsumer

@pytest.fixture
def store():
    if os.getenv('INTEGRATION_TEST_MODE')!='isolated':pytest.skip('Dedicated integration environment required')
    s=Store(os.environ['TEST_DATABASE_URL'])
    assert s.engine.url.database=='recommend_integration'
    with s.engine.begin() as c:c.execute(text('TRUNCATE processed_events,user_item_signals,outbox,events,dead_letters CASCADE'))
    return s

def data():return dict(event_id=str(uuid4()),user_id=str(uuid4()),product_id='p1',event_type='click',dwell_seconds=0)

def test_transaction_rollback(store):
    # Force the outbox insertion to fail after the event INSERT.
    with store.engine.begin() as c:c.execute(text("ALTER TABLE outbox ADD CONSTRAINT test_fail CHECK (attempts < 0) NOT VALID"))
    try:
        with pytest.raises(Exception):store.accept(data())
        with store.engine.connect() as c:assert c.execute(select(func.count()).select_from(events)).scalar()==0
    finally:
        with store.engine.begin() as c:c.execute(text('ALTER TABLE outbox DROP CONSTRAINT test_fail'))

def test_concurrent_claims(store):
    for _ in range(12):store.accept(data())
    with ThreadPoolExecutor(max_workers=12) as pool:rows=list(pool.map(lambda _:store.claim(),range(12)))
    assert len({r['event_id'] for r in rows})==12
    assert store.claim() is None

def test_ack_crash_replay_and_consumer_restart(store):
    p=data();store.accept(p)
    producer=KafkaProducer(bootstrap_servers='broker:9092',value_serializer=lambda x:json.dumps(x).encode(),acks='all')
    original=store.finish
    def crash(*a,**kw):raise RuntimeError('injected crash after broker ACK')
    store.finish=crash
    try:
        with pytest.raises(RuntimeError):relay_once(store,producer)
    finally:store.finish=original
    with store.engine.begin() as c:c.execute(update(outbox).values(lease_until=func.now()-text("INTERVAL '60 seconds'")))
    assert relay_once(store,producer)
    group='test-'+str(uuid4());seen=0
    consumer=KafkaConsumer('user-events',bootstrap_servers='broker:9092',group_id=group,enable_auto_commit=False,auto_offset_reset='earliest',consumer_timeout_ms=15000,max_poll_records=1)
    try:
        for msg in consumer:
            value=json.loads(msg.value)
            if value['event_id']!=p['event_id']:continue
            store.apply(value) # crash after DB commit, before offset commit
            break
        else:pytest.fail('No broker event received')
    finally:consumer.close()
    consumer=KafkaConsumer('user-events',bootstrap_servers='broker:9092',group_id=group,enable_auto_commit=False,auto_offset_reset='earliest',consumer_timeout_ms=15000,max_poll_records=1)
    try:
        for msg in consumer:
            if json.loads(msg.value)['event_id']!=p['event_id']:continue
            consume_once(store,consumer,msg);seen+=1
            if seen>=2:break
    finally:consumer.close();producer.close()
    assert seen==2
    with store.engine.connect() as c:assert c.execute(select(signals.c.weight).where(signals.c.user_id==p['user_id'])).scalar()==2

def test_redis_process_restart_and_fallback(store):
    import redis
    cache=Cache('redis://redis:6379/0');cache.client.ping();p=data();store.accept(p)
    version,history,pop=store.snapshot(p['user_id']);key=cache.key(p['user_id'],5,version);cache.put(key,{'value':1});assert cache.get(key)=={'value':1}
    try:cache.client.execute_command('SHUTDOWN','NOSAVE')
    except redis.RedisError:pass
    # Integration Redis supervisor deliberately waits three seconds before restart.
    assert cache.get(key) is None
    version2,history2,pop2=store.snapshot(p['user_id']);assert history2==history and pop2==pop
    cache.put(key,{'value':2}) # best effort while down
    deadline=time.monotonic()+20
    while True:
        try:cache.client.ping();break
        except redis.RedisError:
            if time.monotonic()>deadline:raise
            time.sleep(.2)
    cache.put(key,{'value':3});assert cache.get(key)=={'value':3}
