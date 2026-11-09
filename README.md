# Affinity – AI Cloud-Native Recommendation System

## Project Overview

Affinity is an AI-powered, cloud-native recommendation system that provides personalized product recommendations based on user interactions and preferences.

The project uses a hybrid recommendation approach that combines Content-Based Filtering, Collaborative Filtering, and Popularity-Based Recommendations to generate relevant suggestions.

It follows a microservices-based architecture and uses Docker containers, PostgreSQL, Redis, and Redpanda for scalable data processing and storage.

## Key Features

- **Personalized Recommendations:** Generates recommendations based on user interaction history.
- **Hybrid Recommendation Engine:** Combines multiple recommendation techniques.
- **Content-Based Filtering:** Uses product features and similarity to recommend relevant items.
- **Collaborative Filtering:** Uses interaction patterns to identify relevant recommendations.
- **Popularity-Based Recommendations:** Uses popular items as an additional recommendation signal.
- **Event-Driven Architecture:** Processes user interactions through an event pipeline.
- **Caching:** Uses Redis to improve recommendation response times.
- **Database Storage:** Uses PostgreSQL to store user interactions and related information.
- **Microservices Architecture:** Separates application responsibilities into independent services.
- **Containerization:** Uses Docker and Docker Compose to run the application.

## Technology Stack

| Category | Technologies |
|---|---|
| Frontend | HTML, CSS, JavaScript, Nginx |
| Backend | Python, FastAPI |
| Machine Learning | Scikit-learn, TF-IDF, Cosine Similarity |
| Database | PostgreSQL |
| Caching | Redis |
| Messaging | Redpanda |
| Containerization | Docker, Docker Compose |
| Monitoring | Prometheus, Grafana |
| API Documentation | FastAPI Swagger UI |

## System Architecture

The project follows a microservices-based architecture.

Main components:

1. **Frontend Service:** Provides the user interface for interacting with the recommendation system.
2. **API Gateway:** Receives frontend requests and forwards them to the appropriate backend service.
3. **Recommendation Service:** Generates personalized recommendations using the hybrid recommendation algorithm.
4. **PostgreSQL:** Stores user interactions, event records, and recommendation-related signals.
5. **Redis:** Caches recommendation results to improve performance.
6. **Redpanda:** Handles event messaging and asynchronous processing.
7. **Relay Service:** Publishes pending events to the messaging system.
8. **Consumer Service:** Processes user interaction events and updates recommendation signals.
9. **Prometheus and Grafana:** Provide monitoring and visualization when the optional monitoring services are enabled.

## Recommendation Techniques

### 1. Content-Based Filtering
Recommends products based on their features and similarity to products the user has interacted with.

### 2. Collaborative Filtering
Uses user-item interaction patterns to identify products that may interest a user.

### 3. Popularity-Based Recommendation
Uses popular products as an additional recommendation signal.

### 4. Hybrid Recommendation
Combines the available recommendation signals to produce the final recommendation list.

## Project Workflow

1. The user opens the frontend application.
2. The user interacts with available products.
3. User interactions are sent to the backend through the API Gateway.
4. Events are stored in PostgreSQL.
5. Redpanda handles asynchronous event messaging.
6. The consumer processes events and updates user-item interaction signals.
7. The recommendation service uses the available signals to generate recommendations.
8. Redis caches recommendation results.
9. Personalized recommendations are displayed on the frontend.

## Prerequisites

Install the following before running the project:

- Docker Desktop
- Docker Compose
- Git
- Visual Studio Code (recommended)

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Affinity-AI-Cloud-Native-Recommendation-System.git
```

### 2. Navigate to the project directory

```bash
cd Affinity-AI-Cloud-Native-Recommendation-System
```

### 3. Start the application

```bash
docker compose up --build -d
```

### 4. Access the application

| Component | URL |
|---|---|
| Frontend | http://localhost:8081 |
| API Documentation | http://localhost:8000/docs |
| Prometheus (if enabled) | http://localhost:9090 |
| Grafana (if enabled) | http://localhost:3000 |

### 5. Stop the application

```bash
docker compose down
```

## API Documentation

FastAPI provides interactive API documentation through Swagger UI.

Open:

http://localhost:8000/docs

You can explore and test the available API endpoints through this interface.

## Project Structure

```text
Affinity/
│
├── backend/
│   └── app/
│       ├── service.py
│       ├── hybrid.py
│       ├── storage.py
│       ├── worker.py
│       ├── cache.py
│       └── catalog.json
│
├── frontend/
│   ├── app.js
│   ├── index.html
│   ├── style.css
│   ├── nginx.conf
│   └── Dockerfile
│
├── docs/
│
├── k8s/
│
├── docker-compose.yml
├── README.md
└── .gitignore
```

## Future Enhancements

- Integration with larger real-world product datasets.
- Improved recommendation accuracy using more user interaction data.
- Advanced machine learning recommendation models.
- Enhanced monitoring and analytics.
- Kubernetes-based deployment and scaling.
- Improved personalization based on user preferences.

## Project Objective

The main objective of Affinity is to develop an intelligent, scalable, and modular recommendation platform that combines machine learning techniques with cloud-native technologies to deliver personalized recommendations.

## License

This project is developed for academic and educational purposes.
