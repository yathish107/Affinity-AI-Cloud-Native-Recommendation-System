"""Evaluate real supplied interaction JSON using chronological holdout; no fabricated dataset."""
import argparse,json,math,sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.hybrid import Hybrid

def metrics(ranked,relevant,k):
    if k<1:raise ValueError("k must be positive")
    if len(ranked)!=len(set(ranked)):raise ValueError("Duplicate ranked items")
    hits=[int(x in relevant) for x in ranked[:k]]
    dcg=sum(x/math.log2(i+2) for i,x in enumerate(hits))
    ideal=sum(1/math.log2(i+2) for i in range(min(k,len(relevant))))
    return {'precision':sum(hits)/k,'recall':sum(hits)/len(relevant) if relevant else 0,'ndcg':dcg/ideal if ideal else 0}
def main():
    p=argparse.ArgumentParser();p.add_argument('events');p.add_argument('--cutoff',required=True);p.add_argument('--k',type=int,default=5);p.add_argument('--output',default='evaluation.json');a=p.parse_args()
    if a.k<1:raise ValueError('k must be positive')
    cutoff=datetime.fromisoformat(a.cutoff);rows=json.loads(Path(a.events).read_text());train=defaultdict(list);truth=defaultdict(set);weights=defaultdict(float);ids=set()
    for e in rows:
        if e['event_id'] in ids:continue
        ids.add(e['event_id']);when=datetime.fromisoformat(e['created_at'])
        if when<cutoff:train[e['user_id']].append(e);weights[(e['user_id'],e['product_id'])]+={'view':1,'click':2,'purchase':5}[e['event_type']]
        else:truth[e['user_id']].add(e['product_id'])
    signals=[dict(user_id=u,product_id=p,weight=w) for (u,p),w in weights.items()];model=Hybrid();report={'cutoff':a.cutoff,'k':a.k,'input_events':len(ids),'modes':{}}
    for mode in ['content','collaborative','popularity','hybrid']:
        results=[]
        for u,relevant in truth.items():
            relevant-=set(e['product_id'] for e in train[u])
            if relevant:results.append(metrics([r['id'] for r in model.recommend(train[u],signals,a.k,mode)],relevant,a.k))
        report['modes'][mode]={'eligible_users':len(results),'metrics':{k:sum(r[k] for r in results)/len(results) for k in ['precision','recall','ndcg']} if results else None}
    Path(a.output).write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
