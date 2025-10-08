#!/usr/bin/env python3
"""
Epic Validator MCP Server
Provides custom tools for validating epic creation inputs
"""

import json
import os
import re
import subprocess
import sys


def validate_epic_creation(planning_doc_path: str) -> dict:
    """Validate epic creation inputs using the epic-paths.sh script"""

    # Clean path - remove line numbers
    clean_path = re.sub(r":\d+$", "", planning_doc_path)

    try:
        # Run the validation script
        script_path = os.path.expanduser("~/.claude/scripts/epic-paths.sh")
        result = subprocess.run(
            [script_path, clean_path], capture_output=True, text=True, check=False
        )

        # Parse the output
        output_lines = result.stdout.strip().split("\n")
        validation_data = {}

        for line in output_lines:
            if "=" in line:
                key, value = line.split("=", 1)
                validation_data[key] = value

        # Determine validation result
        spec_exists = validation_data.get("SPEC_EXISTS", "false") == "true"
        epic_exists = validation_data.get("EPIC_EXISTS", "false") == "true"

        return {
            "valid": spec_exists and not epic_exists,
            "spec_exists": spec_exists,
            "epic_exists": epic_exists,
            "epic_file": validation_data.get("EPIC_FILE", ""),
            "target_dir": validation_data.get("TARGET_DIR", ""),
            "base_name": validation_data.get("BASE_NAME", ""),
            "error_message": validation_data.get("ERROR_MESSAGE", ""),
            "cleaned_path": clean_path,
        }

    except Exception as e:
        return {"valid": False, "error": str(e), "cleaned_path": clean_path}


def handle_request(request):
    """Handle MCP requests"""

    if request["method"] == "tools/list":
        return {
            "tools": [
                {
                    "name": "validate_epic_creation",
                    "description": (
                        "Validate inputs for epic creation before starting work"
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "planning_doc_path": {
                                "type": "string",
                                "description": (
                                    "Path to the planning document (.md file)"
                                ),
                            }
                        },
                        "required": ["planning_doc_path"],
                    },
                }
            ]
        }

    elif request["method"] == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "validate_epic_creation":
            result = validate_epic_creation(arguments["planning_doc_path"])

            if result["valid"]:
                content = (
                    f"✅ Validation passed!\n\n"
                    f"Planning document: {result['cleaned_path']}\n"
                    f"Target epic file: {result['epic_file']}\n\n"
                    f"Ready to proceed with epic creation."
                )
            else:
                if not result["spec_exists"]:
                    error_msg = result.get('error_message', 'File does not exist')
                    content = (
                        f"❌ Planning document not found: "
                        f"{result['cleaned_path']}\n\n"
                        f"Error: {error_msg}\n\n"
                        f"Please provide a valid planning document path."
                    )
                elif result["epic_exists"]:
                    content = (
                        f"❌ Epic file already exists: {result['epic_file']}\n\n"
                        f"Please remove the existing file or use a different name."
                    )
                else:
                    content = (
                        f"❌ Validation failed: {result.get('error', 'Unknown error')}"
                    )

            return {"content": [{"type": "text", "text": content}], "_meta": result}

    return {"error": "Unknown method"}


def main():
    """Main MCP server loop"""
    while True:
        try:
            line = input()
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except EOFError:
            break
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
