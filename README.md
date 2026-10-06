# Building ADK Agents with Skills and Tools: Marathon Planner Agent

This repository contains the source code for the codelab **"Building ADK Agents with Skills and Tools"**, where you build a sophisticated Marathon Planner Agent using the Agent Development Kit (ADK). 

The agent progressively demonstrates capabilities such as well-structured system prompts via a prompt builder, dynamic skill loading, and mapping Model Context Protocol (MCP) tools for real-world location context. Finally, it demonstrates how to deploy the agent to the Google Cloud Agent Engine.

## Project Structure

*   `CODELAB.md`: Progressive agent walkthrough, local setup, authentication, deployment, and troubleshooting instructions.
*   `planner_agent/`: Contains the core code for the ADK agent:
    *   `agent.py`: The main entry point initializing the agent.
    *   `prompts.py` / `utils.py`: A prompt builder to construct logical instructions.
    *   `tools.py`: Tool registry mapping skills and MCP tools.
    *   `skills/`: Directory containing dynamic skills (like gis-spatial-engineering, mapping, and race-director).
    *   `sample.env`: Sample environment file.
*   `main.py`: A helper Python CLI script to interact with your agent once it is deployed to Google Cloud Agent Engine.

## Prerequisites

*   A Google Cloud project with billing enabled.
*   Python 3.12 or newer and `pip` installed.
*   A Google Maps API key if you want the remote Maps MCP tools enabled. The
    agent can also resolve a configured Secret Manager key; without a key,
    Maps tools start disabled. See [CODELAB.md](CODELAB.md) for details.

## Getting Started

1.  **Set up the Python environment:**
    Install `uv` if needed using the platform instructions in
    [CODELAB.md](CODELAB.md), then create and activate the environment:

    ```bash
    uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    ```

    On Windows PowerShell, activate it with
    `.venv\Scripts\Activate.ps1`.

2.  **Configure environment variables:**
    Create the agent environment file from its sample:
    ```bash
    cp planner_agent/sample.env planner_agent/.env
    ```
    Set `GOOGLE_CLOUD_PROJECT` in `planner_agent/.env`. To enable Maps MCP
    tools, provide `GOOGLE_MAPS_API_KEY` there or configure the Secret Manager
    fallback described in [CODELAB.md](CODELAB.md).

    Create the root environment file for `main.py`:
    ```bash
    cp sample.env .env
    ```
    Set its project ID and set `GOOGLE_CLOUD_LOCATION` to the Agent Engine
    runtime region (for this codelab, `europe-west1`). The agent environment
    file's `GOOGLE_CLOUD_LOCATION` controls Vertex AI calls made by the agent;
    the deploy command's `--region` controls where the runtime is created.

    `PLANNER_LOG_LEVEL=INFO` is the recommended default. Set it to `DEBUG` for
    more detailed local logs. Deployed logs are collected in Cloud Logging.

3.  **Run the agent locally (Terminal):**
    ```bash
    adk run planner_agent
    ```

4.  **Run the agent locally (Web UI):**
    To see the agent in action with skill loading and tool call visibility:
    ```bash
    adk web
    ```
    Access the UI at `http://127.0.0.1:8000`.

## Deployment

Deploy the agent to the Google Cloud Agent Engine securely:

```bash
adk deploy agent_engine \
  --env_file planner_agent/.env \
  --requirements_file planner_agent/requirements.txt \
  --project YOUR_PROJECT_ID \
  --region europe-west1 \
  planner_agent
```

Agent Engine runtime deployments require a supported regional location. The
`GOOGLE_CLOUD_LOCATION` value in the agent environment file configures Vertex
AI calls made by the agent; `--region` selects where the Agent Engine runtime
is deployed.

Replace `YOUR_PROJECT_ID` with the project ID used in both environment files.
See [CODELAB.md](CODELAB.md) for full setup, authentication, troubleshooting,
and cleanup steps.

## Interacting with the Deployed Agent

After deployment, you can use the provided `main.py` helper script to test the remote agent.

Make sure your root directory has an `.env` file configured with your `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`.

**List deployed agents:**
```bash
python main.py list
```

**Prompt a specific agent:**
```bash
export AGENT_ID=<YOUR_AGENT_ID>
python main.py prompt --agent-id ${AGENT_ID} --message "Plan a marathon for 10000 participants in Las Vegas on April 24, 2027 in the evening timeframe"
```

**Delete a deployed agent:**
```bash
python main.py delete --agent-id ${AGENT_ID}
```

## Local route map

After prompting the deployed agent with `python main.py prompt`, the CLI saves
returned route GeoJSON to `marathon_route.geojson` in the project root. Run the
map UI from the same directory to display it:

```bash
source .venv/bin/activate
python main.py list
python main.py prompt --agent-id YOUR_AGENT_ID --message "Plan a marathon for 10000 participants in Las Vegas on April 24, 2027 in the evening timeframe"
python route_ui.py
```

Open `http://127.0.0.1:8080`. The UI loads `marathon_route.geojson` when that
file exists; otherwise it generates a route with the local GIS tool using seed
42. Use `--route-file PATH` to display a specific GeoJSON export.

## Cleanup

To avoid ongoing charges, delete the deployed agent with `main.py delete` when
you no longer need it. If you created a Google Cloud project solely for this
codelab, delete it only after confirming it contains no resources you need and
reviewing its billing. See [CODELAB.md](CODELAB.md) for optional secret cleanup
and the full cleanup steps.
