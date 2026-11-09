# API examples

## Health
GET `/health`

## Products
GET `/products`

## Record event
POST `/events`

```json
{
  "user_id": "student1",
  "product_id": "p1",
  "event_type": "click",
  "dwell_seconds": 10
}
```

## Recommendations
GET `/recommendations/student1?limit=5`

## User events
GET `/events/student1`
