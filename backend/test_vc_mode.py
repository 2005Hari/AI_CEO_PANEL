# backend/test_vc_mode.py
import asyncio
import os
import sys
import json
from sqlalchemy import select

# Add current file's directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.session import AsyncSessionLocal, sync_engine
from app.db.models import Base, Project, AgentConfig
from app.agents.instances import AGENTS_MAP
from app.agents.prompts import (
    ANGEL_INVESTOR_PROMPT,
    SAAS_VC_PROMPT,
    DEEP_TECH_VC_PROMPT,
    GROWTH_VC_PROMPT,
    DEVILS_ADVOCATE_PROMPT,
    VC_JUDGE_PROMPT
)
from app.orchestrator.state import GraphState
from app.orchestrator.nodes import analyze_intent, execute_agents, execute_critic, synthesize_consensus
from app.orchestrator.graph import orchestrator

async def test_vc_mode_flow():
    print("Starting VC Pitch Sandbox & VC Simulator Tests...")
    print("-----------------------------------------------")

    # 1. Initialize Tables
    print("Initializing Database tables...")
    Base.metadata.create_all(bind=sync_engine)

    # 2. Setup Async Session
    async with AsyncSessionLocal() as db:
        # 3. Create a test Project
        print("Creating mock project for VC simulation...")
        test_project = Project(
            name="VC Pitch Test Startup",
            core_context={
                "value_proposition": "An AI platform for automated veterinary diagnostics.",
                "target_audience": "Veterinary clinics",
                "tech_stack": "FastAPI, Next.js, PyTorch",
                "business_model": "SaaS per diagnostic run"
            },
            user_id="test_user_vc"
        )
        db.add(test_project)
        await db.commit()
        await db.refresh(test_project)
        project_id = test_project.id
        print(f"Mock Project created with ID: {project_id}")

        try:
            # Test 1: analyze_intent in pitch mode defaults to all active agents
            print("\n[Test 1] Testing intent analysis in pitch mode...")
            state_pitch: GraphState = {
                "user_id": "test_user_vc",
                "project_id": project_id,
                "messages": [type('Msg', (object,), {'content': 'We charge $150/mo. CAC is $80, and churn is 1%.'})],
                "intent": "",
                "active_agents": [],
                "retrieved_context": "",
                "draft_responses": {},
                "critiques": {},
                "final_consensus": "",
                "mode": "pitch"
            }
            intent_result = await analyze_intent(state_pitch)
            print("Intent analyzer active agents in pitch mode:", intent_result["active_agents"])
            assert set(intent_result["active_agents"]) == {"visionary", "operations", "marketing", "finance", "risk"}, \
                "Expected all 5 agents to participate in pitch mode!"
            print("SUCCESS: Intent analyzer correctly activated all VCs.")

            # Test 2: disabled agent configuration is respected in pitch mode
            print("\n[Test 2] Testing agent configuration disablement in pitch mode...")
            marketing_disabled = AgentConfig(
                project_id=project_id,
                agent_role="marketing",
                is_enabled=False
            )
            db.add(marketing_disabled)
            await db.commit()

            intent_result_disabled = await analyze_intent(state_pitch)
            print("Active agents after disabling marketing:", intent_result_disabled["active_agents"])
            assert "marketing" not in intent_result_disabled["active_agents"], "Marketing VC was not disabled!"
            assert set(intent_result_disabled["active_agents"]) == {"visionary", "operations", "finance", "risk"}, \
                "Expected only enabled agents to participate!"
            print("SUCCESS: Config-disabled VC correctly omitted in pitch mode.")

            # Clean up the disablement override for subsequent tests
            await db.delete(marketing_disabled)
            await db.commit()

            # Test 3: verify prompts are correctly selected for VCs in execute_agents and execute_critic
            print("\n[Test 3] Testing correct prompt loading in execution nodes...")
            state_exec: GraphState = {
                "user_id": "test_user_vc",
                "project_id": project_id,
                "messages": [type('Msg', (object,), {'content': 'We charge $150/mo. CAC is $80, and churn is 1%.'})],
                "intent": "Evaluate pitch",
                "active_agents": ["visionary", "operations", "marketing", "finance", "risk"],
                "retrieved_context": "Company: VetAI",
                "draft_responses": {},
                "critiques": {},
                "final_consensus": "",
                "mode": "pitch"
            }

            # We mock the invoke methods to assert prompt selection
            captured_prompts = {}
            original_invokes = {}

            for role in ["visionary", "operations", "marketing", "finance", "risk"]:
                agent = AGENTS_MAP[role]
                original_invokes[role] = agent.ainvoke
                
                # Setup a closed-over mock function
                def make_mock(r=role):
                    async def mock_invoke(user_query, context, system_prompt=None, model=None, temperature=None):
                        captured_prompts[r] = system_prompt
                        return {
                            "analysis": f"Mock {r} evaluation.",
                            "risks": [f"Mock risk {r}"],
                            "recommendations": [f"Mock recommendation {r}"],
                            "confidence": 0.8
                        }
                    return mock_invoke
                
                agent.ainvoke = make_mock()

            try:
                # Run execute_agents
                exec_result = await execute_agents(state_exec)
                state_exec["draft_responses"] = exec_result["draft_responses"]
                
                # Run execute_critic
                critic_result = await execute_critic(state_exec)
                state_exec["critiques"] = critic_result["critiques"]

                print("Captured prompts for VCs during execute:")
                for role, prompt in captured_prompts.items():
                    print(f"  {role}: {prompt[:40].strip()}...")

                # Assert correct VC prompts are used
                assert captured_prompts["visionary"] == ANGEL_INVESTOR_PROMPT, "Visionary did not use ANGEL_INVESTOR_PROMPT!"
                assert captured_prompts["operations"] == SAAS_VC_PROMPT, "Operations did not use SAAS_VC_PROMPT!"
                assert captured_prompts["marketing"] == DEEP_TECH_VC_PROMPT, "Marketing did not use DEEP_TECH_VC_PROMPT!"
                assert captured_prompts["finance"] == GROWTH_VC_PROMPT, "Finance did not use GROWTH_VC_PROMPT!"
                assert captured_prompts["risk"] == DEVILS_ADVOCATE_PROMPT, "Risk did not use DEVILS_ADVOCATE_PROMPT!"
                
                print("SUCCESS: Execution node correctly mapped early-stage and vertical-specific VC prompts.")

            finally:
                # Restore original invoke methods
                for role, orig in original_invokes.items():
                    AGENTS_MAP[role].ainvoke = orig

            # Test 4: synthesize_consensus uses VC_JUDGE_PROMPT in pitch mode
            print("\n[Test 4] Testing Judge prompt synthesis in pitch mode...")
            original_chat_completion = settings.NVIDIA_API_KEY
            captured_judge_prompt = None

            from app.services.nvidia import nvidia_service
            original_completion_method = nvidia_service.chat_completion

            async def mock_chat_completion(messages, temperature=0.3):
                nonlocal captured_judge_prompt
                captured_judge_prompt = messages[0]["content"]
                return "Mock Final Investment Report Consensus"

            nvidia_service.chat_completion = mock_chat_completion

            try:
                state_synthesis: GraphState = {
                    "user_id": "test_user_vc",
                    "project_id": project_id,
                    "messages": [type('Msg', (object,), {'content': 'Pitch message'})],
                    "intent": "Evaluate pitch",
                    "active_agents": ["visionary", "operations", "marketing", "finance", "risk"],
                    "retrieved_context": "Company: VetAI",
                    "draft_responses": {"visionary": {}, "operations": {}, "marketing": {}, "finance": {}},
                    "critiques": {"risk": {}},
                    "final_consensus": "",
                    "mode": "pitch"
                }

                synthesis_result = await synthesize_consensus(state_synthesis)
                assert synthesis_result["final_consensus"] == "Mock Final Investment Report Consensus", \
                    "Consensus output mismatch!"
                assert VC_JUDGE_PROMPT in captured_judge_prompt, "Judge synthesis did not load VC_JUDGE_PROMPT!"
                print("SUCCESS: Synthesizer correctly loaded Lead Investment Partner consensus template.")

            finally:
                nvidia_service.chat_completion = original_completion_method

            # Test 5: End-to-end Graph invocation check (mocked LLM calls)
            print("\n[Test 5] Running mock end-to-end Graph run...")
            
            # Mock nvidia_service for intent, agents, and consensus
            nvidia_service.chat_completion = mock_chat_completion
            
            # Setup mocks for agents again
            for role in ["visionary", "operations", "marketing", "finance", "risk"]:
                agent = AGENTS_MAP[role]
                def make_mock_e2e(r=role):
                    async def mock_invoke(user_query, context, system_prompt=None, model=None, temperature=None):
                        return {
                            "analysis": f"Mock E2E {r} analysis.",
                            "risks": [f"Risk {r}"],
                            "recommendations": [f"Mitigation {r}"],
                            "confidence": 0.85
                        }
                    return mock_invoke
                agent.ainvoke = make_mock_e2e()

            try:
                # Build the initial state
                from langchain_core.messages import HumanMessage
                initial_state: GraphState = {
                    "user_id": "test_user_vc",
                    "project_id": project_id,
                    "messages": [HumanMessage(content="We charge $150/mo. CAC is $80, and churn is 1%.")],
                    "intent": "",
                    "active_agents": [],
                    "retrieved_context": "",
                    "draft_responses": {},
                    "critiques": {},
                    "final_consensus": "",
                    "mode": "pitch"
                }

                outputs = []
                async for output in orchestrator.astream(initial_state):
                    outputs.append(output)

                print("Orchestration pipeline execution steps completed successfully.")
                assert len(outputs) > 0, "No outputs generated from orchestrator execution!"
                
                # Check final node update
                final_node_update = outputs[-1]
                assert "synthesizer" in final_node_update, "Synthesizer did not finish as the final node!"
                print("SUCCESS: End-to-end Graph integration test completed successfully.")

            finally:
                # Restore original invoke methods
                for role, orig in original_invokes.items():
                    AGENTS_MAP[role].ainvoke = orig
                nvidia_service.chat_completion = original_completion_method

        finally:
            print("\nCleaning up mock project...")
            await db.delete(test_project)
            await db.commit()
            print("Cleanup completed.")

if __name__ == "__main__":
    asyncio.run(test_vc_mode_flow())
