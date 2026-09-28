# Deployment Guide - AI CEO Panel MVP

## Overview

This guide covers deploying the AI CEO Panel MVP to production. We'll cover multiple deployment strategies for different hosting preferences.

## Pre-Deployment Checklist

- [ ] All environment variables configured
- [ ] Database migrations tested locally
- [ ] Docker images build successfully
- [ ] All tests pass (`pytest` in backend, `npm test` in frontend)
- [ ] CORS settings configured for production domain
- [ ] SSL certificate provisioned
- [ ] DNS records prepared
- [ ] API rate limits configured

## Option 0: Render (Backend) + Vercel (Frontend) — Recommended

This is the fastest path to a production deployment and matches the `render.yaml` Blueprint checked into the repo root.

### Backend on Render

1. **Push this repo to GitHub** (already done if you're reading this from the repo).

2. **Create the Blueprint**
   - In the Render dashboard: **New → Blueprint**.
   - Select this repository. Render reads `render.yaml` from the repo root and proposes:
     - `ai-ceo-panel-db` — a managed PostgreSQL instance (pgvector is supported natively; the `001_initial_postgres_schema` migration runs `CREATE EXTENSION IF NOT EXISTS vector`).
     - `ai-ceo-panel-backend` — a Python web service with `rootDir: backend`, `buildCommand: pip install -r requirements.txt`, and `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   - Click **Apply** to provision both.

3. **Fill in the secret env vars** Render leaves blank (marked `sync: false` in `render.yaml`) on the `ai-ceo-panel-backend` service:
   - `GEMINI_API_KEY`
   - `NVIDIA_API_KEY`
   - `CLERK_ISSUER` (e.g. `https://your-instance.clerk.accounts.dev`)
   - `CLERK_JWKS_URL` (e.g. `https://your-instance.clerk.accounts.dev/.well-known/jwks.json`)
   - `CLERK_AUDIENCE` (if your Clerk instance requires one)
   - `BACKEND_CORS_ORIGINS` — set this **after** the Vercel deploy below, to your Vercel URL, e.g. `https://your-app.vercel.app` (comma-separate multiple origins)

   `DATABASE_URL` is wired automatically from the `ai-ceo-panel-db` database via `fromDatabase`; `app/core/config.py` accepts either that single connection string or the discrete `POSTGRES_*` vars.

4. **Deploy and verify**
   - Render builds and starts the service. On boot, the app's lifespan hook runs `alembic upgrade head` against the managed Postgres instance automatically — no manual migration step needed.
   - Confirm health: `curl https://ai-ceo-panel-backend.onrender.com/healthcheck` → `{"status": "ok"}`.
   - Note the service URL; you'll need it for the frontend's `NEXT_PUBLIC_API_BASE_URL`.

### Frontend on Vercel

1. **Import the project**
   - In the Vercel dashboard: **Add New → Project**, select this repository.
   - Set **Root Directory** to `frontend` (this is a monorepo; Vercel auto-detects the Next.js framework once the root is set).

2. **Set environment variables** (Project Settings → Environment Variables):
   - `NEXT_PUBLIC_API_BASE_URL` = `https://<your-render-service>.onrender.com/api/v1`
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` = your Clerk publishable key
   - `CLERK_SECRET_KEY` = your Clerk secret key

3. **Deploy**. Vercel builds with `npm run build` and serves via `next start` automatically.

4. **Close the loop on CORS**: once you have the Vercel URL (e.g. `https://your-app.vercel.app`), go back to the Render service and set `BACKEND_CORS_ORIGINS` to that URL, then redeploy the backend so `CORSMiddleware` allows requests from the frontend.

5. **Custom domains** (optional): add your domain in Vercel for the frontend and in Render for the backend, then update `NEXT_PUBLIC_API_BASE_URL` and `BACKEND_CORS_ORIGINS` to match.

### Notes

- Render's free/starter Postgres plans sleep or have connection limits — use a paid plan for anything beyond testing.
- The web service on Render's free tier spins down on idle, which adds cold-start latency; upgrade the plan in `render.yaml` (`plan: starter` → a paid plan) for always-on behavior.
- `AUTH_REQUIRED=true` and `DEV_MOCK_USER_ENABLED=false` are set by default in `render.yaml` — production traffic always goes through Clerk JWT validation.

## Option 1: Docker Compose + Cloud VM (Recommended for MVP)

### Prerequisites
- Docker & Docker Compose installed
- PostgreSQL 14+ (hosted on Neon, AWS RDS, or local)
- Server with 2GB+ RAM

### Steps

1. **Prepare environment files**
   ```bash
   # backend/.env.production
   DATABASE_URL=postgresql://user:pass@db.host:5432/ai_ceo_prod
   NVIDIA_API_KEY=xxx
   GOOGLE_GENAI_API_KEY=xxx
   CLERK_SECRET_KEY=xxx
   CLERK_WEBHOOK_SECRET=xxx
   ENVIRONMENT=production
   
   # frontend/.env.production.local
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=xxx
   NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com/api/v1
   CLERK_SECRET_KEY=xxx
   ```

2. **Build Docker images**
   ```bash
   docker build -t ai-ceo-backend:latest ./backend
   docker build -t ai-ceo-frontend:latest ./frontend
   ```

3. **Update docker-compose.yml for production**
   ```yaml
   version: '3.9'
   
   services:
     backend:
       image: ai-ceo-backend:latest
       environment:
         - DATABASE_URL=postgresql://user:pass@postgres:5432/ai_ceo_prod
         - ENVIRONMENT=production
         - NVIDIA_API_KEY=${NVIDIA_API_KEY}
         - GOOGLE_GENAI_API_KEY=${GOOGLE_GENAI_API_KEY}
       ports:
         - "8000:8000"
       depends_on:
         - postgres
       restart: always
       command: uvicorn app.main:app --host 0.0.0.0 --port 8000
   
     frontend:
       image: ai-ceo-frontend:latest
       environment:
         - NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com/api/v1
         - NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
       ports:
         - "3000:3000"
       depends_on:
         - backend
       restart: always
   
     postgres:
       image: postgres:14-alpine
       environment:
         - POSTGRES_DB=ai_ceo_prod
         - POSTGRES_USER=postgres
         - POSTGRES_PASSWORD=${DB_PASSWORD}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       restart: always
   
   volumes:
     postgres_data:
   ```

4. **Run migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Start services**
   ```bash
   docker-compose up -d
   ```

6. **Configure reverse proxy (Nginx)**
   ```nginx
   upstream api_backend {
       server backend:8000;
   }
   
   upstream frontend_app {
       server frontend:3000;
   }
   
   server {
       listen 80;
       server_name yourdomain.com;
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;
       
       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
       
       # API proxy
       location /api/v1 {
           proxy_pass http://api_backend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       # Frontend
       location / {
           proxy_pass http://frontend_app;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

## Option 2: Heroku Deployment

### Backend Deployment

1. **Create Procfile** (backend/Procfile)
   ```
   release: alembic upgrade head
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

2. **Create Heroku app and add PostgreSQL**
   ```bash
   heroku create ai-ceo-api
   heroku addons:create heroku-postgresql:standard-0 -a ai-ceo-api
   ```

3. **Set environment variables**
   ```bash
   heroku config:set NVIDIA_API_KEY=xxx -a ai-ceo-api
   heroku config:set GOOGLE_GENAI_API_KEY=xxx -a ai-ceo-api
   heroku config:set CLERK_SECRET_KEY=xxx -a ai-ceo-api
   ```

4. **Deploy**
   ```bash
   cd backend
   git subtree push --prefix backend heroku main
   ```

### Frontend Deployment (Vercel)

1. **Create Vercel project**
   ```bash
   cd frontend
   vercel
   ```

2. **Set environment variables in Vercel dashboard**
   - `NEXT_PUBLIC_API_BASE_URL=https://ai-ceo-api.herokuapp.com/api/v1`
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=xxx`
   - `CLERK_SECRET_KEY=xxx`

3. **Configure custom domain**
   - Point DNS to Vercel
   - Update `NEXT_PUBLIC_API_BASE_URL` in environment

## Option 3: AWS Deployment

### Backend (ECS + RDS)

1. **Create RDS Postgres instance**
   ```bash
   aws rds create-db-instance \
     --db-instance-identifier ai-ceo-prod \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --allocated-storage 20
   ```

2. **Push image to ECR**
   ```bash
   aws ecr create-repository --repository-name ai-ceo-backend
   aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   docker tag ai-ceo-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/ai-ceo-backend:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/ai-ceo-backend:latest
   ```

3. **Create ECS cluster and service**
   - Use AWS Console or Terraform to create ECS service
   - Configure CloudWatch logs, auto-scaling

### Frontend (S3 + CloudFront)

1. **Build Next.js for static export** (if possible, otherwise use ECS)
   ```bash
   npm run build
   npm run export
   ```

2. **Upload to S3**
   ```bash
   aws s3 sync out/ s3://ai-ceo-frontend-prod/
   ```

3. **Create CloudFront distribution**
   - Origin: S3 bucket
   - Enable caching
   - Custom domain with ACM certificate

## Post-Deployment

### Health Checks

1. **Backend health**
   ```bash
   curl https://api.yourdomain.com/healthcheck
   ```

2. **Frontend load**
   ```bash
   curl https://yourdomain.com
   ```

3. **Database connectivity**
   ```bash
   # The backend fails to start (and therefore fails its health check) if it
   # cannot run migrations against the database, so a passing /healthcheck
   # implies DB connectivity.
   curl https://api.yourdomain.com/healthcheck
   ```

### Monitoring

Set up monitoring for:
- **Backend**: CPU, memory, request latency, error rates
- **Database**: Connection pool, query performance, disk usage
- **Frontend**: Page load times, JavaScript errors
- **API**: Rate limits, auth failures

#### CloudWatch (AWS)
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name api-high-error-rate \
  --alarm-description "Alert if API error rate > 5%" \
  --metric-name ErrorRate \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

#### Sentry (Error Tracking)
Add to backend:
```python
import sentry_sdk
sentry_sdk.init("YOUR_SENTRY_DSN", traces_sample_rate=1.0)
```

### Logging

Configure centralized logging:
- **Datadog**: `pip install datadog python-json-logger`
- **LogRocket**: Add to frontend for session replay
- **ELK Stack**: Self-hosted logs + Elasticsearch + Kibana

## Scaling Considerations

### Database
- Use read replicas for scaled read workloads
- Enable connection pooling (pgBouncer)
- Regular backups (daily minimum)
- Point-in-time recovery enabled

### Backend
- Horizontal scaling via ECS auto-scaling or Kubernetes
- Load balancing with ALB or Nginx
- Cache frequently accessed data (Redis)
- Async job processing for long-running tasks (Celery + RabbitMQ)

### Frontend
- CDN caching (CloudFront, Cloudflare)
- Image optimization
- Code splitting
- Service workers for offline support

## Rollback Procedure

1. **Identify failing deployment**
   ```bash
   # Check logs for errors
   docker logs -f <container-id>
   ```

2. **Rollback backend** (Docker Compose)
   ```bash
   docker-compose down
   docker pull ai-ceo-backend:previous-tag
   docker-compose up -d
   alembic downgrade -1  # If needed
   ```

3. **Rollback frontend** (Vercel)
   - Go to Deployment settings
   - Select previous stable deployment
   - Click "Promote to Production"

## Database Backup & Recovery

### Automated Backups
```bash
# Using pg_dump
pg_dump postgresql://user:pass@host/ai_ceo_prod > backup.sql

# Restore
psql postgresql://user:pass@host/ai_ceo_prod < backup.sql

# Using S3 (AWS)
aws s3 cp backup.sql s3://ai-ceo-backups/
```

### Recovery Steps
1. Restore database from backup
2. Run migrations: `alembic upgrade head`
3. Verify data integrity
4. Restart services

## Security Checklist

- [ ] All secrets in environment variables (not in code)
- [ ] HTTPS enforced everywhere
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] SQL injection prevention (ORM usage)
- [ ] Auth token validation on all endpoints
- [ ] Database credentials rotated
- [ ] Firewall rules restrict access
- [ ] Regular security audits
- [ ] Dependencies updated for known vulnerabilities

## Cost Estimation (Monthly)

| Component | Cost |
|-----------|------|
| PostgreSQL (AWS RDS t3.micro) | $10-15 |
| Backend (2 ECS tasks) | $20-30 |
| Frontend (Vercel) | $0-20 |
| Data transfer | $5-10 |
| Backups (S3) | $1-2 |
| **Total** | **~$40-80** |

(Costs vary by region and usage)

## Troubleshooting Deployment Issues

### Backend won't start
```bash
# Check logs
docker logs ai-ceo-backend
# Verify env vars
env | grep -E "DATABASE|NVIDIA|GOOGLE"
# Test DB connection
psql $DATABASE_URL
```

### Migration failures
```bash
# Check migration status
alembic current
alembic history
# Rollback if needed
alembic downgrade -1
# Re-run migrations
alembic upgrade head
```

### Frontend blank page
```bash
# Check browser console for errors
# Verify API_BASE_URL is correct
# Check CORS headers in API response
curl -i https://api.yourdomain.com/api/v1/projects
```

## Maintenance

### Weekly
- Monitor error rates and logs
- Check disk usage on database

### Monthly
- Update dependencies
- Review and rotate secrets
- Analyze performance metrics

### Quarterly
- Major version updates
- Security audit
- Disaster recovery drills

## Support & Escalation

For deployment issues:
1. Check this guide and README
2. Review application logs
3. Check external service status (Clerk, Nvidia, Google)
4. Contact hosting provider support if infrastructure issue
