# Project Report

## Title
AI-Powered Cloud-Native Real-Time Recommendation System

## Abstract
This project implements a lightweight real-time recommendation platform inspired by the three supplied research papers. User interactions are captured as events, sent through an event-driven broker, stored as an event log, and used by a machine-learning recommendation engine. The application is separated into frontend, backend/recommendation and broker components and can be deployed using Docker Compose or Kubernetes. A TF-IDF and cosine-similarity content model combines product similarity with weighted user interactions to provide personalized recommendations. The design demonstrates event-driven processing, service decoupling, containerization, horizontal replicas and autoscaling concepts on ordinary student hardware.

## Problem Statement
Traditional recommendation demos often process data in batches and are difficult to demonstrate as scalable cloud-native systems. The objective is to create a small but runnable architecture where user activity becomes an event, the event can be processed asynchronously, and recommendations change according to the user's behavior.

## Objectives
- Capture real-time user events such as view, click and purchase.
- Demonstrate event-driven communication with Kafka-compatible Redpanda.
- Generate personalized recommendations using a lightweight ML model.
- Separate the application into deployable services.
- Demonstrate Docker containerization and Kubernetes scaling.
- Provide an easy web interface for demonstration.

## Methodology
1. Frontend displays products and records user actions.
2. FastAPI validates incoming events.
3. Events are stored in SQLite and attempted to be published to Redpanda.
4. A Kafka consumer can process broker events asynchronously.
5. RecommendationEngine converts product tags to TF-IDF vectors.
6. Cosine similarity finds related products.
7. Interaction weights emphasize purchase > click > view.
8. Docker Compose runs the services together.
9. Kubernetes manifests demonstrate replicas and HPA.

## ML Approach
The prototype uses content-based recommendation. Product descriptions are represented with TF-IDF vectors. For every product interacted with by a user, cosine similarity contributes a score to other products. Event weights are view=1, click=2 and purchase=5. Dwell time slightly increases the event contribution. This is intentionally lightweight and explainable for an academic demonstration.

## Microservice/Cloud-Native Mapping
- Frontend: independent presentation service.
- Recommendation API: independent application service.
- Broker: independent event infrastructure.
- Docker: repeatable packaging.
- Kubernetes: replicas, service discovery and HPA.
- Event log: supports replay-oriented event processing.

## Testing
### Functional tests
- Health endpoint returns status OK.
- Product catalog loads.
- View/click/purchase events are accepted.
- User events are retrievable.
- Recommendations change after interactions.
- Different users can have different profiles.

### Architecture tests
- Broker can be used for event publication.
- API remains usable in local fallback mode if Kafka is unavailable.
- Docker Compose starts the application as separate services.
- Kubernetes manifests define replicas and autoscaling.

## Expected Demonstration Result
If a user repeatedly interacts with electronics products, related electronics products receive higher recommendation scores. If another user interacts with fitness products, fitness-related products receive higher scores. This demonstrates personalization without requiring a large training dataset or GPU.

## Limitations
This is an academic prototype. SQLite is not a distributed database, the recommendation model is not a deep-learning recommender, and performance measurements from the supplied papers should not be presented as measurements of this implementation. Production systems would use a shared database, authentication, observability, durable schema/versioning and a stronger recommendation model.

## Future Scope
- Replace TF-IDF with collaborative filtering or neural embeddings.
- Add PostgreSQL/MongoDB.
- Add Redis caching.
- Add Prometheus/Grafana monitoring.
- Add model training pipeline and A/B testing.
- Add user authentication and an admin dashboard.
