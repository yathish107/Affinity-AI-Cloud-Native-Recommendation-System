"""PostgreSQL authoritative storage. Every mutating operation commits on return."""
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, DateTime, ForeignKey, select, update, func
from sqlalchemy.dialects.postgresql import JSONB, insert

metadata = MetaData()
events = Table('events',metadata,Column('event_id',String,primary_key=True),Column('user_id',String(100),nullable=False,index=True),Column('product_id',String,nullable=False),Column('event_type',String,nullable=False),Column('dwell_seconds',Float,nullable=False),Column('created_at',DateTime(timezone=True),nullable=False))
outbox = Table('outbox',metadata,Column('event_id',ForeignKey('events.event_id'),primary_key=True),Column('payload',JSONB,nullable=False),Column('published_at',DateTime(timezone=True)),Column('lease_token',String),Column('lease_until',DateTime(timezone=True)),Column('attempts',Integer,nullable=False,default=0),Column('available_at',DateTime(timezone=True),nullable=False),Column('last_error',String))
processed = Table('processed_events',metadata,Column('event_id',ForeignKey('events.event_id'),primary_key=True),Column('consumer',String,primary_key=True),Column('processed_at',DateTime(timezone=True),nullable=False))
signals = Table('user_item_signals',metadata,Column('user_id',String,primary_key=True),Column('product_id',String,primary_key=True),Column('weight',Float,nullable=False))
versions = Table('signal_versions',metadata,Column('id',Integer,primary_key=True),Column('version',Integer,nullable=False))

dead_letters = Table('dead_letters',metadata,Column('topic',String,primary_key=True),Column('partition',Integer,primary_key=True),Column('offset',Integer,primary_key=True),Column('raw_hex',String,nullable=False),Column('error',String,nullable=False),Column('created_at',DateTime(timezone=True),nullable=False))

def now():return datetime.now(timezone.utc)
class Conflict(ValueError):pass
class Store:
    def __init__(self,url=None):
        self.engine=create_engine(url or os.environ['DATABASE_URL'],pool_pre_ping=True)
        if self.engine.dialect.name!='postgresql':raise ValueError('PostgreSQL is required')
    def accept(self,payload,created_at=None):
        payload=dict(payload);payload['event_id']=str(payload['event_id'])
        with self.engine.begin() as c:
            result=c.execute(insert(events).values(**payload,created_at=created_at or now()).on_conflict_do_nothing().returning(events.c.event_id)).scalar()
            if result is None:
                old=c.execute(select(events).where(events.c.event_id==payload['event_id'])).mappings().one()
                if (created_at is not None and old['created_at'] != created_at) or any(old[k]!=v for k,v in payload.items()):raise Conflict('Event ID already used for different payload')
                return False
            c.execute(insert(outbox).values(event_id=result,payload=payload,attempts=0,available_at=now()))
            c.execute(update(versions).where(versions.c.id==1).values(version=versions.c.version+1))
        return True
    def history(self,user,limit=100,offset=0):
        with self.engine.connect() as c:
            return [dict(r) for r in c.execute(select(events).where(events.c.user_id==user).order_by(events.c.created_at.desc(),events.c.event_id).limit(min(max(limit,1),500)).offset(max(offset,0))).mappings()]
    def snapshot(self,user):
        with self.engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
            with c.begin():
                version=c.execute(select(versions.c.version).where(versions.c.id==1)).scalar_one()
                history=[dict(r) for r in c.execute(select(events).where(events.c.user_id==user).order_by(events.c.created_at.desc(),events.c.event_id).limit(500)).mappings()]
                popularity=dict(c.execute(select(events.c.product_id,func.count(func.distinct(events.c.user_id))).group_by(events.c.product_id)).all())
                return version,history,popularity
    def claim(self,seconds=30):
        token=str(uuid4())
        with self.engine.begin() as c:
            row=c.execute(select(outbox).where(outbox.c.published_at.is_(None),outbox.c.available_at<=func.now(),(outbox.c.lease_until.is_(None))|(outbox.c.lease_until<func.now())).order_by(outbox.c.available_at,outbox.c.event_id).with_for_update(skip_locked=True).limit(1)).mappings().first()
            if row is None:return None
            c.execute(update(outbox).where(outbox.c.event_id==row['event_id']).values(lease_token=token,lease_until=func.now()+timedelta(seconds=seconds),attempts=outbox.c.attempts+1))
            return {**dict(row),'lease_token':token}
    def finish(self,row,error=None):
        with self.engine.begin() as c:
            values={'lease_token':None,'lease_until':None,'last_error':error}
            if error is None:values['published_at']=now()
            else:values['available_at']=now()+timedelta(seconds=min(60,2**min(row['attempts'],6)))
            return c.execute(update(outbox).where(outbox.c.event_id==row['event_id'],outbox.c.lease_token==row['lease_token'],outbox.c.published_at.is_(None)).values(**values)).rowcount==1
    def apply(self,payload):
        with self.engine.begin() as c:
            canonical=c.execute(select(events).where(events.c.event_id==payload['event_id'])).mappings().first()
            if canonical is None:raise Conflict('Unknown canonical event')
            if any(canonical[k]!=payload[k] for k in ['user_id','product_id','event_type','dwell_seconds']):raise Conflict('Broker payload differs from canonical event')
            added=c.execute(insert(processed).values(event_id=payload['event_id'],consumer='signals-v1',processed_at=now()).on_conflict_do_nothing().returning(processed.c.event_id)).scalar()
            if added is None:return False
            weight={'view':1,'click':2,'purchase':5}[payload['event_type']]
            stmt=insert(signals).values(user_id=payload['user_id'],product_id=payload['product_id'],weight=weight)
            c.execute(stmt.on_conflict_do_update(index_elements=['user_id','product_id'],set_={'weight':signals.c.weight+weight}))
            c.execute(update(versions).where(versions.c.id==1).values(version=versions.c.version+1))
        return True

    def quarantine(self,message,raw,error):
        with self.engine.begin() as c:
            c.execute(insert(dead_letters).values(topic=message.topic,partition=message.partition,offset=message.offset,raw_hex=raw.hex(),error=str(error)[:2000],created_at=now()).on_conflict_do_nothing())

    def model_snapshot(self,user):
        with self.engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
            with c.begin():
                v=c.execute(select(versions.c.version).where(versions.c.id==1)).scalar_one()
                h=[dict(x) for x in c.execute(select(events).where(events.c.user_id==user).order_by(events.c.created_at.desc(),events.c.event_id).limit(500)).mappings()]
                s=[dict(x) for x in c.execute(select(signals).order_by(signals.c.user_id,signals.c.product_id).limit(12000)).mappings()]
                return v,h,s
    def analytics(self):
        with self.engine.connect() as c:
            counts={name:c.execute(select(func.count()).select_from(table)).scalar() for name,table in [('events',events),('processed',processed),('dead_letters',dead_letters)]}
            counts['pending']=c.execute(select(func.count()).select_from(outbox).where(outbox.c.published_at.is_(None))).scalar()
            counts['users']=c.execute(select(func.count(func.distinct(events.c.user_id)))).scalar()
            counts['types']=dict(c.execute(select(events.c.event_type,func.count()).group_by(events.c.event_type)).all())
            return counts

    def pending_count(self):
        with self.engine.connect() as c:return c.execute(select(func.count()).select_from(outbox).where(outbox.c.published_at.is_(None))).scalar()
    def inspect_dead_letters(self,limit=50,offset=0):
        with self.engine.connect() as c:return [dict(r) for r in c.execute(select(dead_letters).order_by(dead_letters.c.created_at.desc()).limit(min(max(limit,1),100)).offset(max(offset,0))).mappings()]
    def replay_dead_letter(self,topic,partition,offset):
        # Reapply only canonical validated payload; existing ledger guarantees no duplicate effect.
        from .envelope import decode_event
        with self.engine.connect() as c:
            row=c.execute(select(dead_letters).where(dead_letters.c.topic==topic,dead_letters.c.partition==partition,dead_letters.c.offset==offset)).mappings().one()
        payload=decode_event(bytes.fromhex(row['raw_hex']))
        return self.apply(payload)
