import litellm
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
from tools.custom_tool import CalendarCreateTool, GoogleContactsTool

litellm.drop_params = True
litellm.modify_params = True

# Claude Opus 4.8 (and the 4.6+ family) reject assistant-message prefill, which
# CrewAI's ReAct loop relies on. The installed litellm predates these models and
# doesn't strip the trailing assistant turn, so we ensure every request ends with
# a user message before it reaches Anthropic.
_orig_completion = litellm.completion


def _completion_no_prefill(*args, **kwargs):
    msgs = kwargs.get("messages")
    if isinstance(msgs, list) and msgs and msgs[-1].get("role") == "assistant":
        kwargs["messages"] = msgs + [{"role": "user", "content": "Continue."}]
    return _orig_completion(*args, **kwargs)


litellm.completion = _completion_no_prefill

llm = LLM(model="anthropic/claude-opus-4-8")

@CrewBase
class DescopeAgenticCrew():
    """DescopeAgenticCrew crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
    userId: str = None
    access_token: str = None

    def __init__(self, user_id=None, access_token=None, *args, **kwargs):
        self.user_id = user_id
        self.access_token = access_token

        super().__init__()

    @agent
    def calendar_manager(self) -> Agent:
        tools = []
        
        return Agent(
            config=self.agents_config.get('calendar_manager', {}),
            tools=tools,
            llm=llm,
            verbose=True,
            max_execution_time=60,  # Limit execution time to 60 seconds
            max_iter=3  # Reduced iterations to prevent loops
        )
    
    @agent
    def contacts_finder(self) -> Agent:
        tools = []
        
        return Agent(
            config=self.agents_config.get('contacts_finder', {}),
            tools=tools,
            llm=llm,
            verbose=True,
            max_execution_time=60,  # Limit execution time to 60 seconds
            max_iter=3  # Reduced iterations to prevent loops
        )
    
    @task
    def find_contact_task(self) -> Task:
        task = Task(
            config=self.tasks_config.get('find_contact_task'),# type: ignore[index]
        )
        task.tools = [GoogleContactsTool(user_id=self.user_id, access_token=self.access_token)]
        return task

    @task
    def create_calendar_task(self) -> Task:
        task = Task(
            config=self.tasks_config.get('create_calendar_task'),# type: ignore[index]
        )
        task.tools = [CalendarCreateTool(user_id=self.user_id, access_token=self.access_token)]
        return task

    @crew
    def crew(self) -> Crew:
        """Creates the DescopeAgenticCrew crew - dynamically configured based on use case"""

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            planning=True,
            planning_llm=llm,
            manager_llm=llm,
        )
    
    
