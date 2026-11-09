import json,sys,sqlite3
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock
from uuid import uuid4
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.worker import relay_once,consume_once
from app.envelope import decode_event
from app.import_sqlite import read_rows

def message(raw):return NS(value=raw,topic='user-events',partition=0,offset=4)
def payload():return dict(event_id=str(uuid4()),user_id='a',product_id='p1',event_type='click',dwell_seconds=0)
@pytest.mark.parametrize('raw',[b'{',b'[]',b'null',b'\xff',b'{}'])
def test_poison_commits_after_quarantine(raw):
    calls=[];s=Mock();c=Mock();s.quarantine.side_effect=lambda *a:calls.append('quarantine');c.commit.side_effect=lambda *a:calls.append('commit')
    consume_once(s,c,message(raw));assert calls==['quarantine','commit'];s.apply.assert_not_called()
def test_quarantine_failure_no_commit():
    s=Mock();c=Mock();s.quarantine.side_effect=RuntimeError('db down')
    with pytest.raises(RuntimeError):consume_once(s,c,message(b'{'))
    c.commit.assert_not_called()
def test_apply_failure_no_commit():
    s=Mock();c=Mock();s.apply.side_effect=RuntimeError('db down')
    with pytest.raises(RuntimeError):consume_once(s,c,message(json.dumps(payload()).encode()))
    c.commit.assert_not_called()
def test_relay_ack_before_finish():
    calls=[];s=Mock();p=Mock();s.claim.return_value={'payload':payload()};p.send.return_value.get.side_effect=lambda **k:calls.append('ack');s.finish.side_effect=lambda *a:calls.append('finish')
    relay_once(s,p);assert calls==['ack','finish']
def test_crash_after_ack_leaves_claim():
    s=Mock();p=Mock();s.claim.return_value={'payload':payload()};s.finish.side_effect=RuntimeError('process crashed')
    with pytest.raises(RuntimeError):relay_once(s,p)
    p.send.return_value.get.assert_called_once();assert s.finish.call_count==1
def test_failed_ack_not_published():
    s=Mock();p=Mock();s.claim.return_value={'payload':payload()};p.send.return_value.get.side_effect=RuntimeError('timeout')
    with pytest.raises(RuntimeError):relay_once(s,p)
    assert s.finish.call_args.args[1]=='timeout'
def test_migration_preserves_instant(tmp_path):
    f=tmp_path/'old.db'
    with sqlite3.connect(f) as c:
        c.execute('CREATE TABLE events(id INTEGER,user_id TEXT,product_id TEXT,event_type TEXT,dwell_seconds REAL,created_at TEXT)')
        c.execute("INSERT INTO events VALUES(1,'a','p1','click',0,'2020-01-01T05:30:00+05:30')")
    before=f.read_bytes();a=read_rows(f,'stable');b=read_rows(f,'stable')
    assert a==b and a[0][1].isoformat()=='2020-01-01T00:00:00+00:00' and f.read_bytes()==before
