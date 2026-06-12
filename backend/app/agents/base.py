import json
from typing import Any, Dict
from app.services.nvidia import nvidia_service

class BaseExecutiveAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

    async def ainvoke(
        self,
        user_query: str,
        context: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None
    ) -> Dict[str, Any]:
        format_instructions = (
            "\n\nCRITICAL REQUIREMENT: You MUST respond ONLY with a raw, valid JSON object matching the following structure. "
            "Do NOT include any markdown formatting, backticks (like ```json), or explanatory text outside the JSON block. "
            "JSON Schema:\n"
            "{\n"
            '  "analysis": "Detailed analysis based on your expertise (string)",\n'
            '  "risks": ["Potential risk 1", "Potential risk 2" (array of strings)],\n'
            '  "recommendations": ["Actionable recommendation 1", "Actionable recommendation 2" (array of strings)],\n'
            '  "confidence": 0.85 (float score between 0.0 and 1.0)\n'
            "}"
        )
        
        prompt_to_use = system_prompt if system_prompt else self.system_prompt
        temp_to_use = temperature if temperature is not None else 0.2
        
        messages = [
            {"role": "system", "content": f"{prompt_to_use}\n\nProject Context:\n{context}{format_instructions}"},
            {"role": "user", "content": user_query}
        ]
        
        response_text = await nvidia_service.chat_completion(
            messages,
            temperature=temp_to_use,
            model=model
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
            
        try:
            result = json.loads(clean_text)
            return {
                "analysis": str(result.get("analysis", "")),
                "risks": list(result.get("risks", [])),
                "recommendations": list(result.get("recommendations", [])),
                "confidence": float(result.get("confidence", 0.8))
            }
        except Exception:
            # Fallback if JSON parsing fails
            return {
                "analysis": response_text,
                "risks": ["Failed to extract structured risks from output."],
                "recommendations": ["Refer to freeform analysis for detailed mitigations."],
                "confidence": 0.5
            }
