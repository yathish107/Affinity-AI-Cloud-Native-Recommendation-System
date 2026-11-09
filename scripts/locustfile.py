import uuid
from locust import HttpUser,task,between
class Shopper(HttpUser):
    wait_time=between(.3,1.5)
    def on_start(self):self.user='load-'+str(uuid.uuid4())
    @task(3)
    def catalog(self):self.client.get('/api/products')
    @task(4)
    def recommend(self):self.client.get('/api/recommendations/'+self.user,name='/api/recommendations/[user]')
    @task
    def event(self):self.client.post('/api/events',json={'event_id':str(uuid.uuid4()),'user_id':self.user,'product_id':'p1','event_type':'click','dwell_seconds':0})
