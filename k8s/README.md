# Kubernetes advanced deployment
All workloads now use PostgreSQL; no Pod-local SQLite is used. Requires a working cluster, default StorageClass, enough disk/RAM and Metrics Server for HPA. This configuration has not been deployed in the authoring environment.

Build and load backend/frontend v2 images into your cluster using its documented image-loading process:
```
docker build -t ai-recommender-backend:v2 ./backend
docker build -t ai-recommender-frontend:v2 ./frontend
kubectl create namespace ai-recommender
```
Create a local secret file (do not commit/share it) containing DATABASE_URL, POSTGRES_PASSWORD, ADMIN_KEY and GRAFANA_PASSWORD. DATABASE_URL must use postgresql+psycopg://recommend:<URL-encoded-password>@postgres:5432/recommend and match POSTGRES_PASSWORD.
```
kubectl create secret generic platform-secrets -n ai-recommender --from-env-file=k8s-secrets.env
kubectl apply -f k8s/platform.yaml
kubectl rollout status deployment/postgres -n ai-recommender
kubectl rollout status deployment/broker -n ai-recommender
kubectl apply -f k8s/jobs.yaml
kubectl wait --for=condition=complete job/migrate job/topics -n ai-recommender --timeout=180s
kubectl rollout status deployment/recommender -n ai-recommender
kubectl port-forward service/frontend 8080:80 -n ai-recommender
```
Inference/API readiness remains false until migrations exist. Workers retry dependencies. PVCs preserve PostgreSQL and broker state; do not delete the namespace/PVCs as a stop command. Single-node broker/PostgreSQL are demo deployments, not HA. Backend image uses service.py by default. HPA targets only recommendation inference.
Optional monitoring: `kubectl apply -f k8s/monitoring/optional.yaml`; port-forward grafana 3000:3000. Grafana dashboard ConfigMaps persist definitions; ad-hoc dashboard edits are ephemeral. Enable tracing by setting OTEL_EXPORTER_OTLP_ENDPOINT=http://otel:4318 on the API/inference Deployments.
