# AWS Deployment Architecture

Phase 18 documents a future deployment path only. Nothing in this document deploys resources, creates credentials, or enables public access.

## Target Architecture

```text
Internet
  |
HTTPS / DNS
  |
Application Load Balancer
  |
Private subnets
  |
EC2 instance running Docker Compose
  |
Sushant Neural Twin backend container
```

## Initial AWS Shape

- **VPC:** Dedicated network with public and private subnets across at least two availability zones.
- **Load balancer:** Public Application Load Balancer terminating HTTPS and forwarding to the backend.
- **Compute:** A private EC2 instance running the already validated backend container.
- **Access:** Security groups allow HTTPS to the load balancer and only the required application port from the load balancer to the instance.
- **Secrets:** Store `AUTH_TOKEN` and future secrets in AWS Secrets Manager or Systems Manager Parameter Store. Never place them in Git, images, or Compose files.
- **TLS:** Use an AWS Certificate Manager certificate at the load balancer.
- **Storage:** Keep personal knowledge data private and encrypted. Select durable storage only after the local data and database contracts are finalized.
- **Backups:** Define encrypted, tested backups before storing real personal data in AWS.

## Deployment Prerequisites

1. Local Docker image and Compose smoke tests pass.
2. Authentication is enabled with a managed secret.
3. CORS origins are restricted to the real frontend domains.
4. Health and readiness behavior is defined.
5. Personal-data retention, backup, and deletion policies are documented.
6. Logs are reviewed to ensure prompts, tokens, and personal data are not emitted.
7. A rollback image tag and recovery procedure exist.

## Planned Release Sequence

1. Build and scan an immutable backend image in CI.
2. Push the image to a private Amazon ECR repository.
3. Provision the VPC, security groups, load balancer, and private compute through reviewed infrastructure code.
4. Inject secrets at runtime through an AWS-managed secret store.
5. Run database and data migrations only after a reviewed data model exists.
6. Deploy to a non-production environment and run health, API, security, and evaluation checks.
7. Promote a tested image to production with a rollback path.

## Explicit Non-Goals

- No AWS resources are provisioned by this repository.
- No AWS credentials are required or stored.
- No automatic deployment workflow is enabled.
- No public endpoint is configured.
- No database, PostgreSQL service, or production reverse proxy is added yet.
- No personal data is uploaded.
