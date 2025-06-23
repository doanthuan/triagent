import json
import re
from typing import Any, List, Optional

from triagent.agents.tx_verifier.entity import FactVerifierResponse
from triagent.logging import logger


def fix_unescaped_quotes_in_json(json_str: str) -> str:
    """
    Fix unescaped quotes in JSON string values to make valid JSON.

    This function handles quotes within string values that would otherwise
    break JSON parsing, while preserving the JSON structure.

    Args:
        json_str: Raw JSON string that may contain unescaped quotes in values

    Returns:
        JSON string with properly escaped quotes in values

    Raises:
        ValueError: If the resulting JSON is still invalid after fixing
    """

    # First, try to parse as-is in case it's already valid
    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass

    # Remove markdown code blocks if present
    json_content = _extract_json_from_markdown(json_str)

    # Try different fixing strategies
    strategies = [
        _fix_quotes_with_state_machine,
        _fix_quotes_with_regex,
        _fix_quotes_aggressive,
    ]

    for strategy in strategies:
        try:
            fixed_content = strategy(json_content)
            # Validate that the fix worked
            json.loads(fixed_content)
            return fixed_content
        except (json.JSONDecodeError, Exception):
            continue

    # If all strategies fail, raise an error
    raise ValueError("Unable to fix JSON string - too malformed")


def _extract_json_from_markdown(content: str) -> str:
    """Extract JSON content from markdown code blocks."""
    # Remove markdown code blocks
    json_pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(json_pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1).strip()

    # If no code blocks, try to find JSON-like content
    start_idx = content.find("{")
    end_idx = content.rfind("}")

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return content[start_idx : end_idx + 1]

    return content


def _fix_quotes_with_state_machine(json_str: str) -> str:
    """
    Fix quotes using a state machine approach - most accurate method.

    This method tracks whether we're inside a string, and whether that
    string is a key or value, then properly escapes quotes in values.
    """
    result = []
    i = 0
    in_string = False
    in_key = True  # Start assuming we're in a key context
    escape_next = False
    brace_depth = 0

    while i < len(json_str):
        char = json_str[i]

        if escape_next:
            result.append(char)
            escape_next = False
        elif char == "\\":
            result.append(char)
            escape_next = True
        elif char == '"':
            if not in_string:
                # Starting a string
                in_string = True
                result.append(char)
            else:
                # Check if this quote should end the string or be escaped
                if in_key:
                    # In a key - this quote should end the string
                    in_string = False
                    in_key = False  # After a key, we expect a value next
                    result.append(char)
                else:
                    # In a value - check if this should end the string
                    # Look ahead to see what comes next
                    next_non_space = _get_next_non_space_char(json_str, i + 1)
                    if next_non_space in [",", "}", "]", None]:
                        # This quote should end the string
                        in_string = False
                        result.append(char)
                    else:
                        # This quote should be escaped
                        result.append('\\"')
        elif char in ["{", "["]:
            if not in_string:
                brace_depth += 1
                in_key = True  # After opening brace/bracket, expect key
            result.append(char)
        elif char in ["}", "]"]:
            if not in_string:
                brace_depth -= 1
            result.append(char)
        elif char == ":" and not in_string:
            # After colon, we expect a value
            in_key = False
            result.append(char)
        elif char == "," and not in_string:
            # After comma, we expect a key (in objects) or value (in arrays)
            in_key = True
            result.append(char)
        else:
            result.append(char)

        i += 1

    return "".join(result)


def _get_next_non_space_char(text: str, start_pos: int) -> Optional[str]:
    """Get the next non-whitespace character from the given position."""
    for i in range(start_pos, len(text)):
        if not text[i].isspace():
            return text[i]
    return None


def _fix_quotes_with_regex(json_str: str) -> str:
    """
    Fix quotes using regex patterns - good for common cases.

    This method uses regex to identify string values and escape quotes within them.
    """

    def escape_value_quotes(match):
        prefix = match.group(1)  # Everything before the value
        value = match.group(2)  # The value content
        suffix = match.group(3)  # Everything after the value

        # Don't escape already escaped quotes
        # First, temporarily replace already escaped quotes
        temp_value = value.replace('\\"', "___TEMP_ESCAPED___")
        # Escape unescaped quotes
        temp_value = temp_value.replace('"', '\\"')
        # Restore the originally escaped quotes
        escaped_value = temp_value.replace("___TEMP_ESCAPED___", '\\"')

        return f'{prefix}"{escaped_value}"{suffix}'

    # Pattern to match string values (not keys)
    # This matches: "key": "value with possible quotes"
    pattern = r'("[\w_-]+"\s*:\s*)"((?:[^"\\]|\\.)*?)"(\s*[,}\]])'

    # Apply the fix
    fixed_content = re.sub(pattern, escape_value_quotes, json_str, flags=re.DOTALL)

    # Handle array values too
    # Pattern for array elements: ["value with quotes", "another value"]
    array_pattern = (
        r'(\[\s*(?:"[^"]*",\s*)*)"((?:[^"\\]|\\.)*?)"(\s*(?:,\s*"[^"]*")*\s*\])'
    )
    fixed_content = re.sub(
        array_pattern,
        escape_value_quotes,
        fixed_content,
        flags=re.DOTALL,
    )

    return fixed_content


def _fix_quotes_aggressive(json_str: str) -> str:
    """
    Aggressive quote fixing - last resort method.

    This method makes broad assumptions and may over-escape,
    but can handle very malformed JSON.
    """
    # Replace all unescaped quotes in what looks like string values
    # This is a very broad pattern that might over-escape

    lines = json_str.split("\n")
    fixed_lines = []

    for line in lines:
        # Skip lines that are just structural JSON (braces, brackets)
        if re.match(r"^\s*[{}\[\],]\s*$", line):
            fixed_lines.append(line)
            continue

        # For lines that contain key-value pairs
        if ":" in line:
            # Split on colon to separate key from value
            parts = line.split(":", 1)
            if len(parts) == 2:
                key_part = parts[0]
                value_part = parts[1]

                # Fix quotes in the value part only
                # Find string values (enclosed in quotes)
                value_matches = re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', value_part)

                # Process matches in reverse order to maintain indices
                for match in reversed(list(value_matches)):
                    start, end = match.span(1)  # Get the content inside quotes
                    content = match.group(1)

                    # Escape any unescaped quotes in the content
                    escaped_content = (
                        content.replace('\\"', "___TEMP___")
                        .replace('"', '\\"')
                        .replace("___TEMP___", '\\"')
                    )

                    # Replace in the value part
                    value_part = (
                        value_part[: match.start()]
                        + f'"{escaped_content}"'
                        + value_part[match.end() :]
                    )

                fixed_lines.append(key_part + ":" + value_part)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def parse_json_safe(json_str: str) -> Any:
    """
    Parse JSON string safely, attempting to fix common issues.

    Args:
        json_str: JSON string that may have issues

    Returns:
        Parsed JSON object or None if parsing fails
    """
    try:
        fixed_json = fix_unescaped_quotes_in_json(json_str)
        return json.loads(fixed_json)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Failed to parse JSON: {e}")
        return None


def extract_final_json_from_response(response: Any) -> Any:
    """
    Extract the final JSON from the agent response.
    This function tries to parse the response and extract meaningful fact-check results.
    """
    # Check if response is already a JSON object
    if isinstance(response, (dict, list)):
        return response

    response = response.strip()

    try:
        # Extract JSON object from example string
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        json_str = response[json_start:json_end]

        # Parse JSON and extract only inaccurate_facts
        output_json = json.loads(json_str)

        return output_json
    except Exception as e:
        logger.warning(f"Normal parsing failed: {e}")

    # Try to parse the entire response as JSON first
    try:
        # Try to parse the entire response as JSON first
        parsed = parse_json_safe(response)
        if parsed:
            return parsed
        logger.error(f"Failed to parse JSON from response: {response}")
    except Exception as e:
        logger.error(f"Error extracting JSON from response: {e}")
    return None


def parse_final_response(response: Any) -> List[FactVerifierResponse]:
    """
    Parse the final response from the agent.
    """
    final_json = extract_final_json_from_response(response=response)
    if final_json is None:
        logger.error("Error JSON parsing final results")
        return []

    try:
        fv_results = [FactVerifierResponse(**result) for result in final_json["claims"]]
        return fv_results
    except Exception as e:
        logger.error(f"Error parsing final results: {e}")
        return []
