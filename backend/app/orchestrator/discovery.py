# backend/app/orchestrator/discovery.py
"""
Business Discovery Agent — Interviews the founder to build a CompanyBlueprint.
Uses an iterative Q&A loop until confidence exceeds 90%.
"""
import json
from typing import Dict, Any, List, Optional

from app.services.nvidia import nvidia_service
from app.db.session import AsyncSessionLocal
from app.db.models import CompanyBlueprint, Project
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

# All fields that contribute to blueprint completeness
BLUEPRINT_FIELDS = [
    ("company_name", "What is your company or startup name?"),
    ("industry", "What industry are you in?"),
    ("business_model", "What is your business model? (e.g., SaaS, marketplace, agency, hardware)"),
    ("target_audience", "Who is your target audience? Be specific about demographics, company size, or persona."),
    ("value_proposition", "What is your unique value proposition? What problem do you solve?"),
    ("products_services", "What products or services do you offer? List them with a brief description."),
    ("competitors", "Who are your main competitors? What differentiates you from them?"),
    ("revenue_model", "How do you make money? Describe your revenue streams."),
    ("pricing", "What is your pricing strategy?"),
    ("team_size", "What is your current team size and key roles?"),
    ("budget", "What is your approximate monthly/annual budget or runway?"),
    ("geography", "Where are you based and what markets do you serve?"),
    ("tech_stack", "What technologies do you use? (programming languages, frameworks, cloud, etc.)"),
    ("marketing_strategy", "What is your current marketing strategy?"),
    ("sales_strategy", "What is your sales approach? (self-serve, outbound, partnerships, etc.)"),
    ("current_goals", "What are your top 3 goals for the next 6 months?"),
    ("current_problems", "What are the biggest challenges you are facing right now?"),
    ("product_roadmap", "What features or milestones are on your product roadmap?"),
    ("brand_voice", "How would you describe your brand voice and tone?"),
    ("growth_stage", "What stage is your company at? (idea, MVP, growth, scale)"),
]

FIELD_NAMES = [f[0] for f in BLUEPRINT_FIELDS]
FIELD_QUESTIONS = {f[0]: f[1] for f in BLUEPRINT_FIELDS}


def _get_field_confidence(blueprint: CompanyBlueprint, field_name: str) -> float:
    """Helper to get confidence for a field, defaulting to 100 if filled but no confidence recorded."""
    confidences = blueprint.field_confidences or {}
    if field_name in confidences:
        return float(confidences[field_name])
    
    val = getattr(blueprint, field_name, None)
    if val is not None:
        if isinstance(val, str) and val.strip():
            return 100.0
        elif isinstance(val, list) and len(val) > 0:
            return 100.0
        elif isinstance(val, dict) and len(val) > 0:
            return 100.0
    return 0.0


def calculate_confidence(blueprint: CompanyBlueprint) -> float:
    """Calculate discovery completeness as a 0.0-1.0 confidence score based on completed_fields / required_fields."""
    completed = 0
    total = len(BLUEPRINT_FIELDS)

    for field_name, _ in BLUEPRINT_FIELDS:
        if _get_field_confidence(blueprint, field_name) >= 80.0:
            completed += 1
    
    return completed / total if total > 0 else 0.0


def get_missing_fields(blueprint: CompanyBlueprint) -> List[str]:
    """Return list of field names that have confidence < 80%."""
    missing = []
    for field_name, _ in BLUEPRINT_FIELDS:
        if _get_field_confidence(blueprint, field_name) < 80.0:
            missing.append(field_name)
    return missing


async def generate_discovery_questions(
    blueprint: CompanyBlueprint,
    conversation_history: List[Dict[str, str]],
    max_questions: int = 3
) -> str:
    """
    Uses LLM to generate smart, contextual follow-up questions based on what's 
    already known and what's missing.
    """
    missing = get_missing_fields(blueprint)
    if not missing:
        return "I have a comprehensive understanding of your business now. Let me finalize your Company Blueprint."

    # Build context of what we already know
    known_facts = []
    for field_name, _ in BLUEPRINT_FIELDS:
        val = getattr(blueprint, field_name, None)
        conf = _get_field_confidence(blueprint, field_name)
        if val and ((isinstance(val, str) and val.strip()) or 
                    (isinstance(val, (list, dict)) and len(val) > 0)):
            known_facts.append(f"- {field_name}: {val} (Confidence: {conf}%)")

    known_context = "\n".join(known_facts) if known_facts else "Nothing known yet."
    missing_fields_text = ", ".join(missing[:max_questions])

    prompt = (
        "You are an experienced business consultant acting as a Discovery Agent.\n"
        "Your goal is to understand the founder's business deeply through a natural, adaptive conversation.\n\n"
        f"What we currently know (and our confidence in the data):\n{known_context}\n\n"
        f"Fields that still need more details (confidence < 80%): {missing_fields_text}\n\n"
        "INSTRUCTIONS:\n"
        "1. Ask follow-up questions that explicitly narrow down uncertainty based on the known facts. Do NOT repeat the exact same generic question.\n"
        "2. If the founder gave a detailed answer previously, ask fewer questions.\n"
        "3. If the founder gave a very short answer, ask guided questions (e.g. 'You mentioned businesses. Are they mainly schools, hospitals, or retailers?').\n"
        f"4. Generate up to {min(max_questions, len(missing))} conversational questions.\n"
        "5. Be warm, professional, and flow naturally like a real consultant.\n"
        "Format: Return ONLY a JSON array of question strings.\n"
    )

    messages = [{"role": "system", "content": prompt}]
    # Add conversation history for context continuity
    for msg in conversation_history[-6:]:  # Last 6 messages
        messages.append(msg)

    try:
        response = await nvidia_service.chat_completion(messages, temperature=0.4, max_tokens=512)
        clean = response.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            clean = "\n".join(lines).strip()
        
        questions = json.loads(clean)
        if isinstance(questions, list):
            return "\n\n".join(f"**{i+1}.** {q}" for i, q in enumerate(questions))
    except Exception:
        pass

    # Fallback: use static questions for missing fields
    fallback_qs = [FIELD_QUESTIONS[f] for f in missing[:max_questions]]
    return "\n\n".join(f"**{i+1}.** {q}" for i, q in enumerate(fallback_qs))


async def process_discovery_response(
    project_id: str,
    founder_response: str,
    conversation_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Takes a founder's natural language response and uses LLM to extract
    structured data to fill blueprint fields.
    """
    async with AsyncSessionLocal() as db:
        # Load blueprint
        result = await db.execute(
            select(CompanyBlueprint).where(CompanyBlueprint.project_id == project_id)
        )
        blueprint = result.scalars().first()
        if not blueprint:
            blueprint = CompanyBlueprint(project_id=project_id)
            db.add(blueprint)
            await db.commit()
            await db.refresh(blueprint)

        missing = get_missing_fields(blueprint)
        if not missing:
            return {
                "status": "complete",
                "confidence": 1.0,
                "message": "Discovery is already complete!",
                "next_questions": ""
            }

        # Use LLM to extract structured info from the founder's response
        extraction_prompt = (
            "You are an AI assistant that extracts business information from a founder's response.\n"
            f"The following fields are currently incomplete or missing: {', '.join(missing[:8])}\n\n"
            "From the founder's response below, extract any relevant information across ALL fields, even if not explicitly listed above.\n"
            "The founder might use poor English, Hinglish, spelling mistakes, very short answers, or long paragraphs. Extract intelligently and infer when reasonably possible.\n"
            "IMPORTANT: One answer may contain multiple fields. Extract and update all fields simultaneously.\n"
            "Return ONLY a JSON object where keys are field names and values match this structure:\n"
            "{\n"
            '  "field_name": {\n'
            '    "value": <extracted_data>,\n'
            '    "confidence": <integer from 0 to 100 based on certainty>\n'
            '  }\n'
            "}\n\n"
            "For list fields (products_services, competitors, current_goals, current_problems, product_roadmap), 'value' should be an array.\n"
            "For dict fields (pricing), 'value' should be an object.\n"
            "For string fields, 'value' should be a string.\n"
            "Only include fields you can extract. Skip uncertain ones entirely.\n\n"
            f"Founder's response: {founder_response}\n"
        )

        messages = [{"role": "system", "content": extraction_prompt}]
        
        extracted = {}
        try:
            response = await nvidia_service.chat_completion(messages, temperature=0.1, max_tokens=1024)
            clean = response.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                clean = "\n".join(lines).strip()
            extracted = json.loads(clean)
        except Exception:
            # If extraction fails, store the raw response in the most likely missing field
            if missing:
                extracted = {missing[0]: {"value": founder_response.strip(), "confidence": 50}}

        # Apply extracted data to blueprint
        updated_fields = []
        confidences = blueprint.field_confidences or {}
        
        for field_name, field_data in extracted.items():
            if field_name in FIELD_NAMES and isinstance(field_data, dict) and "value" in field_data:
                new_val = field_data["value"]
                new_conf = field_data.get("confidence", 50)
                
                # Update if new confidence is higher or field is empty
                current_conf = _get_field_confidence(blueprint, field_name)
                if new_conf > current_conf or current_conf == 0:
                    setattr(blueprint, field_name, new_val)
                    confidences[field_name] = new_conf
                    updated_fields.append(field_name)
                    if isinstance(new_val, (list, dict)):
                        flag_modified(blueprint, field_name)
                        
        blueprint.field_confidences = confidences
        flag_modified(blueprint, "field_confidences")

        # Recalculate confidence
        confidence = calculate_confidence(blueprint)
        blueprint.discovery_confidence = confidence

        await db.commit()
        await db.refresh(blueprint)

        # Update project discovery status
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        if project and confidence >= 0.9:
            project.discovery_completed = True
            await db.commit()

        # Generate next questions
        next_questions = ""
        if confidence < 0.9:
            next_questions = await generate_discovery_questions(blueprint, conversation_history)

        if updated_fields:
            from app.services.memory_hooks import on_discovery_updated
            await on_discovery_updated(project_id, updated_fields, confidence)

        return {
            "status": "complete" if confidence >= 0.9 else "in_progress",
            "confidence": confidence,
            "updated_fields": updated_fields,
            "message": f"Got it! Updated: {', '.join(updated_fields)}." if updated_fields else "I couldn't extract specific data from that. Could you be more specific?",
            "next_questions": next_questions,
        }
