import pytest
from sqlalchemy import select

from app.db.models import (
    CompanyBlueprint,
    CompanyOperatingProfile,
    DecisionLog,
    FounderProfile,
    MemoryUpdateEvent,
)
from app.db.session import AsyncSessionLocal
from app.events.bus import event_bus
from app.events import types as event_types
from app.services.context_builder import UnifiedContextBuilder
from app.services.memory_hooks import on_blueprint_updated
from app.services.operating_profile import sync_operating_profile_from_blueprint


@pytest.mark.asyncio
async def test_event_bus_delivers_to_subscriber():
    received = []

    async def handler(payload):
        received.append(payload)

    event_bus.subscribe("test.event", handler)
    await event_bus.publish("test.event", {"value": 42})
    assert received == [{"value": 42}]


@pytest.mark.asyncio
async def test_blueprint_syncs_to_operating_profile(user_project):
    async with AsyncSessionLocal() as db:
        blueprint = CompanyBlueprint(
            project_id=user_project.id,
            company_name="Acme AI",
            industry="SaaS",
            value_proposition="AI ops for founders",
            current_goals=["Launch MVP"],
        )
        db.add(blueprint)
        await db.commit()

        profile, updated = await sync_operating_profile_from_blueprint(db, user_project.id)
        assert profile.company_name == "Acme AI"
        assert profile.industry == "SaaS"
        assert "company_name" in updated
        assert profile.discovery_confidence == 0.0


@pytest.mark.asyncio
async def test_memory_hook_creates_update_event(user_project):
    async with AsyncSessionLocal() as db:
        blueprint = CompanyBlueprint(
            project_id=user_project.id,
            company_name="Hook Test Co",
            business_model="B2B",
        )
        db.add(blueprint)
        await db.commit()

    await on_blueprint_updated(user_project.id, ["company_name"])

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MemoryUpdateEvent).where(MemoryUpdateEvent.project_id == user_project.id)
        )
        events = result.scalars().all()
        assert len(events) >= 1
        assert events[0].trigger == event_types.BLUEPRINT_UPDATED


@pytest.mark.asyncio
async def test_unified_context_builder_includes_profile_and_founder(user_project, mock_user):
    async with AsyncSessionLocal() as db:
        blueprint = CompanyBlueprint(
            project_id=user_project.id,
            company_name="Context Co",
            target_audience="SMB founders",
        )
        db.add(blueprint)
        fp = FounderProfile(
            user_id=mock_user.id,
            display_name="Jane Founder",
            founding_goals=["Build AI OS"],
        )
        db.add(fp)
        await db.commit()

        await sync_operating_profile_from_blueprint(db, user_project.id)
        context = await UnifiedContextBuilder.build(
            db, user_project.id, user_id=mock_user.id, include_rag=False
        )

        assert "Context Co" in context.prompt_text
        assert "Jane Founder" in context.prompt_text
        assert "SMB founders" in context.prompt_text
        assert context.structured["operating_profile"]["company_name"] == "Context Co"


@pytest.mark.asyncio
async def test_decision_log_persists(user_project):
    from app.services.decisions import log_decision

    async with AsyncSessionLocal() as db:
        decision = await log_decision(
            db,
            project_id=user_project.id,
            decision_type="strategic",
            source="boardroom",
            summary="Proceed with niche GTM",
            publish=False,
        )
        result = await db.execute(select(DecisionLog).where(DecisionLog.id == decision.id))
        assert result.scalars().first() is not None
