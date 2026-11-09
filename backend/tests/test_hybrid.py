import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.hybrid import Hybrid, PRODUCTS

def test_cold_start():
    r=Hybrid().recommend([],[]);assert len(r)==5 and all(x['score']==0 for x in r)
def test_contributions():
    h=[dict(product_id='p1',event_type='click')];s=[dict(user_id=u,product_id=p,weight=2) for u in ['a','b'] for p in ['p1','p3']]
    r=Hybrid().recommend(h,s)
    assert all(x['id']!='p1' and abs(x['score']-sum(x['explanation']['contributions'].values()))<1e-12 for x in r)
    assert r==Hybrid().recommend(h,list(reversed(s)))
def test_popularity():
    assert Hybrid().recommend([],[dict(user_id='a',product_id='p4',weight=1)])[0]['id']=='p4'


def test_refresh_rotates_the_five_recommendations():
    model = Hybrid()
    first = model.recommend([], [], refresh_seed=1)
    second = model.recommend([], [], refresh_seed=2)
    assert len(first) == 5
    assert len(second) == 5
    assert [x["id"] for x in first] != [x["id"] for x in second]


def test_fills_five_even_when_every_product_was_interacted_with():
    model = Hybrid()
    history = [
        {"product_id": product["id"], "event_type": "purchase", "dwell_seconds": 0}
        for product in PRODUCTS
    ]
    result = model.recommend(history, [])
    assert len(result) == min(5, len(PRODUCTS))
