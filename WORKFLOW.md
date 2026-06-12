# MVP Workflow Guide

## Quick Start: From Startup Idea to Executable Plan

This guide walks a founder through the complete AI CEO Panel MVP workflow in ~15 minutes.

## Step 1: Sign In & Create Project

1. Go to `https://yourdomain.com`
2. Sign in with Clerk (Google, GitHub, or email)
3. Click "Create Startup"
4. Enter startup name (e.g., "TechFlow")
5. Click "Create"

**Result**: You're in the dashboard with a new project ready for discovery.

## Step 2: Complete Discovery Interview

1. Click the **🧭 Discovery** tab
2. AI interviewer asks about your startup:
   - What problem does it solve?
   - Who is your target audience?
   - What's your business model?
   - What's your tech stack?
   - What are your short-term goals?

3. Answer each question honestly (2-3 sentences each)
4. Click "Next" after each answer
5. When complete, click "Finalize Discovery"

**Result**: System generates Company Blueprint with all your startup details.

## Step 3: View Operating Profile

1. Click the **📊 Overview** tab
2. Your Operating Profile auto-generates from the blueprint
3. Review key sections:
   - Company name, industry, business model
   - Products/services overview
   - Team and budget info
   - Tech stack
   - Marketing & sales strategy
   - Current goals and problems

**Result**: Your AI-generated operating memory is ready.

## Step 4: Request Manager v2 Plan

1. Click the **📊 Plans** tab
2. In the "Manager v2: Generate Plan & Tasks" section, describe what you need:
   ```
   Example: "I need a landing page, pricing page, and marketing strategy for launch in 2 weeks"
   ```
3. Click "Generate Plan & Tasks"
4. Wait 30-60 seconds for AI to generate

**Result**: Manager v2 breaks down your request into:
- A comprehensive plan with milestones
- Specific tasks assigned to agents (developer, marketing, designer)
- Task descriptions with priorities

## Step 5: Review Generated Plan

1. Still in **📊 Plans** tab
2. See your newly created plan in the "Available Plans" section
3. Click the plan to view its details:
   - Plan title and description
   - Task list with assignments
   - Task descriptions and priorities

4. Review each task:
   - Who's assigned (developer, marketing, designer)
   - What needs to be done
   - Priority level
   - Status (starts as "assigned")

**Result**: You have a structured roadmap with clear task ownership.

## Step 6: Approve Deliverables

1. Click the **✅ Approvals** tab
2. See pending approvals for tasks and deliverables
3. For each pending approval:
   - Read the description and context
   - Click **Approve** to accept and move to next step
   - Click **Reject** to request changes (optional reason)

4. As approvals progress:
   - Task status updates (assigned → in-progress → review → done)
   - Deliverables are marked ready or completed

**Result**: You control the quality gate. Only approved work advances.

## Step 7: Monitor Progress

1. Click the **📈 Metrics** tab
2. See real-time dashboard with:
   - **Tasks**: Pending, Assigned, In Progress, Completed counts
   - **Deliverables**: Pending, In Progress, Ready for Review, Approved counts
   - **Approvals**: Pending, Approved, Rejected counts

3. Refresh to see updates as agents work

**Result**: Full visibility into project status at a glance.

## Step 8: Access Deliverables

As tasks complete and you approve deliverables:
- Landing page HTML/CSS is available
- Marketing copy and assets are generated
- Code is pushed to GitHub (if integrated)
- Deployments can be triggered to Vercel (if integrated)

## Key Commands

### In the Dashboard

| Tab | Purpose |
|-----|---------|
| 📊 Overview | View your operating profile |
| 🧭 Discovery | Start/continue discovery interview |
| 🎯 Objectives | Set and track goals |
| 📋 Task Board | View all tasks in kanban board |
| **📊 Plans** | **Generate and view plans** |
| **✅ Approvals** | **Review and approve deliverables** |
| **📈 Metrics** | **Track progress dashboard** |
| 💬 Boardroom | Legacy agent chat interface |
| ⚙️ Settings | Project settings and integrations |

### Manager v2 Commands

In the **Plans** tab, describe your needs naturally:

```
"I need a React landing page with pricing, contact form, and blog section"

"Create a GTM strategy and social media content calendar for launch"

"Build out the technical architecture and deployment pipeline"

"Generate brand guidelines, logo concepts, and color palette"
```

## Integration Setup (Optional)

### Connect GitHub
1. Go to ⚙️ **Settings**
2. Find "GitHub Integration"
3. Click "Connect"
4. Authorize with your GitHub account
5. Manager can now create repos and PRs

### Connect Vercel
1. Go to ⚙️ **Settings**
2. Find "Vercel Integration"
3. Click "Connect"
4. Authorize with your Vercel account
5. Manager can now trigger deployments

## Workflow Variations

### For Landing Page MVP
1. Complete discovery
2. Request: "Landing page with pricing, CTA buttons, and testimonials"
3. Approve designer's mockups
4. Approve developer's code
5. Deploy to Vercel

### For B2B SaaS
1. Complete discovery
2. Request: "SaaS onboarding flow, user dashboard prototype, API documentation"
3. Review and approve each component
4. Set up GitHub integration
5. Have developer push code

### For Content/Marketing MVP
1. Complete discovery
2. Request: "Blog post strategy, 5 article outlines, social media content calendar"
3. Review marketing copy
4. Schedule content rollout
5. Use metrics to track engagement

## Troubleshooting

### Manager doesn't generate plan
- Ensure your discovery is marked "Complete"
- Try simpler, more specific request
- Check that backend is running

### Approvals not appearing
- Refresh the page
- Check that tasks have been created
- Ensure review_required is set on tasks

### No deliverables shown
- Wait for agents to process tasks
- Check task status in Task Board tab
- Try requesting a specific deliverable type

### Integration not working
- Verify you've authorized the integration
- Check that you have required API tokens
- Review application logs for errors

## Next Steps After MVP

Once your initial plan is approved and deliverables are ready:

1. **Deploy** - Use integrations to push code to GitHub and deploy to Vercel
2. **Iterate** - Request additional tasks or modifications
3. **Scale** - Add more team members and delegate tasks
4. **Measure** - Use metrics to track KPIs and adjust strategy

## Support

- **Documentation**: See [README.md](README.md) and [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Docs**: Check backend `/docs` endpoint (Swagger UI)
- **Issues**: Report bugs with steps to reproduce
- **Feedback**: Share feature requests and improvements

---

**Ready to go?** Create your first project and complete the discovery interview!
