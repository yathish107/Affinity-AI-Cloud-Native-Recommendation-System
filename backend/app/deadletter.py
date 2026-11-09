"""Operator-only inspection/replay; credentials come from DATABASE_URL."""
import argparse,json
from .storage import Store

def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=50);p.add_argument('--offset',type=int,default=0);p.add_argument('--replay',nargs=3,metavar=('TOPIC','PARTITION','OFFSET'));p.add_argument('--confirm',action='store_true');a=p.parse_args();s=Store()
    if a.replay:
        if not a.confirm:p.error('Explicit --confirm required after inspecting the record')
        topic,partition,offset=a.replay
        print(json.dumps({'new_effect':s.replay_dead_letter(topic,int(partition),int(offset))}))
    else:print(json.dumps(s.inspect_dead_letters(a.limit,a.offset),default=str,indent=2))
if __name__=='__main__':main()
