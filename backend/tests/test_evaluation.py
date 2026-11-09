import importlib.util,sys,json,subprocess
from pathlib import Path
import pytest
path=Path(__file__).resolve().parents[2]/'scripts/evaluate.py'
spec=importlib.util.spec_from_file_location('evaluate',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_metrics():
    r=m.metrics(['a','b','c'],{'a','c'},3)
    assert r['precision']==pytest.approx(2/3) and r['recall']==1
    assert r['ndcg']==pytest.approx(1.5/(1+1/__import__('math').log2(3)))
def test_empty_metrics():assert m.metrics([],set(),5)==dict(precision=0,recall=0,ndcg=0)
@pytest.mark.parametrize('kind',['empty','duplicates','cold'])
def test_chronology(tmp_path,kind):
    rows=[]
    if kind!='empty':
        rows=[dict(event_id='1',user_id='a',product_id='p1',event_type='click',dwell_seconds=0,created_at='2020-01-01T00:00:00+00:00'),dict(event_id='2',user_id='b' if kind=='cold' else 'a',product_id='p2',event_type='click',dwell_seconds=0,created_at='2021-01-01T00:00:00+00:00')]
        if kind=='duplicates':rows.append(rows[0])
    f=tmp_path/'events.json';f.write_text(json.dumps(rows));out=tmp_path/'result.json'
    subprocess.run([sys.executable,str(path),str(f),'--cutoff','2020-06-01T00:00:00+00:00','--output',str(out)],check=True)
    result=json.loads(out.read_text());assert result['input_events']==(0 if kind=='empty' else 2)
    assert result['modes']['hybrid']['eligible_users']==(0 if kind=='empty' else 1)
def test_invalid(tmp_path):
    f=tmp_path/'bad.json';f.write_text('[{}]')
    assert subprocess.run([sys.executable,str(path),str(f),'--cutoff','2020-01-01T00:00:00+00:00'],capture_output=True).returncode!=0
