"""
ExamAI - Gemini Service
Core grading engine using Gemini 3's native vision capabilities.
No OCR — sends PDF page images directly to Gemini for understanding.
"""

import json
import re
import time
import base64
import logging
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds, doubles each retry


def get_client():
    """Create and return a Gemini API client."""
    return genai.Client(api_key=GEMINI_API_KEY)


def analyze_answer_key(page_images: list[bytes]) -> dict:
    """
    Analyze the answer key PDF using Gemini's native vision.
    
    Sends all answer key pages as images to Gemini and extracts
    structured question-answer-marks data.
    
    Args:
        page_images: List of PNG image bytes for each page
    
    Returns:
        Dictionary with structured answer key data
    """
    client = get_client()

    # Build parts: instruction text + all page images
    parts = [
        types.Part.from_text(text="""You are an expert exam grading assistant. Analyze this answer key document carefully.

For EACH question in the answer key, extract:
1. The question number
2. The correct answer or key points expected
3. The maximum marks allocated for that question

Return your analysis as a JSON object with this exact structure:
{
    "total_questions": <number>,
    "total_marks": <number>,
    "questions": [
        {
            "question_number": "1",
            "question_text": "<brief description of what the question asks, if visible>",
            "expected_answer": "<the correct answer or key points>",
            "max_marks": <number>,
            "grading_criteria": "<how to evaluate - keywords, concepts, or exact match>"
        }
    ]
}

Be thorough. Read every page carefully. Include ALL questions you find.
Return ONLY the JSON object, no other text.""")
    ]

    # Add each page image
    for i, img_bytes in enumerate(page_images):
        parts.append(types.Part.from_text(text=f"\n--- Answer Key Page {i + 1} ---"))
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    return _call_gemini_with_retry(client, parts, temperature=0.1)


def grade_exam_sheet(page_images: list[bytes], answer_key_data: dict) -> dict:
    """
    Grade a handwritten exam sheet against the answer key using Gemini's vision.
    
    Sends exam sheet pages as images along with the structured answer key
    for Gemini to evaluate and assign marks.
    
    Args:
        page_images: List of PNG image bytes for each exam page
        answer_key_data: Structured answer key from analyze_answer_key()
    
    Returns:
        Dictionary with per-question grading results
    """
    client = get_client()

    # Format the answer key context
    answer_key_context = json.dumps(answer_key_data, indent=2)

    parts = [
        types.Part.from_text(text=f"""You are an expert exam grader. You must grade a handwritten exam sheet against the provided answer key.

## ANSWER KEY (Reference):
{answer_key_context}

## YOUR TASK:
Look at the handwritten exam sheet images below. For EACH question:
1. Read what the student has written (handwritten text, diagrams, equations, etc.)
2. Compare it against the expected answer from the answer key
3. Assign marks based on how well the student's answer matches
4. Provide brief reasoning for the marks given

## GRADING GUIDELINES:
- Award full marks if the answer is correct and complete
- Award partial marks for partially correct answers
- Award 0 marks for incorrect or missing answers
- Consider the meaning/intent, not just exact wording
- Be fair but accurate in your assessment

Return your grading as a JSON object with this exact structure:
{{
    "student_name": "<if visible on the sheet, otherwise 'Unknown'>",
    "total_marks_obtained": <number>,
    "total_marks_possible": {answer_key_data.get('total_marks', 0)},
    "percentage": <number>,
    "results": [
        {{
            "question_number": "1",
            "question_text": "<brief description>",
            "student_answer_summary": "<what the student wrote>",
            "expected_answer_summary": "<key points from answer key>",
            "max_marks": <number>,
            "marks_obtained": <number>,
            "reasoning": "<why this score was given>"
        }}
    ],
    "overall_feedback": "<general feedback for the student>"
}}

Grade ALL questions found in the answer key. If a question appears to be unanswered, give 0 marks.
Return ONLY the JSON object, no other text.""")
    ]

    # Add each exam page image
    for i, img_bytes in enumerate(page_images):
        parts.append(types.Part.from_text(text=f"\n--- Exam Sheet Page {i + 1} ---"))
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    return _call_gemini_with_retry(client, parts, temperature=0.2)


def _call_gemini_with_retry(client, parts: list, temperature: float = 0.1) -> dict:
    """
    Call Gemini with automatic retry logic for transient failures.
    Uses response_mime_type to enforce valid JSON output.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Gemini API call attempt {attempt}/{MAX_RETRIES}")
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=65536,
                    response_mime_type="application/json",  # Force valid JSON
                )
            )

            result = _parse_json(response.text)
            logger.info(f"Gemini API call succeeded on attempt {attempt}")
            return result

        except (json.JSONDecodeError, Exception) as e:
            last_error = e
            logger.warning(
                f"Attempt {attempt}/{MAX_RETRIES} failed: {type(e).__name__}: {e}"
            )
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_BASE ** attempt
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)

    raise RuntimeError(
        f"Gemini API failed after {MAX_RETRIES} attempts. Last error: {last_error}"
    )


def _parse_json(text: str) -> dict:
    """
    Robustly parse JSON from Gemini's response.
    Handles markdown code blocks, trailing commas, truncated output,
    control characters, and other common quirks.
    """
    if not text or not text.strip():
        raise json.JSONDecodeError("Empty response from Gemini", text or "", 0)

    text = text.strip()

    # ── Step 1: Remove markdown code block wrapping ──
    # Handle ```json ... ``` and ``` ... ``` patterns
    code_block = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()
    elif text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()

    # ── Step 2: Remove control characters (except whitespace) ──
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    # ── Step 3: Fix trailing commas before } or ] ──
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # ── Step 4: Try direct parse ──
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ── Step 5: Extract JSON object from surrounding text ──
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = match.group()
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # ── Step 6: Attempt to repair truncated JSON ──
    # If the response was cut off, we try to close open braces/brackets
    repaired = _repair_truncated_json(text)
    if repaired:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    # All strategies failed
    raise json.JSONDecodeError(
        f"Could not parse Gemini response as JSON. First 500 chars: {text[:500]}",
        text, 0
    )


def _repair_truncated_json(text: str) -> str | None:
    """
    Attempt to repair JSON that was truncated mid-output.
    Closes unclosed strings, arrays, and objects.
    """
    # Find the start of the JSON object
    start = text.find("{")
    if start == -1:
        return None

    fragment = text[start:]

    # Remove a trailing incomplete string value (truncated mid-string)
    # e.g., `"reasoning": "The student wrote` → remove this last bad pair
    fragment = re.sub(r',\s*"[^"]*"\s*:\s*"[^"]*$', '', fragment)
    # Also handle case where value string is completely missing
    fragment = re.sub(r',\s*"[^"]*"\s*:\s*$', '', fragment)

    # Fix trailing commas after cleanup
    fragment = re.sub(r",\s*([}\]])", r"\1", fragment)
    # Remove trailing comma at end of string
    fragment = re.sub(r",\s*$", "", fragment)

    # Count unclosed brackets and braces
    open_braces = fragment.count("{") - fragment.count("}")
    open_brackets = fragment.count("[") - fragment.count("]")

    # Close them in reverse order (brackets first, then braces)
    fragment += "]" * max(0, open_brackets)
    fragment += "}" * max(0, open_braces)

    return fragment
