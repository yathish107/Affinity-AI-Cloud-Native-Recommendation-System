import hashlib,json,os
import redis
class Cache:
    def __init__(self,url=None):
        self.client=redis.Redis.from_url(url or os.getenv('REDIS_URL','redis://localhost:6379/0'),socket_connect_timeout=.2,socket_timeout=.2,decode_responses=True)
    def key(self,user,limit,version):return 'recommendations:content-v2:'+hashlib.sha256(user.encode()).hexdigest()+f':{limit}:{version}'
    def get(self,key):
        try:
            raw=self.client.get(key)
            return json.loads(raw) if raw else None
        except (redis.RedisError,ValueError):return None
    def put(self,key,value):
        try:self.client.set(key,json.dumps(value),ex=60)
        except redis.RedisError:pass
