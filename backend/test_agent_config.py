# backend/test_agent_config.py
import asyncio
import os
import sys
from sqlalchemy import select

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.session import AsyncSessionLocal, sync_engine
from app.db.models import Base, Project, AgentConfig
from app.agents.instances import AGENTS_MAP
from app.orchestrator.state import GraphState
from app.orchestrator.nodes import analyze_intent, execute_agents, execute_critic

async def test_agent_config_flow():
    print("Starting Boardroom Agent Configuration Tests...")
    print("-----------------------------------------------")
    
    # 1. Initialize Tables
    print("Initializing Database tables (includes agent_configs)...")
    Base.metadata.create_all(bind=sync_engine)
    
    # 2. Setup Async Session
    async with AsyncSessionLocal() as db:
        # 3. Create a test Project
        print("Creating mock project...")
        test_project = Project(
            name="Custom Agent Test Startup",
            core_context={"value_proposition": "A custom prompt validation startup."},
            user_id="test_user_prompt"
        )
        db.add(test_project)
        await db.commit()
        await db.refresh(test_project)
        project_id = test_project.id
        print(f"Mock Project created with ID: {project_id}")

        try:
            # 4. Assert listing returns defaults initially
            # We mimic list_agent_configs router logic
            result = await db.execute(
                select(AgentConfig).where(AgentConfig.project_id == project_id)
            )
            overrides = {ac.agent_role: ac for ac in result.scalars().all()}
            print(f"Initial DB overrides count: {len(overrides)}")
            assert len(overrides) == 0, "Expected 0 initial overrides"

            # 5. Insert overrides for Visionary CEO (french prompt, higher temp)
            print("Applying database override for visionary agent...")
            visionary_override = AgentConfig(
                project_id=project_id,
                agent_role="visionary",
                system_prompt="You are a French Visionary CEO. Begin everything with Bonjour!",
                model_override="meta/llama-3.1-70b-instruct",
                temperature=0.85,
                is_enabled=True
            )
            db.add(visionary_override)
            
            # Disable Marketing CEO entirely
            print("Disabling marketing agent in database...")
            marketing_disabled = AgentConfig(
                project_id=project_id,
                agent_role="marketing",
                is_enabled=False
            )
            db.add(marketing_disabled)
            await db.commit()

            # 6. Verify Intent Filtering (analyze_intent should skip marketing)
            print("\nTesting intent analysis filtering...")
            state: GraphState = {
                "messages": [type('Msg', (object,), {'content': 'Should we do GTM planning?'})],
                "project_id": project_id,
                "intent": "",
                "active_agents": [],
                "retrieved_context": "",
                "draft_responses": {},
                "critiques": {},
                "final_consensus": ""
            }
            
            # Run analyze_intent
            intent_result = await analyze_intent(state)
            print("Intent result active agents:", intent_result["active_agents"])
            assert "marketing" not in intent_result["active_agents"], "Marketing agent was NOT filtered out!"
            print("SUCCESS: marketing agent correctly skipped.")

            # 7. Verify Execute Agents override injection
            # Inject active_agents directly into state
            state["active_agents"] = ["visionary", "operations"]
            state["retrieved_context"] = "Company Name: Test Startup"
            
            # Mock the visionary.ainvoke call to check parameters
            original_ainvoke = AGENTS_MAP["visionary"].ainvoke
            captured_params = {}
            
            async def mock_ainvoke(user_query, context, system_prompt=None, model=None, temperature=None):
                captured_params["system_prompt"] = system_prompt
                captured_params["model"] = model
                captured_params["temperature"] = temperature
                return {"analysis": "Bonjour! C'est magnifique.", "risks": [], "recommendations": [], "confidence": 0.9}
                
            AGENTS_MAP["visionary"].ainvoke = mock_ainvoke

            try:
                print("\nExecuting agents to check dynamic override injection...")
                await execute_agents(state)
                
                print("Captured override params passed to visionary:")
                print(f"  system_prompt: {captured_params.get('system_prompt')!r}")
                print(f"  model: {captured_params.get('model')!r}")
                print(f"  temperature: {captured_params.get('temperature')!r}")
                
                assert captured_params["system_prompt"] == "You are a French Visionary CEO. Begin everything with Bonjour!", "System prompt override not passed!"
                assert captured_params["model"] == "meta/llama-3.1-70b-instruct", "Model override not passed!"
                assert captured_params["temperature"] == 0.85, "Temperature override not passed!"
                print("SUCCESS: Config overrides correctly injected into execution layers.")
                
            finally:
                # Restore original method
                AGENTS_MAP["visionary"].ainvoke = original_ainvoke

            # 8. Reset agent config
            print("\nResetting visionary agent settings...")
            result = await db.execute(
                select(AgentConfig)
                .where(AgentConfig.project_id == project_id)
                .where(AgentConfig.agent_role == "visionary")
            )
            cfg_to_delete = result.scalars().first()
            if cfg_to_delete:
                await db.delete(cfg_to_delete)
                await db.commit()
                
            # Query again to confirm deletion
            result = await db.execute(
                select(AgentConfig)
                .where(AgentConfig.project_id == project_id)
                .where(AgentConfig.agent_role == "visionary")
            )
            cfg_deleted = result.scalars().first()
            assert cfg_deleted is None, "Visionary config was NOT deleted!"
            print("SUCCESS: Reset defaults (deletion) verified.")

        finally:
            # Cleanup mock project
            print("\nCleaning up mock project...")
            await db.delete(test_project)
            await db.commit()
            print("Cleanup completed.")

if __name__ == "__main__":
    asyncio.run(test_agent_config_flow())
