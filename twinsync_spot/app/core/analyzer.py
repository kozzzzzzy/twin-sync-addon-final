"""Spot analyzer using Gemini Vision API."""
import json
import os
import re
import time
import base64
from typing import Optional

import aiohttp

from app.core.models import CheckResult, SpotMemory
from app.core.voices import get_voice_prompt
from app.core.memory import MemoryEngine


class SpotAnalyzer:
    """Analyzes spots using Gemini Vision API."""
    
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.memory_engine = MemoryEngine()
    
    async def analyze(
        self,
        image_bytes: bytes,
        spot_name: str,
        definition: str,
        voice: str = "supportive",
        custom_voice_prompt: str = None,
        memory: SpotMemory = None,
    ) -> CheckResult:
        """Analyze a spot image."""
        if not self.api_key:
            return CheckResult(
                status="error",
                error_message="Gemini API key not configured"
            )
        
        start_time = time.time()
        
        try:
            # Build prompt
            voice_prompt = get_voice_prompt(voice, custom_voice_prompt)
            memory_context = self.memory_engine.build_memory_context(memory) if memory else "First check."
            prompt = self._build_prompt(spot_name, definition, voice_prompt, memory_context)
            
            # Encode image
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_b64
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 1024,
                    }
                }
                
                url = f"{self.GEMINI_API_URL}?key={self.api_key}"
                
                async with session.post(url, json=payload) as response:
                    elapsed = time.time() - start_time
                    
                    if response.status == 429:
                        return CheckResult(
                            status="error",
                            error_message="API quota exceeded. Please try again later.",
                            api_response_time=elapsed
                        )
                    
                    if response.status != 200:
                        text = await response.text()
                        return CheckResult(
                            status="error",
                            error_message=f"API error: {response.status} - {text[:200]}",
                            api_response_time=elapsed
                        )
                    
                    data = await response.json()
            
            # Parse response
            result = self._parse_response(data)
            result.api_response_time = elapsed
            
            # Enrich with recurring info from memory
            if memory and memory.patterns.recurring_items:
                result.to_sort = self.memory_engine.enrich_items_with_recurring(
                    result.to_sort, memory.patterns.recurring_items
                )
            
            return result
            
        except aiohttp.ClientError as e:
            return CheckResult(
                status="error",
                error_message=f"Network error: {str(e)}",
                api_response_time=time.time() - start_time
            )
        except Exception as e:
            return CheckResult(
                status="error",
                error_message=f"Unexpected error: {str(e)}",
                api_response_time=time.time() - start_time
            )
    
    def _build_prompt(self, spot_name: str, definition: str, voice_prompt: str, memory_context: str) -> str:
        """Build the analysis prompt."""
        return f'''You are checking if "{spot_name}" matches its Ready State.

THE USER'S DEFINITION:
{definition}

HISTORY:
{memory_context}

YOUR VOICE:
{voice_prompt}

TASK:
1. List what's "To sort" - things that don't match the definition
2. List what's "Looking good" - things that do match the definition
3. Brief notes in your voice
4. Mention patterns from history if relevant

RULES:
- Be SPECIFIC. "Coffee mug on left side of desk" not "items out of place"
- Reference user's own words from their definition
- Reference history if relevant
- NO generic phrases. NO clichés. NO "Let's tidy up!"
- NEVER say "AI" or mention being an AI
- Keep notes to a few sentences max
- Do NOT include "recurring" field - that will be calculated separately

RETURN ONLY VALID JSON (no markdown, no backticks):
{{
    "status": "sorted" or "needs_attention",
    "to_sort": [
        {{"item": "coffee mug", "location": "left of desk"}}
    ],
    "looking_good": ["laptop on stand", "blinds open"],
    "notes": {{
        "main": "Your observation in your voice",
        "pattern": "Any pattern noticed or null",
        "encouragement": "If appropriate or null"
    }}
}}'''
    
    def _parse_response(self, data: dict) -> CheckResult:
        """Parse Gemini API response."""
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                return CheckResult(status="error", error_message="No response from API")
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                return CheckResult(status="error", error_message="Empty response from API")
            
            text = parts[0].get("text", "")
            
            # Clean up markdown if present
            text = text.strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            
            # Parse JSON
            result_data = json.loads(text)
            
            # Validate and extract
            status = result_data.get("status", "needs_attention")
            if status not in ("sorted", "needs_attention"):
                status = "needs_attention"
            
            to_sort = result_data.get("to_sort", [])
            looking_good = result_data.get("looking_good", [])
            notes = result_data.get("notes", {})
            
            # Remove any "recurring" field from AI response (we calculate it ourselves)
            to_sort = self._validate_to_sort(to_sort)
            
            return CheckResult(
                status=status,
                to_sort=to_sort,
                looking_good=looking_good,
                notes=notes if isinstance(notes, dict) else {"main": str(notes)}
            )
            
        except json.JSONDecodeError as e:
            return CheckResult(
                status="error",
                error_message=f"Failed to parse API response: {str(e)}"
            )
    
    def _validate_to_sort(self, items: list) -> list:
        """Validate and clean to_sort items."""
        cleaned = []
        for item in items:
            if isinstance(item, dict):
                # Remove recurring field - we calculate it ourselves
                cleaned_item = {
                    "item": item.get("item", "Unknown item"),
                    "location": item.get("location")
                }
                cleaned.append(cleaned_item)
            elif isinstance(item, str):
                cleaned.append({"item": item})
        return cleaned
    
    async def validate_api_key(self) -> bool:
        """Validate that the API key works."""
        if not self.api_key:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
                async with session.get(url) as response:
                    return response.status == 200
        except Exception:
            return False
