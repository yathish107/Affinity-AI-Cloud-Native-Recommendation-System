import json,math
from uuid import UUID

def decode_event(raw):
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError('Expected object')
    required={'event_id','user_id','product_id','event_type','dwell_seconds'}
    if set(value)!=required:raise ValueError('Unsupported envelope fields')
    if not isinstance(value['event_id'],str):raise ValueError('Invalid event ID')
    value['event_id']=str(UUID(value['event_id']))
    if not isinstance(value['user_id'],str) or not value['user_id'].strip() or len(value['user_id'])>100:raise ValueError('Invalid user')
    if value['product_id'] not in {f'p{i}' for i in range(1,13)}:raise ValueError('Invalid product')
    if value['event_type'] not in {'view','click','purchase'}:raise ValueError('Invalid type')
    dwell=value['dwell_seconds']
    if isinstance(dwell,bool) or not isinstance(dwell,(float,int)) or not math.isfinite(dwell) or not 0<=dwell<=36000:raise ValueError('Invalid dwell')
    return value
