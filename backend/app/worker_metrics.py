from prometheus_client import Counter,Histogram,Gauge
processed=Counter('worker_events_total','Completed worker operations',['role'])
failures=Counter('worker_failures_total','Failed operations',['role'])
retries=Counter('worker_retries_total','Reconnect retries',['role'])
quarantined=Counter('worker_quarantined_total','Durably quarantined deliveries')
duration=Histogram('worker_processing_seconds','Processing duration',['role'])
backlog=Gauge('worker_outbox_backlog','Pending unpublished canonical events')

def measured(role):
    def decorate(fn):
        def wrapped(*args,**kwargs):
            with duration.labels(role).time():
                try:
                    result=fn(*args,**kwargs)
                    if result is not False:processed.labels(role).inc()
                    return result
                except Exception:failures.labels(role).inc();raise
        return wrapped
    return decorate
