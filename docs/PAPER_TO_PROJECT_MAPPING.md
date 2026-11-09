# Mapping of the Three Supplied Papers to the Project

## Paper 1: Scalable Event-Driven Architecture for Machine Learning-Based Real-Time Personalization and Recommendation Systems
Project mapping:
- User interactions become events.
- Kafka-compatible Redpanda provides the event-broker layer.
- A consumer worker demonstrates asynchronous event processing.
- The recommendation engine updates recommendations from recent interaction history.
- Event storage supports replay-oriented processing.

## Paper 2: A Systematic Literature Review on AI-Driven Migration from Monolithic Architectures to Microservices
Project mapping:
- The application is decomposed into frontend, recommendation/API and broker services.
- Each component can be packaged and deployed independently.
- Kubernetes Services provide service discovery.
- Multiple backend replicas demonstrate horizontal decomposition/scaling.

## Paper 3: From Prototype to Platform: Cloud-Native AI at Scale
Project mapping:
- Docker packages the services.
- Kubernetes manifests provide orchestration.
- Backend replicas and HPA demonstrate elastic scaling concepts.
- The ML engine is isolated from the UI and broker, making the architecture cloud-native in structure.

## Important distinction
The numerical performance results reported in the research papers are literature results. They are not claimed as measured results of this student implementation.
