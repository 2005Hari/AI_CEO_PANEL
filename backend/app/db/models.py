from datetime import datetime
import uuid
from typing import List, Dict, Any

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())


# ──────────────────────────────────────────────
# EXISTING MODELS (preserved, extended where noted)
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    clerk_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("Project", back_populates="owner")
    workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    founder_profile = relationship("FounderProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    cost_records = relationship("AgentCostRecord", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String, nullable=False)
    # Storing core facts and user preferences as structured JSON
    core_context = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ── NEW COLUMNS ──
    operating_mode = Column(String, default="startup")       # 'startup' | 'business'
    discovery_completed = Column(Boolean, default=False)
    health_score = Column(Float, nullable=True)
    
    # ── RELATIONSHIPS (existing) ──
    owner = relationship("User", back_populates="projects")
    workspace = relationship("Workspace", back_populates="projects")
    sessions = relationship("Session", back_populates="project")
    memories = relationship("Memory", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    agent_configs = relationship("AgentConfig", back_populates="project", cascade="all, delete-orphan")
    
    # ── RELATIONSHIPS (new) ──
    blueprint = relationship("CompanyBlueprint", back_populates="project", uselist=False, cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("AgentActivity", back_populates="project", cascade="all, delete-orphan")
    objectives = relationship("Objective", back_populates="project", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="project", cascade="all, delete-orphan")
    kpis = relationship("KPI", back_populates="project", cascade="all, delete-orphan")
    deliverables = relationship("Deliverable", back_populates="project", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="project", cascade="all, delete-orphan")
    cost_records = relationship("AgentCostRecord", back_populates="project", cascade="all, delete-orphan")
    operating_profile = relationship(
        "CompanyOperatingProfile", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    decisions = relationship("DecisionLog", back_populates="project", cascade="all, delete-orphan")
    memory_updates = relationship("MemoryUpdateEvent", back_populates="project", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="project", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="project", cascade="all, delete-orphan")
    queues = relationship("WorkQueue", back_populates="project", cascade="all, delete-orphan")
    agent_communications = relationship("AgentCommunicationLog", back_populates="project", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="sessions")
    messages = relationship("Message", back_populates="session", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False) # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    # Storing the drafts from individual agents to render the history properly
    agent_drafts = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="messages")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="documents")
    memories = relationship("Memory", back_populates="document", cascade="all, delete-orphan")

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    # Using Google GenAI text-embedding-004 which is 768 dims
    embedding = Column(Vector(768))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="memories")
    document = relationship("Document", back_populates="memories")

class AgentConfig(Base):
    __tablename__ = "agent_configs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    agent_role = Column(String, nullable=False)  # 'visionary', 'operations', etc.
    system_prompt = Column(Text, nullable=True)
    model_override = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    is_enabled = Column(Boolean, default=True)
    
    project = relationship("Project", back_populates="agent_configs")


# ──────────────────────────────────────────────
# NEW MODELS — Phase 1: Company Blueprint
# ──────────────────────────────────────────────

class CompanyBlueprint(Base):
    __tablename__ = "company_blueprints"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Core Identity
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    business_model = Column(String, nullable=True)
    target_audience = Column(Text, nullable=True)
    value_proposition = Column(Text, nullable=True)
    
    # Products & Market
    products_services = Column(JSON, default=list)        # [{name, description, status}]
    competitors = Column(JSON, default=list)               # [{name, threat_level, notes}]
    revenue_model = Column(Text, nullable=True)
    pricing = Column(JSON, default=dict)
    
    # Team & Operations
    team_size = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    geography = Column(String, nullable=True)
    tech_stack = Column(Text, nullable=True)
    
    # Strategy
    marketing_strategy = Column(Text, nullable=True)
    sales_strategy = Column(Text, nullable=True)
    current_goals = Column(JSON, default=list)
    current_problems = Column(JSON, default=list)
    product_roadmap = Column(JSON, default=list)
    
    # Brand & Stage
    brand_voice = Column(Text, nullable=True)
    growth_stage = Column(String, nullable=True)           # 'idea' | 'mvp' | 'growth' | 'scale'
    
    # Meta
    discovery_confidence = Column(Float, default=0.0)
    field_confidences = Column(JSON, default=dict)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)
    
    project = relationship("Project", back_populates="blueprint")


# ──────────────────────────────────────────────
# NEW MODELS — Phase 3: Agent Definitions Registry
# ──────────────────────────────────────────────

class AgentDefinition(Base):
    __tablename__ = "agent_definitions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    role = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    category = Column(String, nullable=True)               # 'strategy'|'marketing'|'engineering'|'operations'|'creative'
    
    system_prompt = Column(Text, nullable=False)
    output_schema = Column(JSON, default=dict)
    icon = Column(String, default="💼")
    color = Column(String, default="#3b82f6")
    
    supported_modes = Column(JSON, default=lambda: ["startup", "business"])
    is_system = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# NEW MODELS — Phase 4: Task Engine
# ──────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assigned_agent = Column(String, nullable=True)
    
    status = Column(String, default="pending")             # pending|assigned|working|review|completed|blocked
    priority = Column(String, default="medium")             # low|medium|high|urgent
    progress = Column(Float, default=0.0)                   # 0.0 to 1.0
    # Expanded lifecycle / tracking fields
    plan_id = Column(String, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    # deliverable linkage handled on Deliverable.task_id (see architecture v2 deliverable)
    stage = Column(String, default="todo")                 # todo|in_progress|review|done|archived
    review_required = Column(Boolean, default=False)
    reviewer_id = Column(String, nullable=True)
    approval_status = Column(String, default="unapproved") # unapproved|approved|rejected
    approval_history = Column(JSON, default=list)
    estimated_hours = Column(Float, nullable=True)
    time_spent_hours = Column(Float, default=0.0)
    due_date = Column(DateTime, nullable=True)
    review_requested_at = Column(DateTime, nullable=True)
    blocked_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    attempt_logs = Column(JSON, default=list)
    external_url = Column(String, nullable=True)
    
    # Execution context
    input_context = Column(JSON, default=dict)
    output_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    project = relationship("Project", back_populates="tasks")
    parent_task = relationship("Task", remote_side="Task.id", backref="subtasks")
    dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.task_id", cascade="all, delete-orphan")
    activities = relationship("AgentActivity", back_populates="task")
    plan = relationship("Plan", back_populates="tasks")
    queue_entry = relationship("WorkQueue", back_populates="task", uselist=False, cascade="all, delete-orphan")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)


# ──────────────────────────────────────────────
# NEW MODELS — Plan & Deliverable (MVP Phase)
# ──────────────────────────────────────────────

class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    milestones = Column(JSON, default=list)   # [{title, due_date, status}]
    status = Column(String, default="draft") # draft|active|paused|completed
    owner_agent = Column(String, nullable=True)
    plan_type = Column(String, nullable=True) # 'operational'|'marketing'|'engineering' etc.
    confidence_score = Column(Float, nullable=True)
    generated_by = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="plans")
    tasks = relationship("Task", back_populates="plan", cascade="all, delete-orphan")
    deliverables = relationship("Deliverable", back_populates="plan", cascade="all, delete-orphan")





# ──────────────────────────────────────────────
# NEW MODELS — Phase 5: Objectives
# ──────────────────────────────────────────────

class Objective(Base):
    __tablename__ = "objectives"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)               # 'product'|'marketing'|'sales'|'engineering'|'operations'
    status = Column(String, default="active")               # 'active'|'completed'|'paused'
    progress = Column(Float, default=0.0)
    target_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="objectives")


# ──────────────────────────────────────────────
# NEW MODELS — Phase 6: Agent Activity Feed
# ──────────────────────────────────────────────

class AgentActivity(Base):
    __tablename__ = "agent_activities"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    
    agent_role = Column(String, nullable=False)
    activity_type = Column(String, nullable=False)         # 'thinking'|'generating'|'reviewing'|'completed'|'error'
    message = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="activities")
    task = relationship("Task", back_populates="activities")


# ──────────────────────────────────────────────
# NEW MODELS — Phase 8: Integration Framework
# ──────────────────────────────────────────────

class Integration(Base):
    __tablename__ = "integrations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    provider = Column(String, nullable=False)              # 'github'|'vercel'|'gmail'|etc.
    status = Column(String, default="disconnected")        # 'connected'|'disconnected'|'error'
    config = Column(JSON, default=dict)                     # Encrypted credentials/tokens
    
    connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="integrations")


# ──────────────────────────────────────────────
# PRIORITY 2 — Company Operating Memory
# ──────────────────────────────────────────────

class CompanyOperatingProfile(Base):
    """Canonical company brain — synced from Blueprint, extended with assets/risks."""
    __tablename__ = "company_operating_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    business_model = Column(String, nullable=True)
    target_audience = Column(Text, nullable=True)
    value_proposition = Column(Text, nullable=True)
    market_positioning = Column(Text, nullable=True)

    products_services = Column(JSON, default=list)
    competitors = Column(JSON, default=list)
    customer_segments = Column(JSON, default=list)
    revenue_model = Column(Text, nullable=True)
    pricing = Column(JSON, default=dict)

    team_structure = Column(JSON, default=dict)
    team_size = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    geography = Column(String, nullable=True)
    tech_stack = Column(Text, nullable=True)

    marketing_strategy = Column(Text, nullable=True)
    sales_strategy = Column(Text, nullable=True)
    marketing_assets = Column(JSON, default=list)
    technical_assets = Column(JSON, default=list)

    current_goals = Column(JSON, default=list)
    current_problems = Column(JSON, default=list)
    product_roadmap = Column(JSON, default=list)
    risks = Column(JSON, default=list)

    brand_voice = Column(Text, nullable=True)
    growth_stage = Column(String, nullable=True)
    operating_mode = Column(String, default="startup")

    discovery_confidence = Column(Float, default=0.0)
    synced_from_blueprint_version = Column(Integer, default=0)
    last_synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="operating_profile")


class DecisionLog(Base):
    """Immutable record of founder and agent decisions."""
    __tablename__ = "decision_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    decision_type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    source_agent = Column(String, nullable=True)
    summary = Column(Text, nullable=False)
    context = Column(JSON, default=dict)

    related_task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    related_session_id = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    related_deliverable_id = Column(String, ForeignKey("deliverables.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    project = relationship("Project", back_populates="decisions")


class MemoryUpdateEvent(Base):
    """Audit trail for automatic operating memory updates."""
    __tablename__ = "memory_update_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    trigger = Column(String, nullable=False)
    source = Column(String, nullable=False)
    field_updates = Column(JSON, default=dict)
    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    project = relationship("Project", back_populates="memory_updates")


# ──────────────────────────────────────────────
# ARCHITECTURE v2 — Identity & workspace (schema only in P1)
# ──────────────────────────────────────────────

class Workspace(Base):
    """Lightweight container grouping projects for a single founder."""
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, default="My Workspace")
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="workspaces")
    projects = relationship("Project", back_populates="workspace")


class FounderProfile(Base):
    """Founder identity and preferences — 1:1 with User."""
    __tablename__ = "founder_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    display_name = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    timezone = Column(String, default="UTC")
    expertise = Column(JSON, default=list)
    preferences = Column(JSON, default=dict)
    founding_goals = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="founder_profile")


# ──────────────────────────────────────────────
# ARCHITECTURE v2 — KPI framework (schema only in P1)
# ──────────────────────────────────────────────

class KPI(Base):
    """Metric definition scoped to a project."""
    __tablename__ = "kpis"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    target_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    period = Column(String, default="monthly")
    is_active = Column(Boolean, default=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="kpis")
    records = relationship("KPIRecord", back_populates="kpi", cascade="all, delete-orphan")


class KPIRecord(Base):
    """Time-series data point for a KPI."""
    __tablename__ = "kpi_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    kpi_id = Column(String, ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    kpi = relationship("KPI", back_populates="records")


# ──────────────────────────────────────────────
# ARCHITECTURE v2 — Deliverable storage (schema only in P1)
# Dual storage: inline content + optional file reference (local/s3)
# Chain: Objective → Plan → Task → Deliverable
# ──────────────────────────────────────────────

class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    objective_id = Column(String, ForeignKey("objectives.id", ondelete="SET NULL"), nullable=True)
    plan_id = Column(String, ForeignKey("plans.id", ondelete="CASCADE"), nullable=True, index=True)

    deliverable_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default="draft")

    content_markdown = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=True)
    storage_backend = Column(String, default="inline")
    storage_path = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    checksum_sha256 = Column(String, nullable=True)

    version = Column(Integer, default=1)
    parent_deliverable_id = Column(String, ForeignKey("deliverables.id"), nullable=True)

    created_by_agent = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by_user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="deliverables")
    plan = relationship("Plan", back_populates="deliverables")
    parent = relationship("Deliverable", remote_side="Deliverable.id", backref="revisions")


# ──────────────────────────────────────────────
# ARCHITECTURE v2 — Agent cost tracking (schema only in P1)
# ──────────────────────────────────────────────

class AgentCostRecord(Base):
    __tablename__ = "agent_cost_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    agent_role = Column(String, nullable=True)
    operation_type = Column(String, nullable=False)
    model_name = Column(String, nullable=False)

    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)

    task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    metadata_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    project = relationship("Project", back_populates="cost_records")
    user = relationship("User", back_populates="cost_records")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    resource_type = Column(String, nullable=False)   # 'task'|'deliverable'|'plan'
    resource_id = Column(String, nullable=False)

    requested_by = Column(String, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")     # pending|approved|rejected
    approver_id = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decision_reason = Column(Text, nullable=True)
    history = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="approvals")


# ──────────────────────────────────────────────
# NEW MODELS — Phase 2: Departments & Work Queues
# ──────────────────────────────────────────────

class Department(Base):
    __tablename__ = "departments"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False) # 'Technology', 'Marketing', etc.
    manager_agent = Column(String, nullable=False) # 'CTO Agent', 'CMO Agent'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="departments")
    queues = relationship("WorkQueue", back_populates="department", cascade="all, delete-orphan")


class WorkQueue(Base):
    __tablename__ = "work_queues"
    id = Column(String, primary_key=True, default=generate_uuid)
    department_id = Column(String, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(String, default="queued") # queued | processing | completed | failed
    assigned_worker = Column(String, nullable=True) # E.g., "Developer Agent"
    
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    department = relationship("Department", back_populates="queues")
    project = relationship("Project", back_populates="queues")
    task = relationship("Task", back_populates="queue_entry", uselist=False)


class AgentCommunicationLog(Base):
    __tablename__ = "agent_communication_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sender_agent = Column(String, nullable=False)
    receiver_agent = Column(String, nullable=True) # Null if broadcast
    message = Column(Text, nullable=False)
    event_type = Column(String, default="message") # message | task_request | escalation
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    project = relationship("Project", back_populates="agent_communications")

