# backend/app/services/task_engine.py
import json
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import Task, AgentDefinition
from app.services.context_builder import UnifiedContextBuilder
from app.services.nvidia import nvidia_service
from app.services.integrations import integration_manager

async def execute_agent_task(task: Task) -> Dict[str, Any]:
    """
    Executes a task using the specified agent role.
    This bypasses the full langgraph for single-task executions.
    Supports dynamic tools injection and mock execution.
    """
    async with AsyncSessionLocal() as db:
        # Get agent definition
        result = await db.execute(select(AgentDefinition).where(AgentDefinition.role == task.assigned_agent))
        agent_def = result.scalars().first()
        
        if not agent_def:
            raise ValueError(f"Agent definition not found for role: {task.assigned_agent}")
            
        # Unified company memory
        rag_query = task.description or task.title
        context = await UnifiedContextBuilder.build(
            db, task.project_id, rag_query=rag_query, include_rag=True
        )
        blueprint_ctx = context.prompt_text
            
        # Get active integration providers and their tools
        active_providers = await integration_manager.get_active_providers(task.project_id, db)
        available_tools = []
        for provider in active_providers:
            available_tools.extend(provider.get_tools())
            
    # Build dynamic prompt instructions based on agent's output schema or fallback
    tool_instructions = ""
    if available_tools:
        tool_instructions = (
            "\n\nEXTERNAL TOOLS AVAILABLE:\n"
            "You can execute actions on connected external tools. To call a tool, add a 'tool_calls' field to your JSON output.\n"
            f"Tools Schema:\n{json.dumps(available_tools, indent=2)}\n\n"
            "Example usage in your JSON response:\n"
            "{\n"
            "  ... (your regular analysis fields) ...,\n"
            "  \"tool_calls\": [\n"
            "    {\n"
            "      \"name\": \"tool_name\",\n"
            "      \"arguments\": {\"param_name\": \"value\"}\n"
            "    }\n"
            "  ]\n"
            "}"
        )

    schema_instructions = ""
    if agent_def.output_schema:
        # Merge or document tool_calls in output_schema
        merged_schema = {**agent_def.output_schema}
        merged_schema["tool_calls"] = "List of tool calls (optional)"
        schema_instructions = (
            "\n\nCRITICAL REQUIREMENT: You MUST respond ONLY with a raw, valid JSON object matching the following structure. "
            "Do NOT include any markdown formatting, backticks (like ```json), or explanatory text outside the JSON block. "
            f"JSON Schema:\n{json.dumps(merged_schema, indent=2)}"
        )
    else:
        schema_instructions = (
            "\n\nCRITICAL REQUIREMENT: You MUST respond ONLY with a raw, valid JSON object containing an 'output' field with your detailed markdown response. "
            "Do NOT include any markdown formatting, backticks (like ```json), or explanatory text outside the JSON block. "
            "JSON Schema:\n{\n  \"output\": \"Your full markdown response here\",\n  \"tool_calls\": []\n}"
        )

    task_context = json.dumps(task.input_context, indent=2) if task.input_context else "No specific task context provided."

    prompt = (
        f"{agent_def.system_prompt}\n\n"
        f"Company Blueprint Context:\n{blueprint_ctx}\n\n"
        f"Task Description:\n{task.description}\n\n"
        f"Input Context:\n{task_context}"
        f"{tool_instructions}"
        f"{schema_instructions}"
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Please execute the task: {task.title}"}
    ]

    try:
        response_text = await nvidia_service.chat_completion(
            messages,
            temperature=0.2,
            max_tokens=2048
        )
        
        # Clean potential markdown block wrappers
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()
            
        result = json.loads(clean_text)
        
        # Execute tool calls if any are requested
        tool_results = []
        if "tool_calls" in result and isinstance(result["tool_calls"], list):
            async with AsyncSessionLocal() as db:
                for tc in result["tool_calls"]:
                    tool_name = tc.get("name")
                    args = tc.get("arguments", {})
                    try:
                        t_res = await integration_manager.execute_tool_call(task.project_id, tool_name, args, db)
                        tool_results.append({
                            "tool_name": tool_name,
                            "arguments": args,
                            "result": t_res
                        })
                    except Exception as te:
                        tool_results.append({
                            "tool_name": tool_name,
                            "arguments": args,
                            "error": str(te)
                        })
            result["tool_results"] = tool_results
            
        return result
        
    except Exception as e:
        # Fallback if execution or JSON parsing fails
        return {
            "error": "Failed to execute task or parse output.",
            "details": str(e),
            "raw_output": response_text if 'response_text' in locals() else None
        }

