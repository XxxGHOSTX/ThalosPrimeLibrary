<!-- PROPRIETARY AND CONFIDENTIAL -->
<!-- Copyright © 2026 Tony Ray Macier III. All Rights Reserved. -->

# Infrastructure

**Owner:** Tony Ray Macier III

## Deployment Steps

1. **Docker Compose (local/dev)**
   ```bash
   cd infrastructure
   docker-compose up --build
   ```

2. **Kubernetes (production)**
   ```bash
   kubectl apply -f kubernetes/
   ```

## Rollback Strategy
```bash
kubectl rollout undo deployment/thalos-core
```

## CI Integration
- Docker images are built in `ci.yml` on every push to `main`
- Kubernetes manifests are applied via CD after image push
