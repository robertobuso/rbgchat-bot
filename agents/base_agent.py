"""
Base agent implementation for ChatDSJ Slack Bot.

This module provides the BaseAgent class that serves as the foundation
for all specialized agents in the system.
"""
from typing import Any, List, Optional

from crewai import Agent
from loguru import logger


class BaseAgent:
    """
    Base class for all CrewAI agents in the ChatDSJ system.
    
    This class provides common functionality and structure for specialized
    agents, including initialization, backstory generation, and tool management.
    
    Attributes:
        name: Name of the agent
        role: Role description of the agent
        goal: Goal or objective of the agent
        verbose: Whether to enable verbose logging
        crew_agent: The CrewAI Agent instance
    """

    def __init__(self, name: str, role: str, goal: str, verbose: bool = False) -> None:
        """
        Initialize a base agent with core attributes.
        
        Args:
            name: Name of the agent
            role: Role description of the agent
            goal: Goal or objective of the agent
            verbose: Whether to enable verbose logging
        """
        self.name = name
        self.role = role
        self.goal = goal
        self.verbose = verbose
        self.crew_agent: Optional[Agent] = None
        
        # Create the CrewAI agent
        self._create_agent()

    def _create_agent(self) -> None:
        """
        Create a CrewAI Agent instance with the agent's attributes.
        
        This method initializes the crew_agent attribute with a new
        CrewAI Agent configured with the agent's name, role, goal,
        backstory, and tools.
        """
        try:
            self.crew_agent = Agent(
                name=self.name,
                role=self.role,
                goal=self.goal,
                backstory=self.get_backstory(),
                tools=self.get_tools(),
                verbose=self.verbose
            )
            logger.debug(f"Created agent: {self.name}")
        except Exception as e:
            logger.error(f"Failed to create agent {self.name}: {e}")
            self.crew_agent = None

    def get_backstory(self) -> str:
        """
        Get the backstory for this agent.
        
        Returns:
            str: Default backstory text
            
        Note:
            This method should be overridden by subclasses to provide
            a specialized backstory for each agent type.
        """
        return (
            f"You are {self.name}, an AI assistant specialized in {self.role}. "
            f"Your goal is to {self.goal}."
        )

    def get_tools(self) -> List[Any]:
        """
        Get the tools available to this agent.
        
        Returns:
            List[Any]: Empty list of tools
            
        Note:
            This method should be overridden by subclasses to provide
            specialized tools for each agent type.
        """
        return []

    def get_agent(self) -> Optional[Agent]:
        """
        Get the CrewAI Agent instance.
        
        Returns:
            Optional[Agent]: The CrewAI Agent instance or None if not initialized
        """
        return self.crew_agent