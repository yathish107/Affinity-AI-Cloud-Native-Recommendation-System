"""Read-only legacy import preserving original instants; rejects ambiguous naive times."""
import argparse,sqlite3
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid5,NAMESPACE_URL
from .storage import Store
from .envelope import decode_event
import json

def read_rows(source,source_id):
    with sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute('SELECT * FROM events ORDER BY id').fetchall()
    result=[]
    for row in rows:
        x=dict(row)
        timestamp=datetime.fromisoformat(x['created_at'].replace('Z','+00:00'))
        if timestamp.tzinfo is None:raise ValueError(f"Row {x['id']}: timestamp has no timezone; resolve before import")
        event={k:x[k] for k in ['user_id','product_id','event_type','dwell_seconds']}
        event['event_id']=x.get('event_id') or str(uuid5(NAMESPACE_URL,source_id+':'+str(x['id'])))
        result.append((decode_event(json.dumps(event)),timestamp.astimezone(timezone.utc)))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--source-id',required=True);p.add_argument('--apply',action='store_true');args=p.parse_args()
    rows=read_rows(args.source,args.source_id) # Validate all rows before any writes.
    if args.apply:
        store=Store()
        for event,timestamp in rows:store.accept(event,created_at=timestamp)
    print('Imported' if args.apply else 'Validated dry run:',len(rows))
if __name__=='__main__':main()
