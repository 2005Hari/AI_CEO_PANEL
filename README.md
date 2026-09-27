# AI CEO Panel - MVP Edition

**A founder's startup operating system that automates planning, task generation, and approval workflows.**

## Overview

AI CEO Panel is a lightweight MVP designed to help startup founders go from idea to executable plan in minutes. The system uses AI agents to:
- Generate comprehensive operating profiles from discovery interviews
- Create structured plans with milestones and tasks
- Assign tasks to specialized agents (Developer, Marketing, Designer)
- Manage approval workflows
- Track progress with real-time metrics

## Founder Workflow

The MVP supports a complete founder workflow:

1. **Create Project** - Founder creates a new startup project
2. **Complete Discovery** - AI-guided discovery interview generates company blueprint
3. **Generate Operating Profile** - System synthesizes blueprint into operational memory
4. **Request Plan** - Founder describes needs to Manager v2 agent
5. **Generate Plan & Tasks** - Manager v2 creates structured plan with tasks
6. **Agent Execution** - Developer, Marketing, Designer agents generate outputs
7. **Review Approvals** - Founder reviews and approves deliverables
8. **View Metrics** - Track progress on tasks, deliverables, and approvals

## Key Features (MVP Phase)

### Core Features
- ✅ Project and workspace management
- ✅ Discovery-driven company blueprint generation
- ✅ Operating profile creation (auto-synced from blueprint)
- ✅ Manager v2 agent for plan generation
- ✅ Task lifecycle with approval workflow
- ✅ Developer, Marketing, Designer agent support
- ✅ Lightweight approval system
- ✅ Real-time metrics dashboard

### Integrations (Skeleton)
- GitHub (repository creation, PR management)
- Vercel (deployment triggering)
- Google Workspace (doc creation)
- Slack (notifications)

### Not Included (Post-MVP)
- Finance Agent or billing system
- Operations Agent
- Sales Agent
- Health Engine
- Team collaboration features
- Advanced planning types

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI**: Nvidia NVIDIA API (LLM calls) + Google GenAI (embeddings)
- **Authentication**: Clerk (via JWT tokens)
- **Task Scheduling**: Async jobs via AsyncIO
- **Migrations**: Alembic

### Frontend
- **Framework**: Next.js 14+ (React + TypeScript)
- **Styling**: Tailwind CSS
- **Auth**: Clerk for user management
- **API Client**: Native fetch with auth token handling
- **State**: React hooks + local state

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Clerk account (for authentication)
- Nvidia API key (for LLM)
- Google GenAI API key (for embeddings)

### Backend Setup

1. **Clone and navigate to backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   Create `.env` file:
   ```
   DATABASE_URL=postgresql://user:password@localhost/ai_ceo_panel
   NVIDIA_API_KEY=your_nvidia_api_key
   GOOGLE_GENAI_API_KEY=your_google_genai_key
   CLERK_SECRET_KEY=your_clerk_secret_key
   CLERK_WEBHOOK_SECRET=your_webhook_secret
   ```

4. **Initialize database**
   ```bash
   alembic upgrade head
   ```

5. **Run development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**
   Create `.env.local`:
   ```
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
   CLERK_SECRET_KEY=your_clerk_secret_key
   ```

3. **Run development server**
   ```bash
   npm run dev
   ```

4. **Open browser**
   Navigate to `http://localhost:3000`

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry
│   ├── agents/                 # Agent implementations
│   │   ├── base.py             # BaseExecutiveAgent
│   │   ├── instances.py        # Agent instances (manager_v2, developer, designer)
│   │   ├── prompts.py          # Agent system prompts
│   │   └── registry.py         # Agent registry
│   ├── api/
│   │   ├── main.py             # API router setup
│   │   ├── deps/               # Dependency injectors
│   │   └── routes/             # API endpoint handlers
│   │       ├── manager.py      # Manager v1 & v2 endpoints
│   │       ├── plans.py        # Plan CRUD endpoints
│   │       ├── approvals.py    # Approval workflow endpoints
│   │       ├── metrics.py      # Metrics dashboard endpoint
│   │       └── ...             # Other routes
│   ├── db/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── session.py          # Database session setup
│   │   └── ...
│   ├── services/
│   │   ├── approvals.py        # Approval service
│   │   ├── task_engine.py      # Task execution engine
│   │   ├── integrations.py     # Integration providers
│   │   └── ...                 # Other services
│   ├── orchestrator/
│   │   ├── manager_v2.py       # Manager v2 orchestration
│   │   └── ...
│   └── ...
├── alembic/
│   └── versions/               # Database migrations
├── pytest.ini
├── requirements.txt
└── ...

frontend/
├── src/
│   ├── app/
│   │   ├── dashboard/          # Main dashboard page
│   │   ├── sign-in/            # Auth pages
│   │   └── ...
│   ├── components/             # Reusable components
│   ├── features/               # Feature components
│   │   ├── manager/            # Manager input & plan viewer
│   │   ├── approval/           # Approval workflow UI
│   │   ├── metrics/            # Metrics dashboard
│   │   └── ...
│   ├── lib/
│   │   ├── api.ts              # API client functions
│   │   └── auth-token.ts       # Auth token handling
│   └── ...
├── package.json
├── tsconfig.json
└── ...
```

## API Documentation

### Manager v2 Endpoint
```
POST /api/v1/projects/{project_id}/manager/plan_v2
Body: { "request": "string" }
Response: { "status": "success", "plan_id": "...", "tasks_created": [...], ... }
```

### Plans Endpoints
```
GET /api/v1/projects/{project_id}/plans
GET /api/v1/projects/{project_id}/plans/{plan_id}
```

### Approvals Endpoints
```
POST /api/v1/projects/{project_id}/approvals/request
Body: { "resource_type": "task|deliverable", "resource_id": "...", "reason": "..." }

POST /api/v1/projects/{project_id}/approvals/{approval_id}/decide
Body: { "approve": true|false, "reason": "..." }

GET /api/v1/projects/{project_id}/approvals/pending
```

### Metrics Endpoint
```
GET /api/v1/projects/{project_id}/metrics
Response: { "tasks": {...}, "deliverables": {...}, "approvals": {...} }
```

## Database Schema (MVP)

Key tables:
- `projects` - Startup projects
- `users` - Founder accounts
- `plans` - Generated execution plans
- `tasks` - Individual work items with lifecycle fields
- `deliverables` - Artifacts (landing pages, marketing assets, code)
- `approvals` - Approval records for tasks/deliverables
- `company_operating_profiles` - Operational memory
- `company_blueprints` - Discovery-generated company info
- `integrations` - Connected external services
- `kpis` - Metrics tracking

## Running Tests

### Backend
```bash
cd backend
pytest
# With coverage:
pytest --cov=app --cov-report=html
```

### Frontend
```bash
cd frontend
npm run test
```

## Deployment

### Docker Compose (Local/Development)
```bash
docker-compose up --build
```
This starts Postgres + pgvector, the backend (port 8000), and the frontend (port 3000)
with safe placeholder Clerk/NVIDIA credentials, so the stack boots without any setup.
Sign-in and real LLM calls won't work with the placeholders — for those, create a
`.env` file at the repo root (docker-compose reads it automatically) with your real
`NVIDIA_API_KEY`, `CLERK_ISSUER`, `CLERK_JWKS_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`,
and `CLERK_SECRET_KEY`, then re-run `docker-compose up --build`.

### Production Deployment (See DEPLOYMENT.md)
- Build and push Docker images
- Configure Postgres on Neon or AWS RDS
- Deploy backend to AWS ECS, Heroku, or Cloud Run
- Deploy frontend to Vercel, Netlify, or S3 + CloudFront
- Set up DNS and SSL

## Troubleshooting

### Backend won't connect to database
- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Run `alembic upgrade head` to initialize schema

### Frontend API calls fail
- Verify backend is running on `http://localhost:8000`
- Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
- Ensure auth token is being sent (check browser DevTools)

### LLM calls failing
- Verify `NVIDIA_API_KEY` and `GOOGLE_GENAI_API_KEY` are set
- Check API quotas and rate limits

## Contributing

This is an MVP. Focus areas for contribution:
1. **Improve agent prompts** - Enhance manager, developer, designer outputs
2. **Add integration providers** - Extend GitHub, Vercel, Google, Slack
3. **Expand approval workflow** - Add multi-step approvals, delegation
4. **Metrics expansion** - Add custom KPI tracking
5. **Performance optimization** - Caching, query optimization

## License

Private (Founder Use Only)

## Support

For issues, questions, or feature requests:
1. Check this README for solutions
2. Review existing GitHub issues
3. Contact the development team
