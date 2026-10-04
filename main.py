# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import argparse
import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
import vertexai
from dotenv import load_dotenv

load_dotenv()


def _to_jsonable(value):
    """Convert an SDK event to nested dictionaries and lists when possible."""
    if isinstance(value, Mapping):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _to_jsonable(model_dump(mode="json", exclude_none=True))
        except TypeError:
            return _to_jsonable(model_dump())

    return value


def _find_route_geojson(value):
    """Find route GeoJSON in an ADK event or tool response."""
    candidates = []

    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                normalized_key = str(key).replace("_", "").lower()
                if (
                    normalized_key in {"routegeojson", "geojson"}
                    and isinstance(child, dict)
                    and child.get("type") == "FeatureCollection"
                    and isinstance(child.get("features"), list)
                ):
                    # Prefer the report tool's result to the initial route result.
                    priority = 2 if normalized_key == "routegeojson" else 1
                    candidates.append((priority, child))
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def _write_route_geojson(route, route_file):
    route_file.parent.mkdir(parents=True, exist_ok=True)
    route_file.write_text(json.dumps(route, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved route GeoJSON to {route_file}")


def _find_text(value):
    """Collect text parts from an ADK event or tool response."""
    if isinstance(value, dict):
        content = value.get("content")
        if isinstance(content, dict):
            parts = content.get("parts")
            if isinstance(parts, list):
                return "".join(
                    part["text"]
                    for part in parts
                    if isinstance(part, dict) and isinstance(part.get("text"), str)
                )
        return "".join(_find_text(child) for child in value.values())
    if isinstance(value, list):
        return "".join(_find_text(child) for child in value)
    return ""


def _write_markdown_response(response, response_file):
    if not response.strip():
        print("No markdown response was returned; no response file was written.")
        return
    response_file.parent.mkdir(parents=True, exist_ok=True)
    response_file.write_text(response.rstrip() + "\n", encoding="utf-8")
    print(f"Saved markdown response to {response_file}")


async def prompt_agent(
    client, project_id, location, agent_id, message, route_file, response_file
):
    name = f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_id}"
    remote_app = client.agent_engines.get(name=name)

    # user id is user defined. so could be anything
    remote_session = await remote_app.async_create_session(user_id="u_123")

    # we have a session
    session_id = remote_session["id"]

    print(f"Streaming response from agent {agent_id}:\n")
    route_geojson = None
    markdown_response = []
    async for event in remote_app.async_stream_query(
        user_id="u_123", session_id=session_id, message=message
    ):
        print(event, end="", flush=True)
        event_data = _to_jsonable(event)
        text = _find_text(event_data)
        if text:
            markdown_response.append(text)
        candidate = _find_route_geojson(event_data)
        if candidate is not None:
            route_geojson = candidate
    print()

    if route_geojson is not None:
        _write_route_geojson(route_geojson, route_file)
    else:
        print("No route GeoJSON was returned; no map file was written.")
    _write_markdown_response("".join(markdown_response), response_file)


def list_agents(client):
    print("Listing deployed agents...\n")
    agents = client.agent_engines.list()
    count = 0
    for agent in agents:
        agent_id = agent.api_resource.name.split("/")[-1]
        print(f"ID: {agent_id} | Display Name: {agent.api_resource.display_name}")
        count += 1
    if count == 0:
        print("No deployed agents found.")


def delete_agent(client, project_id, location, agent_id):
    name = f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_id}"
    print(f"Deleting agent: {agent_id}...")
    client.agent_engines.delete(name=name, force=True)
    print("Agent deleted successfully.")


async def main():
    parser = argparse.ArgumentParser(description="Vertex AI Agent Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # Prompt command
    prompt_parser = subparsers.add_parser(
        "prompt", help="Send a prompt to a deployed agent"
    )
    prompt_parser.add_argument(
        "--agent-id",
        required=True,
        help="The ID of the deployed agent (e.g. your AGENT_RUNTIME_ID)",
    )
    prompt_parser.add_argument(
        "--response-file",
        type=Path,
        default=Path("marathon_plan.md"),
        help="Where to save the agent's final markdown response",
    )
    prompt_parser.add_argument(
        "--message", required=True, help="The message/prompt to send"
    )
    prompt_parser.add_argument(
        "--route-file",
        type=Path,
        default=Path("marathon_route.geojson"),
        help="Where to save route GeoJSON returned by the agent",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List all deployed agents")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a deployed agent")
    delete_parser.add_argument(
        "--agent-id", required=True, help="The ID of the deployed agent to delete"
    )

    args = parser.parse_args()

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")

    if not project_id or not location:
        print(
            "Error: GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set in your environment or .env file."
        )
        return

    # Initialize the Vertex AI client
    client = vertexai.Client(project=project_id, location=location)

    if args.command == "prompt":
        await prompt_agent(
            client,
            project_id,
            location,
            args.agent_id,
            args.message,
            args.route_file,
            args.response_file,
        )
    elif args.command == "list":
        # list() and delete() are synchronous operations in the SDK
        list_agents(client)
    elif args.command == "delete":
        delete_agent(client, project_id, location, args.agent_id)


if __name__ == "__main__":
    asyncio.run(main())
