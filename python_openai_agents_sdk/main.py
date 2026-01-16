from agents import (Agent, Runner, AgentHooks, Tool, RunContextWrapper,
                    TResponseInputItem,)
from functools import partial
from arcadepy import AsyncArcade
from agents_arcade import get_arcade_tools
from typing import Any
from human_in_the_loop import (UserDeniedToolCall,
                               confirm_tool_usage,
                               auth_tool)

import globals


class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self,
                       context: RunContextWrapper,
                       agent: Agent) -> None:
        self.event_counter += 1
        print(f"### ({self.display_name}) {
              self.event_counter}: Agent {agent.name} started")

    async def on_end(self,
                     context: RunContextWrapper,
                     agent: Agent,
                     output: Any) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended with output {output}"
                agent.name} ended"
        )

    async def on_handoff(self,
                         context: RunContextWrapper,
                         agent: Agent,
                         source: Agent) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                source.name} handed off to {agent.name}"
        )

    async def on_tool_start(self,
                            context: RunContextWrapper,
                            agent: Agent,
                            tool: Tool) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}:"
            f" Agent {agent.name} started tool {tool.name}"
            f" with context: {context.context}"
        )

    async def on_tool_end(self,
                          context: RunContextWrapper,
                          agent: Agent,
                          tool: Tool,
                          result: str) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended tool {tool.name} with result {result}"
                agent.name} ended tool {tool.name}"
        )


async def main():

    context = {
        "user_id": os.getenv("ARCADE_USER_ID"),
    }

    client = AsyncArcade()

    arcade_tools = await get_arcade_tools(
        client, toolkits=["GoogleSearch"]
    )

    for tool in arcade_tools:
        # - human in the loop
        if tool.name in ENFORCE_HUMAN_CONFIRMATION:
            tool.on_invoke_tool = partial(
                confirm_tool_usage,
                tool_name=tool.name,
                callback=tool.on_invoke_tool,
            )
        # - auth
        await auth_tool(client, tool.name, user_id=context["user_id"])

    agent = Agent(
        name="",
        instructions="# Introduction

Welcome to the AI Research Assistant! This agent is designed to help you conduct efficient online searches and gather valuable information from Google. By leveraging advanced search capabilities, it provides timely answers to your queries, making your research process smoother and more effective.

# Instructions

1. **Understand the Query:** Interpret the user's search query to identify key terms and context.
2. **Conduct a Google Search:** Utilize the GoogleSearch_Search tool by sending a query to retrieve relevant organic search results.
3. **Analyze Results:** Review the search results to extract key information and present it to the user in a clear and concise manner.
4. **Follow Up:** If additional information or clarification is needed, engage further with follow-up questions or searches.
5. **Provide Summaries:** Offer summaries or synthesized content based on the search results to help the user understand the information quickly.

# Workflows

## Workflow 1: Basic Information Search
1. Receive user query.
2. Use **GoogleSearch_Search** to perform a search with the specified query.
3. Analyze the top search results and extract key information.
4. Present the findings to the user.

## Workflow 2: Topic Exploration
1. Receive user query for a broader topic.
2. Use **GoogleSearch_Search** to retrieve multiple results (set `n_results` to a higher number).
3. Categorize the results based on subtopics or relevant themes.
4. Summarize the subtopics and provide a comprehensive overview to the user.

## Workflow 3: Follow-Up Clarification
1. Identify if user seeks further information after initial search results.
2. Engage user with clarifying questions to refine their query.
3. Conduct a follow-up search via **GoogleSearch_Search** with the refined query.
4. Analyze and present new findings to the user.

## Workflow 4: Comparative Analysis
1. Receive user query pertaining to comparisons between different entities (e.g., products, services).
2. Use **GoogleSearch_Search** to gather relevant results for all entities involved in the comparison.
3. Extract key comparative points from the search results.
4. Present a comparative synopsis to the user highlighting the differences and similarities.",
        model=os.environ["OPENAI_MODEL"],
        tools=arcade_tools,
        hooks=CustomAgentHooks(display_name="")
    )

    # initialize the conversation
    history: list[TResponseInputItem] = []
    # run the loop!
    while True:
        prompt = input("You: ")
        if prompt.lower() == "exit":
            break
        history.append({"role": "user", "content": prompt})
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=history,
                context=context
            )
            history = result.to_input_list()
            print(result.final_output)
        except UserDeniedToolCall as e:
            history.extend([
                {"role": "assistant",
                 "content": f"Please confirm the call to {e.tool_name}"},
                {"role": "user",
                 "content": "I changed my mind, please don't do it!"},
                {"role": "assistant",
                 "content": f"Sure, I cancelled the call to {e.tool_name}."
                 " What else can I do for you today?"
                 },
            ])
            print(history[-1]["content"])

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())