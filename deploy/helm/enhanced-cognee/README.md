# RNR Enhanced Cognee Helm Chart

Production-grade Kubernetes deployment for RNR Enhanced Cognee with all 4 storage tiers (PostgreSQL + Qdrant + Valkey + ArcadeDB) + the MCP HTTP server.

## What ships

- 1 Deployment (MCP HTTP server) + Service + optional Ingress
- 4 StatefulSets (postgres, qdrant, valkey, arcadedb) + headless Services
- ConfigMap for dynamic categories (`/etc/enhanced-cognee/categories.json`)
- Optional TLS Secret mount for HTTPS termination at the MCP server
- Optional API-key Secret reference for `X-API-Key` auth

All four DB tiers are toggleable via `deployments.<tier>.enabled` so you can run with external managed services (RDS / Aurora / Memorystore / GCP managed Postgres / etc.) by setting `storage.<tier>.host` and leaving the in-chart Deployment off.

## Quick start

```bash
helm install RNR-Enhanced-Cognee ./deploy/helm/enhanced-cognee \
  --namespace RNR-Enhanced-Cognee --create-namespace

# Wait for all 5 workloads ready
kubectl -n RNR-Enhanced-Cognee rollout status statefulset/enhanced-cognee-postgres
kubectl -n RNR-Enhanced-Cognee rollout status statefulset/enhanced-cognee-qdrant
kubectl -n RNR-Enhanced-Cognee rollout status statefulset/enhanced-cognee-valkey
kubectl -n RNR-Enhanced-Cognee rollout status statefulset/enhanced-cognee-arcadedb
kubectl -n RNR-Enhanced-Cognee rollout status deployment/enhanced-cognee-mcp

# Bootstrap the shared_memory schema (one-time)
kubectl -n RNR-Enhanced-Cognee exec -i statefulset/enhanced-cognee-postgres -- \
  psql -U cognee_user -d cognee_db < ../../docker/init-scripts/01-init-pgvector.sql

# Port-forward + test
kubectl -n RNR-Enhanced-Cognee port-forward svc/enhanced-cognee-mcp 8080:8080
curl http://localhost:8080/health
```

## Production-ready overrides

Save as `production-values.yaml`:

```yaml
image:
  repository: your.registry.example/enhanced-cognee
  tag: "1.0.0"

multiTenant:
  required: true            # refuse un-tenanted writes in production

security:
  apiKeySecretRef:
    name: enhanced-cognee-secrets
    key: api-key
  maxPayloadBytes: 2097152   # 2 MiB
  rateLimitPerMin:
    addMemory: 120
    searchMemories: 600

tls:
  enabled: true
  secretName: enhanced-cognee-tls    # issued by cert-manager

mcpServer:
  replicaCount: 3
  ingress:
    enabled: true
    className: nginx
    hosts:
      - host: cognee.example.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - hosts: [cognee.example.com]
        secretName: enhanced-cognee-tls
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

# Use a managed Postgres (RDS / Aurora) instead of in-chart:
deployments:
  postgres:
    enabled: false
storage:
  relational:
    host: my-postgres.cluster-xxx.us-east-1.rds.amazonaws.com
    passwordSecretRef:
      name: enhanced-cognee-secrets
      key: postgres-password

observability:
  otlpEndpoint: signoz-otel-collector.signoz.svc.cluster.local:4317
```

Install:

```bash
helm install RNR-Enhanced-Cognee ./deploy/helm/enhanced-cognee \
  --namespace RNR-Enhanced-Cognee --create-namespace \
  -f production-values.yaml
```

## Secrets setup

```bash
kubectl -n RNR-Enhanced-Cognee create secret generic enhanced-cognee-secrets \
  --from-literal=api-key="$(openssl rand -base64 32)" \
  --from-literal=postgres-password="$(openssl rand -base64 32)" \
  --from-literal=arcadedb-password="$(openssl rand -base64 32)"
```

For TLS, point cert-manager at the `enhanced-cognee-tls` Secret name in your Certificate resource.

## Notes per tier

- **PostgreSQL** uses the `pgvector/pgvector:pg18` image so the pgvector extension is preinstalled. The shared_memory schema is NOT auto-bootstrapped by the chart -- run the `psql -f docker/init-scripts/01-init-pgvector.sql` step once after the StatefulSet is ready.
- **ArcadeDB** uses the public `arcadedata/arcadedb:latest` image which does NOT ship the BoltPlugin JAR. Set `storage.graph.transport: http` (the chart's default). To use Bolt, mount a `lib/plugins/` volume containing the JAR.
- **Qdrant** uses `qdrant/qdrant:v1.12.0`. Probes hit `/livez` and `/readyz`.
- **Valkey** uses `valkey/valkey:8-alpine` with persistence enabled (`--appendonly yes`).

## Switching providers

To swap a tier:

```yaml
storage:
  graph:
    provider: neo4j          # was arcadedb
deployments:
  arcadedb:
    enabled: false           # turn off ArcadeDB StatefulSet
```

Then deploy Neo4j separately (or use the Bitnami chart) and set `storage.graph.host` to its Service DNS.

The 30 providers in [`docs/PROFILES.md`](../../docs/PROFILES.md) all work the same way -- flip `storage.<tier>.provider` + `storage.<tier>.host` and the MCP server's pluggable factory routes through the right adapter.

## Uninstall

```bash
helm uninstall RNR-Enhanced-Cognee --namespace RNR-Enhanced-Cognee

# PersistentVolumeClaims are NOT automatically deleted -- preserve or remove
# manually:
kubectl -n RNR-Enhanced-Cognee get pvc
kubectl -n RNR-Enhanced-Cognee delete pvc --all
```

## See also

- [Helm chart values reference](values.yaml)
- [`docs/PROFILES.md`](../../docs/PROFILES.md) -- per-profile adapter matrix
- [`docs/SECRETS_MANAGEMENT.md`](../../docs/SECRETS_MANAGEMENT.md) -- production secrets handling
- [`docs/PLUGGABLE_DB_BACKENDS.md`](../../docs/PLUGGABLE_DB_BACKENDS.md) -- provider factory architecture
