"""Run separately: python -m app.worker relay|consumer. At-least-once delivery."""
import json,logging,os,sys,time
from .storage import Store, Conflict
from kafka import TopicPartition, OffsetAndMetadata
from .envelope import decode_event
from .worker_metrics import measured,retries,quarantined,backlog
from prometheus_client import start_http_server

@measured("relay")
def relay_once(store,producer):
    row=store.claim()
    if row is None:return False
    try:
        producer.send('user-events',key=row['payload']['user_id'].encode(),value=row['payload']).get(timeout=10)
    except Exception as exc:
        store.finish(row,str(exc)[:1000]);raise
    store.finish(row)
    return True

@measured("consumer")
def consume_once(store,consumer,message):
    raw=message.value
    try:
        payload=decode_event(raw)
    except (ValueError, TypeError, UnicodeError) as exc:
        store.quarantine(message,raw,exc);quarantined.inc()
    else:
        try: store.apply(payload)
        except Conflict as exc: store.quarantine(message,raw,exc);quarantined.inc()
    consumer.commit({TopicPartition(message.topic,message.partition):OffsetAndMetadata(message.offset+1,'')})


def main():
    from kafka import KafkaProducer,KafkaConsumer
    logging.basicConfig(level=logging.INFO)
    store=Store()
    start_http_server(int(os.getenv("WORKER_METRICS_PORT","9101")))
    while True:
        client=None
        try:
            if sys.argv[1]=='relay':
                client=KafkaProducer(bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP','broker:9092'),value_serializer=lambda x:json.dumps(x).encode(),acks='all',max_block_ms=10000)
                while True:
                    backlog.set(store.pending_count())
                    if not relay_once(store,client):time.sleep(.5)
            else:
                client=KafkaConsumer('user-events',bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP','broker:9092'),group_id='signals-v1',enable_auto_commit=False,auto_offset_reset='earliest',max_poll_records=1)
                for message in client:consume_once(store,client,message)
        except KeyboardInterrupt:break
        except Exception:retries.labels(sys.argv[1]).inc();logging.exception('Worker failure; retrying without advancing failed offset');time.sleep(2)
        finally:
            if client is not None:
                try:client.close()
                except Exception:logging.exception('Client close failed')
if __name__=='__main__':main()
