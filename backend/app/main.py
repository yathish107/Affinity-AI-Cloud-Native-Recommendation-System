import json
from uuid import UUID, uuid4
import math
from typing import Literal
from pydantic import field_validator
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DB_PATH = os.getenv("DB_PATH", "/tmp/recommendations.db")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = "user-events"

PRODUCTS = [
    {"id":"p1","name":"Gaming Laptop","category":"electronics","price":74999,"tags":"gaming laptop computer gpu performance electronics"},
    {"id":"p2","name":"Wireless Headphones","category":"electronics","price":4999,"tags":"audio headphones wireless music electronics"},
    {"id":"p3","name":"Mechanical Keyboard","category":"electronics","price":3499,"tags":"gaming keyboard mechanical computer electronics"},
    {"id":"p4","name":"Smartphone","category":"electronics","price":29999,"tags":"phone smartphone android electronics mobile"},
    {"id":"p5","name":"Running Shoes","category":"fitness","price":3999,"tags":"running shoes fitness sports workout"},
    {"id":"p6","name":"Gym Backpack","category":"fitness","price":1899,"tags":"gym backpack fitness sports travel"},
    {"id":"p7","name":"Protein Shaker","category":"fitness","price":799,"tags":"protein shaker gym fitness workout"},
    {"id":"p8","name":"Dumbbell Set","category":"fitness","price":5999,"tags":"dumbbell strength gym fitness workout"},
    {"id":"p9","name":"Desk Lamp","category":"home","price":1299,"tags":"desk lamp office study home lighting"},
    {"id":"p10","name":"Office Chair","category":"home","price":8999,"tags":"office chair desk work home furniture"},
    {"id":"p11","name":"Coffee Maker","category":"home","price":4999,"tags":"coffee maker kitchen home beverage"},
    {"id":"p12","name":"Travel Backpack","category":"travel","price":2999,"tags":"travel backpack luggage outdoor journey"},
]

EVENT_WEIGHT = {"view": 1.0, "click": 2.0, "purchase": 5.0}

app = FastAPI(title="AI Cloud-Native Recommendation API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    @field_validator("user_id")
    @classmethod
    def clean_user(cls, value):
        value = value.strip()
        if not value: raise ValueError("user_id must not be blank")
        return value

    user_id: str = Field(min_length=1, max_length=100)
    product_id: str
    event_type: Literal["view", "click", "purchase"]
    dwell_seconds: float = Field(default=0, ge=0, le=36000)

class RecommendationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform([p["tags"] for p in PRODUCTS])
        self.index = {p["id"]: i for i, p in enumerate(PRODUCTS)}

    def recommend(self, events, limit=5, popularity=None):
        scores = {p["id"]: 0.0 for p in PRODUCTS}
        interacted = set()
        for e in sorted(events, key=lambda e: (e["product_id"], e["event_type"], float(e.get("dwell_seconds", 0)))):
            pid = e["product_id"]
            if pid not in scores: continue
            interacted.add(pid)
            weight = EVENT_WEIGHT.get(e["event_type"], 0.5)
            weight *= (1.0 + min(float(e.get("dwell_seconds", 0)), 120) / 240.0)
            scores[pid] += weight
        # Content-based personalization: similar products receive score from the user's profile.
        base_scores = scores.copy()
        for pid in sorted(interacted):
            base = base_scores[pid]
            sims = cosine_similarity(self.matrix[self.index[pid]], self.matrix).flatten()
            for product in PRODUCTS:
                scores[product["id"]] += base * float(sims[self.index[product["id"]]]) * 0.65
        # Small popularity prior prevents a weak/new profile from returning arbitrary items.
        for p in PRODUCTS:
            scores[p["id"]] += 0.01 * (popularity or {}).get(p["id"], 0)
        ranked = sorted(PRODUCTS, key=lambda p: (-scores[p["id"]], p["id"]))
        return [{**p, "score": round(scores[p["id"]], 4)} for p in ranked if p["id"] not in interacted][:limit]

engine = RecommendationEngine()

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, product_id TEXT, event_type TEXT, dwell_seconds REAL, created_at TEXT)")
    columns = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
    if "event_id" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN event_id TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS events_identity ON events(event_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS events_user ON events(user_id,id)")
    conn.commit()
    return conn

USE_POSTGRES = bool(os.getenv("DATABASE_URL"))
if not USE_POSTGRES and os.getenv("ALLOW_LEGACY_SQLITE") != "1":
    raise RuntimeError("DATABASE_URL is required; SQLite is only an explicit legacy test mode")
if USE_POSTGRES:
    from .storage import Store, Conflict
    from .cache import Cache
    store, cache = Store(), Cache()
DB = None if USE_POSTGRES else db()
DB_LOCK = threading.Lock()

def save_event(event: Event):
    if event.product_id not in {p["id"] for p in PRODUCTS}: raise HTTPException(404, "Unknown product")
    if event.event_type not in EVENT_WEIGHT: raise HTTPException(400, "event_type must be view, click or purchase")
    with DB_LOCK:
        old = DB.execute("SELECT user_id,product_id,event_type,dwell_seconds FROM events WHERE event_id=?", (str(event.event_id),)).fetchone()
        payload = (event.user_id,event.product_id,event.event_type,event.dwell_seconds)
        if old is not None:
            if tuple(old) != payload: raise HTTPException(409, "Event ID already used for different payload")
            return
        DB.execute("INSERT INTO events(event_id,user_id,product_id,event_type,dwell_seconds,created_at) VALUES(?,?,?,?,?,?)", (str(event.event_id),*payload,datetime.now(timezone.utc).isoformat()))
        DB.commit()

def get_events(user_id):
    if USE_POSTGRES: return store.history(user_id)
    with DB_LOCK:
        rows = DB.execute("SELECT product_id,event_type,dwell_seconds,created_at FROM events WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    return [{"product_id":r[0],"event_type":r[1],"dwell_seconds":r[2],"created_at":r[3]} for r in rows]

def kafka_worker():
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP, value_deserializer=lambda x: json.loads(x.decode()), group_id="recommendation-worker", auto_offset_reset="earliest")
        for msg in consumer:
            try: save_event(Event(**msg.value))
            except Exception: pass
    except Exception:
        pass

@app.on_event("startup")
def startup():
    if not USE_POSTGRES: threading.Thread(target=kafka_worker, daemon=True).start()

@app.get("/health")
def health():
    return {"status":"ok","service":"recommendation-api","timestamp":datetime.now(timezone.utc).isoformat()}

@app.get("/products")
def products(): return PRODUCTS

@app.get("/events/{user_id}")
def events(user_id: str): return get_events(user_id)

@app.get("/recommendations/{user_id}")
def recommendations(user_id: str, limit: int = 50):
    limit = max(1, min(limit, len(PRODUCTS)))
    if USE_POSTGRES:
        version, history, popularity = store.snapshot(user_id)
        key = cache.key(user_id, limit, version)
        result = cache.get(key)
        if result is None:
            result = {"user_id":user_id,"recommendations":engine.recommend(history,limit,popularity)}
            cache.put(key,result)
        return result
    with DB_LOCK:
        popularity = dict(DB.execute("SELECT product_id,COUNT(DISTINCT user_id) FROM events GROUP BY product_id"))
    return {"user_id":user_id,"recommendations":engine.recommend(get_events(user_id), limit, popularity)}

@app.post("/events")
def create_event(event: Event):
    if USE_POSTGRES:
        if event.product_id not in engine.index: raise HTTPException(404,"Unknown product")
        try: store.accept(event.model_dump(mode="json"))
        except Conflict as exc: raise HTTPException(409,str(exc))
        return {"message":"event accepted","event":event.model_dump(mode="json"),"published_to_broker":False,"publication_status":"queued_or_previously_accepted"}
    save_event(event)
    # Also attempt to publish to Kafka for the event-driven architecture demo.
    published = False
    producer = None
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP, value_serializer=lambda x: json.dumps(x).encode())
        producer.send(TOPIC, event.model_dump(mode="json")).get(timeout=2)
        producer.flush(timeout=2)
        published = True
    except Exception:
        pass
    finally:
        if producer is not None:
            try: producer.close(timeout=2)
            except Exception: pass
    return {"message":"event accepted","event":event.model_dump(mode="json"),"published_to_broker":published}
