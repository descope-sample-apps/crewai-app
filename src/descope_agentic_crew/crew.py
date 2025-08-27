from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
from tools.custom_tool import CalendarCreateTool, GoogleContactsTool

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

llm = LLM(model="gpt-4o")

@CrewBase
class DescopeAgenticCrew():
    """DescopeAgenticCrew crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
    userId: str = None
    session_token: str = None

    def __init__(self, user_id=None, session_token=None, *args, **kwargs):
        """Initialize the crew with optional user_id and calendar access token"""
        self.user_id = user_id
        self.session_token = session_token

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
        task.tools = [GoogleContactsTool(user_id=self.user_id, session_token=self.session_token)]
        return task

    @task
    def create_calendar_task(self) -> Task:
        task = Task(
            config=self.tasks_config.get('create_calendar_task'),# type: ignore[index]
        )
        task.tools = [CalendarCreateTool(user_id=self.user_id, session_token=self.session_token)]
        return task

    @crew
    def crew(self) -> Crew:
        """Creates the DescopeAgenticCrew crew - dynamically configured based on use case"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            planning=True,
            planning_llm=llm,
            manager_llm=llm,
        )
    
    
