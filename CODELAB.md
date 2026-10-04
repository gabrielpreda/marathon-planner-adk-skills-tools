# Marathon Planner Agent: setup and deployment


In this codelab you will build a Marathon Planner Agent using the Agent Development Kit (ADK).
You will progressively examine capabilities of the agent, from a well-structured system prompt to dynamic skill loading and mapping MCP tools. Finally, you will test the agent locally and deploy it to the Agent Runtime (Agent Engine).


## What you will learn

- Initialize a new ADK agent project
- Compose a robust system prompt using a structured builder
- Add Google Maps MCP tools for real-world location context
- Dynamically load skills into the agent's toolset
- Test the agent execution locally
- Deploy the agent to Agent Engine (Cloud Run)

## 1. Prerequisites and cloud setup

You need:

- A Google Cloud project with billing enabled.
- Python 3.12 or newer and `pip`.
- The Google Cloud CLI (`gcloud`).
- A browser for the Cloud Console and local ADK web interface.
- Basic familiarity with Python and terminal commands.
- A Maps API key if you want the remote Maps MCP tools enabled.
- Permissions to enable services, use Vertex AI, and deploy an Agent Engine
  runtime. Ask your administrator for the required roles if needed.

Authenticate the Google Cloud CLI and Application Default Credentials (ADC):

Verify the authentication:
```bash
gcloud auth login
```

Confirmm the project is configured:

```bash
gcloud config get project
```

Verify authentication:

```bash
gcloud auth list
```

Authenticate:

```bash
gcloud auth application-default login
```

Set your project as the default project:

```bash
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
```

### Enable APIs

Set your project ID in the shell and enable the APIs used by this codelab:

```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="europe-west1"  # Or another supported runtime region.
```

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  mapstools.googleapis.com \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com \
  --project "$GOOGLE_CLOUD_PROJECT"
```

### Alternative: use a Cloud Shell

If using Cloud Shell, it is already authenticated for `gcloud`; still check
that the active account and project are the intended ones. ADK deployment uses
ADC for its Google Cloud API calls.


### Create a Maps API key

Create a key in the Cloud Console under **Google Maps Platform → Credentials**.
Restrict the key to the APIs and applications appropriate for your deployment.
The key is sent to the Maps MCP endpoint as an API key header.

The agent checks `GOOGLE_MAPS_API_KEY` first. Its code also has a fallback that
tries to read the latest version of a Secret Manager secret named
`maps-api-key`. If using that fallback, enable Secret Manager, create the
secret, and ensure the runtime identity can access its version. Save the key to
a protected local file, then create the secret without putting the key in a
command argument:

```bash
gcloud secrets create maps-api-key \
  --data-file="PATH_TO_PROTECTED_KEY_FILE" \
  --project "$GOOGLE_CLOUD_PROJECT"
```

Grant the identity used by the agent permission to access the secret version.
Without a resolvable key, the agent starts with Maps tools disabled.

## 2. Install the project

From the repository root, create and activate an uv virtual environment, then
install the project dependencies:

```bash
uv venv .venv
source .venv/bin/activate
```

```bash
uv pip install -r planner_agent/requirements.txt
```


The root requirements support local development and the CLI. The separate
`planner_agent/requirements.txt` is installed in the remote runtime and
includes the Agent Engine SDK extras and MCP package needed by the agent.

## 3. Configure environment files

Create both environment files from their samples:

```bash
cp planner_agent/sample.env planner_agent/.env
cp sample.env .env
```

In `planner_agent/.env`, set the project ID and Maps API key:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=YOUR_MODEL_LOCATION
GOOGLE_MAPS_API_KEY=YOUR_MAPS_API_KEY
PLANNER_LOG_LEVEL=INFO
```

The model location is used for Vertex AI calls made by the agent. In the root
`.env`, set the same project ID and the region where you will deploy the
runtime; `main.py` uses these values to find the deployed agent:

```dotenv
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=europe-west1
```

The model location and runtime region are separate settings. Choose a
supported Agent Engine regional location that meets your latency and data
location needs. For deployments serving users in Europe, `europe-west1` is a
reasonable starting point. Set the shell's `GOOGLE_CLOUD_LOCATION` to the
runtime region you chose, and use the same value in the root `.env`. If you
choose another region, update both values.

The sample enables OpenTelemetry and ADK message-content capture in spans. This
can place prompts and responses in trace data. Set
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false` and
`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` if traces should not include
message content. Keep `.env` files private and do not commit them.

## 4. Explore the agent and prompt

The repository contains the complete agent. Start with these files:

- `planner_agent/agent.py` creates the ADK `Agent` and selects the model,
  instruction, and tools.
- `planner_agent/prompts.py` defines role, rules, skills, tools, and workflow
  sections. It builds both a prompt-only instruction and the full instruction.
- `planner_agent/utils.py` contains `PromptBuilder`, which assembles the named
  sections in order.


### Before testing: instructions, skills, and tools

This codelab compares three agent configurations. The first has generic
instructions and no tools. The second adds marathon-planning instructions but
still has no tools. The third adds the full planner instructions and registers
skills and tools.

A **skill** provides focused guidance that the agent can load when relevant.
A **tool** lets the agent perform an operation or retrieve information. In this
project, the GIS skill guides route planning, and GIS tools generate and report
the route. Maps MCP tools can look up real-world information when configured.

As you run each version, watch for two things: how the instructions shape the
answer, and whether the agent actually calls tools to produce or retrieve
results.

### Run locally and inspect events

You will perform three tests (Step 1 to Step 3), with three versions of the agents setup.
You can test the application in two ways:

Use `adk run` command:

```bash
adk run planner_agent
```

Alternatively, you can start the ADK web interface:

```bash
adk web
```

If you run from GCP Cloud Shell terminal, use:

```bash
adk web --allow_origins "regex:.*"
```

Open `http://127.0.0.1:8000`, choose `planner_agent`, and send a planning
request such as:

```text
Plan a marathon for 10000 participants in Las Vegas on April 24, 2027 in the evening. Include the route, logistics, safety, community impact, and weather considerations.
```

Inspect the skill-load and tool-call events, then review the generated plan.

Stop either local process with Ctrl+C when finished.

### Step 1: Simple instructions, no tools

To follow the progression, begin with the generic baseline. In
`planner_agent/agent.py` these lines are uncommented:

```python
instruction = "Answer user questions to the best of your knowledge"
description = "A helpful assistant for user questions."
tools = []
```

Run the agent and ask a simple general question.

Then ask the question given above.

This shows the behavior of a basic agent before specialized
instructions or tools are added.


### Step 2: prompt-only instructions, no tools

Next, use the prompt-only instruction and keep the tool list empty:

```python
instruction = PLANNER_INSTRUCTION_NO_TOOLS
description = "Expert GIS analyst for marathon route and event planning."
tools = []
```

Run the agent and try a general question, then ask it to plan a marathon.

The prompt-only version can reason from its instructions but cannot call route
or Maps tools. 


### Explore skills and tools

The skills live under `planner_agent/skills/` and are loaded from their
`SKILL.md` files by `planner_agent/tools.py`:

- `gis-spatial-engineering` provides route planning and route reporting using
  the included road network data.
- `mapping` describes how to ground landmarks and weather details with Maps
  tools.
- `race-director` guides event logistics, safety, traffic mitigation, and
  community impact.

ADK's `SkillToolset` makes skills available on demand. The GIS functions are
registered as additional tools and become available after the relevant skill
is loaded. The agent also uses a memory preload tool.

The mapping integration in `planner_agent/tools.py` creates an MCP client for
the Maps endpoint and authenticates with the API key. The Maps API key can be
provided through the agent environment or resolved through the configured
Secret Manager fallback described above.

### Step 3: planner instructions, skills & tools

In the final step, restore the full configuration already
provided in the repository:

```python
instruction = PLANNER_INSTRUCTION
tools = get_tools()
```

The full prompt tells the agent how to select skills, plan logistics, validate
safety, and present a readable plan. The model and agent implementation are
defined in `agent.py`; use the version in the checkout rather than copying
older model examples. Restore the final configuration before deploying.



## 5. Deploy to Agent Engine

Deploy from the repository root. Use the same project ID and runtime region
configured above:

```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="europe-west1"  # Or another supported runtime region.
```

Run the deploy to Agent Engine script:

```bash
adk deploy agent_engine \
  --env_file planner_agent/.env \
  --requirements_file planner_agent/requirements.txt \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --display_name marathon-planner \
  planner_agent
```

The command prints the resource name and runtime ID. Save the runtime ID for
the next step. The shell variable must contain a real supported location; do
not type a placeholder such as `YOUR_RUNTIME_REGION` as the region value.

Open the runtime in the Cloud Console or test it in the Agent Engine
playground. The runtime can also be called from this repository's CLI.

## 6. List and call the deployed agent

Make sure the root `.env` contains the deployed runtime's project and region,
then list deployed agents:

```bash
python main.py list
```

Send a prompt using the runtime ID:

```bash
export AGENT_ID="YOUR_AGENT_ID"
python main.py prompt \
  --agent-id $AGENT_ID \
  --message "Plan a marathon for 10000 participants in Las Vegas on April 24, 2027 in the evening. Include the route, logistics, safety, community impact, and weather considerations."
```


## 7. Visualize the marathon route

The agent run generated the file `marathon_route.geojson`. 
Visualise the marathon route generated as an artefact by the agent with:

```bash
python route_ui.py
```

Then open the visualization tool by accessing `http://127.0.0.1:8080`.


## 8. Troubleshooting

- **Authentication errors:** Check `gcloud auth list`, repeat both login
  commands, and confirm that your account has the required cloud permissions.
- **Runtime location errors:** Pass a supported regional location to
  `--region`. The model-call location and runtime region are configured
  separately.
- **Missing Python modules in the runtime:** Add the imported package to
  `planner_agent/requirements.txt` and redeploy.
- **Runtime startup errors:** Inspect Cloud Logging for the corresponding
  `aiplatform.googleapis.com/ReasoningEngine` resource.
- **Maps tools are unavailable:** Confirm that the Maps key is configured, the
  Maps MCP API is enabled for the project, and any Secret Manager identity has
  permission to read the secret version.

## 9. Clean up

Delete the runtime when it is no longer needed:

```bash
python main.py delete --agent-id "$AGENT_ID"
```

If you created the optional `maps-api-key` Secret Manager secret, delete it
when it is no longer needed:

```bash
gcloud secrets delete maps-api-key --project "$GOOGLE_CLOUD_PROJECT"
```

If you created a dedicated project solely for this codelab, you can delete the
project after confirming that it contains no resources you need. Review
project billing for charges from Vertex AI, Agent Engine, and other enabled
services.

## References

- [Agent Engine setup](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/set-up)
- [Agent Engine deployment](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy)
- [Google Cloud MCP authentication](https://docs.cloud.google.com/mcp/set-up-authentication-mcp-servers)
