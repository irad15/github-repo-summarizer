import os
import json
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

async def generate_summary(repo_name: str, file_tree: str, file_contents: str) -> dict:
    """
    Send the parsed repository data to LLM and request a structured JSON response.
    
    This function takes the condensed directory tree and the raw text of the
    priority files, injects them into a strict system prompt, and uses the
    OpenAI async SDK with `response_format={"type": "json_object"}` to guarantee
    the output exactly matches the requested 'summary', 'technologies', and 'structure' keys.
    """
    
    # Initialize the client. It automatically picks up OPENAI_API_KEY from environment variables.
    try:
        client = AsyncOpenAI()
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        raise ValueError("OpenAI API key missing or invalid.")

    # Prevent massive payloads from crashing the API context window 
    # (gpt-4o-mini has 128k context. 300k chars is safe for gpt-4o-mini).
    max_chars = 300_000
    if len(file_contents) > max_chars:
        logger.warning(f"File contents exceed {max_chars} chars. Truncating.")
        file_contents = file_contents[:max_chars] + "\n...[CONTENT TRUNCATED]..."

    system_prompt = f"""You are an expert software engineer analyzing the {repo_name} repository.
I will provide you with the directory tree structure of the project, and the raw text contents of its most important files.

Your task is to analyze this context and return a JSON object with exactly the following structure:
{{
  "summary": "A human-readable description of what the project does",
  "technologies": ["List", "of", "main", "technologies", "languages", "and", "frameworks"],
  "structure": "Brief description of the project structure"
}}

Respond ONLY with valid JSON."""

    user_prompt = f"""Directory Tree:
{file_tree}

Key File Contents:
{file_contents}
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")
            
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise RuntimeError(f"Failed to generate summary: {str(e)}")
