# QA & Testing Guide - AI CEO Panel MVP

## Pre-Launch Testing Checklist

### Backend API Testing

#### Database Setup
- [ ] PostgreSQL running and accessible
- [ ] All migrations applied: `alembic current` shows latest version
- [ ] Database contains required tables: `plans`, `deliverables`, `approvals`, `tasks`
- [ ] Indexes created for query performance

#### Health Checks
```bash
# Test backend is running
curl http://localhost:8000/health

# Test database connection
curl http://localhost:8000/api/v1/projects

# Test Clerk auth required
curl -H "Authorization: Bearer invalid" http://localhost:8000/api/v1/projects
# Should return 403 Unauthorized
```

#### Manager v2 API
```bash
# Get valid auth token from Clerk (from browser DevTools)
TOKEN="your_jwt_token_here"

# Create a test project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Project","core_context":{}}'

# Get project ID from response
PROJECT_ID="xxxxx"

# Test Manager v2 plan generation
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/manager/plan_v2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request":"Create a landing page with pricing"}'
# Response should have status: "success"
```

#### Plans Routes
```bash
# List plans
curl http://localhost:8000/api/v1/projects/$PROJECT_ID/plans \
  -H "Authorization: Bearer $TOKEN"

# Get specific plan
curl http://localhost:8000/api/v1/projects/$PROJECT_ID/plans/{plan_id} \
  -H "Authorization: Bearer $TOKEN"
```

#### Approvals Routes
```bash
# Request approval
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/approvals/request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"resource_type":"task","resource_id":"task_id_here"}'

# List pending approvals
curl http://localhost:8000/api/v1/projects/$PROJECT_ID/approvals/pending \
  -H "Authorization: Bearer $TOKEN"

# Decide approval
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/approvals/{approval_id}/decide \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approve":true,"reason":"Looks good"}'
```

#### Metrics Route
```bash
# Get metrics
curl http://localhost:8000/api/v1/projects/$PROJECT_ID/metrics \
  -H "Authorization: Bearer $TOKEN"
# Response should have tasks, deliverables, approvals counts
```

### Frontend UI Testing

#### Authentication
- [ ] User can sign up with Clerk
- [ ] User can sign in with email/Google/GitHub
- [ ] Auth token is stored and sent with API calls
- [ ] Unauthorized users redirected to sign-in page

#### Project Creation
- [ ] User can create a new project
- [ ] Project name is validated (not empty)
- [ ] New project appears in sidebar project list
- [ ] Can switch between multiple projects

#### Discovery Tab
- [ ] Discovery questions load
- [ ] User can answer each question
- [ ] Responses save properly
- [ ] Can navigate between questions
- [ ] Can finalize discovery
- [ ] Operating profile auto-generates after finalize

#### Overview Tab
- [ ] Operating profile displays
- [ ] All sections visible (company info, strategy, etc.)
- [ ] Profile updates when discovery changes

#### Plans Tab
- [ ] Manager v2 input form appears
- [ ] User can type multi-line requests
- [ ] "Generate Plan & Tasks" button works
- [ ] Loading state shows while generating
- [ ] Plans list populates after generation
- [ ] Can click plan to see tasks
- [ ] Tasks display with correct details (title, agent, priority)

#### Approvals Tab
- [ ] Pending approvals load
- [ ] Approval cards show resource type and ID
- [ ] "Approve" button works and updates status
- [ ] "Reject" button works
- [ ] Empty state shows when no approvals pending
- [ ] Auto-refresh shows new approvals

#### Metrics Tab
- [ ] Metrics load
- [ ] Task counts display (pending, assigned, etc.)
- [ ] Deliverable counts display
- [ ] Approval counts display
- [ ] "Refresh" button updates metrics
- [ ] Metrics auto-refresh every 10 seconds

#### Task Board Tab
- [ ] Tasks load from database
- [ ] Tasks filter by status
- [ ] Can view task details
- [ ] Plan association visible

#### Settings Tab
- [ ] Project settings display
- [ ] Integration options available
- [ ] Can configure integrations (GitHub, Vercel, etc.)

### End-to-End Workflow Testing

#### Complete Founder Flow (15 minutes)

1. **Create Project**
   - [ ] Sign in → Create new project → Name it "Test Startup"

2. **Discovery**
   - [ ] Start discovery → Answer 5 questions → Finalize
   - [ ] Blueprint should be created in database

3. **Operating Profile**
   - [ ] Go to Overview tab
   - [ ] Profile loads with discovery data
   - [ ] All fields properly populated

4. **Manager v2 Plan**
   - [ ] Go to Plans tab
   - [ ] Type request: "Create a landing page with pricing and signup form"
   - [ ] Click "Generate Plan & Tasks"
   - [ ] Wait for response (30-60 seconds)
   - [ ] Plan appears in list
   - [ ] Click plan → see tasks

5. **View Tasks**
   - [ ] Tasks display with assignments
   - [ ] Each task has title, description, priority, agent
   - [ ] Status shows "assigned"

6. **Approvals Workflow**
   - [ ] Go to Approvals tab
   - [ ] See pending approvals for tasks
   - [ ] Click "Approve" on one task
   - [ ] Go to Task Board → task status updates to approved
   - [ ] Go back to Approvals → approval count decreased

7. **Metrics**
   - [ ] Go to Metrics tab
   - [ ] See task counts (some pending, some approved)
   - [ ] See deliverables (should have some pending/approved)
   - [ ] See approval counts
   - [ ] Click Refresh → counts update

#### Test Data Verification
```bash
# After running full workflow, verify data in database:

# Check plan exists
psql $DATABASE_URL -c "SELECT id, title, status FROM plans LIMIT 1;"

# Check tasks linked to plan
psql $DATABASE_URL -c "SELECT id, title, plan_id, status FROM tasks WHERE plan_id IS NOT NULL LIMIT 5;"

# Check deliverables
psql $DATABASE_URL -c "SELECT id, title, status FROM deliverables LIMIT 5;"

# Check approvals
psql $DATABASE_URL -c "SELECT id, resource_type, status FROM approvals LIMIT 5;"
```

### Performance Testing

#### Load Time
- [ ] Dashboard page loads in < 2 seconds
- [ ] Plans tab loads in < 1 second
- [ ] Metrics refresh in < 3 seconds

#### Concurrent Users
- [ ] 10 simultaneous users creating projects - no errors
- [ ] 5 users generating plans simultaneously - all succeed
- [ ] Database connections stable (check `SELECT count(*) FROM pg_stat_activity;`)

```bash
# Load test with Apache Bench
ab -n 100 -c 10 http://localhost:3000/dashboard

# API load test
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/projects
```

### Error Handling

#### Backend Errors
- [ ] Invalid token → 403 Unauthorized
- [ ] Missing required fields → 400 Bad Request
- [ ] Database down → 500 Internal Server Error (logged)
- [ ] Invalid project ID → 404 Not Found

#### Frontend Errors
- [ ] API timeout → error message shown, retry option
- [ ] Invalid input → validation message
- [ ] Network error → graceful degradation
- [ ] Missing auth → redirect to sign-in

### Browser Compatibility

Test on:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Chrome
- [ ] Mobile Safari

### Responsive Design
- [ ] Desktop (1920x1080) - all elements visible
- [ ] Tablet (768x1024) - sidebar collapses
- [ ] Mobile (375x667) - hamburger menu works

## Integration Testing

### GitHub Integration (if enabled)
- [ ] Connect GitHub account
- [ ] Manager can create repository
- [ ] Manager can create pull request
- [ ] Code pushed to GitHub appears in repo

### Vercel Integration (if enabled)
- [ ] Connect Vercel account
- [ ] Manager can trigger deployment
- [ ] Deployment completes successfully
- [ ] Site accessible at deployed URL

### Slack Integration (if enabled)
- [ ] Connect Slack workspace
- [ ] Notifications sent on task completion
- [ ] Messages format correctly

## Database Migration Testing

```bash
# Test forward migration
alembic upgrade head

# Verify tables exist
\dt
# Should show: plans, deliverables, approvals, tasks (with new columns)

# Test backward migration
alembic downgrade -1

# Verify tables removed
\dt
# Should not have plans, deliverables, approvals

# Re-apply
alembic upgrade head
```

## Security Testing

- [ ] SQL injection attempt fails: `'; DROP TABLE plans; --`
- [ ] XSS attempt in input: `<script>alert('xss')</script>` - stored as text
- [ ] CORS headers only allow configured domains
- [ ] Secrets not exposed in error messages
- [ ] Sensitive data not logged

```bash
# Test CORS
curl -H "Origin: http://malicious.com" \
  -H "Access-Control-Request-Method: GET" \
  http://localhost:8000/api/v1/projects

# Should NOT include Access-Control-Allow-Origin for malicious.com
```

## Regression Testing

After any changes, verify:
- [ ] Discovery workflow still works
- [ ] Plans still generate
- [ ] Approvals still function
- [ ] Metrics update correctly
- [ ] No console errors in browser
- [ ] No errors in backend logs

## Test Results Template

```markdown
## Test Run - [Date]

### Backend API
- Discovery Workflow: ✅ PASS
- Manager v2 Plan Generation: ✅ PASS
- Approval Workflow: ✅ PASS
- Metrics Endpoint: ✅ PASS
- Error Handling: ✅ PASS

### Frontend UI
- Authentication: ✅ PASS
- Project Creation: ✅ PASS
- Plans Generation: ✅ PASS
- Approvals: ✅ PASS
- Metrics: ✅ PASS
- Responsive Design: ✅ PASS

### Performance
- Dashboard Load: 1.2s ✅
- API Response (avg): 450ms ✅
- Database Queries (avg): 120ms ✅

### Compatibility
- Chrome: ✅ PASS
- Firefox: ✅ PASS
- Safari: ✅ PASS
- Mobile: ✅ PASS

### Overall: ✅ READY FOR PRODUCTION
```

## Deployment Test Checklist

Before deploying to production:

- [ ] All API endpoints tested with production database
- [ ] All frontend pages tested with production API base URL
- [ ] SSL certificate valid and renewed
- [ ] Database backups configured
- [ ] Monitoring and logging configured
- [ ] Email notifications configured (if needed)
- [ ] Error tracking (Sentry) configured
- [ ] Analytics configured
- [ ] Rate limiting configured
- [ ] CORS configured for production domain

## Post-Deployment Verification

After deploying to production:

- [ ] Health check endpoint returns 200
- [ ] User can sign up and create project
- [ ] Discovery workflow completes
- [ ] Manager v2 generates plan
- [ ] Metrics dashboard updates
- [ ] Approvals workflow functions
- [ ] All integrations working
- [ ] Error logging active
- [ ] No sensitive data in logs

## Continuous Testing

### Automated Tests
```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm run test
```

### Monitoring
- CloudWatch/Datadog alerts for:
  - Error rate > 5%
  - API response time > 1000ms
  - Database connection errors
  - Disk usage > 80%

### Regular Audits
- Weekly: Check error logs, performance metrics
- Monthly: Security scan, dependency updates
- Quarterly: Load testing, disaster recovery drill
