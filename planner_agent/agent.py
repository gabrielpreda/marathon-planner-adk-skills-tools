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

from google.adk.agents.llm_agent import Agent
from .prompts import PLANNER_INSTRUCTION, PLANNER_INSTRUCTION_NO_TOOLS
from .tools import get_tools
from .logging_config import configure_logging

import logging

configure_logging()
logger = logging.getLogger(__name__)

instruction = "Answer user questions to the best of your knowledge"
description = "A helpful assistant for user questions."
tools = []

# # TODO: Replace Instruction and Description Prompt only
# instruction=PLANNER_INSTRUCTION_NO_TOOLS
# description="Expert GIS analyst for marathon route and event planning."

# # TODO: Replaces Tools
#instruction=PLANNER_INSTRUCTION
#tools=get_tools()

root_agent = Agent(
    model="gemini-2.5-flash",
    name="planner_agent",
    description=description,
    instruction=instruction,
    tools=tools,
)

logger.info(
    "Initialized planner agent: model=%s tools=%d mode=%s",
    root_agent.model,
    len(tools),
    "skills-and-tools" if tools else "basic-or-prompt-only",
)
