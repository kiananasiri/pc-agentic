from dotenv import load_dotenv
from datetime import datetime
import threading
import os
from openai import OpenAI as clientOpenAI

# Load environment variables
load_dotenv()

# Thread-local storage for request isolation
_thread_local = threading.local()


class Config:
    """Configuration class for the chatbot application."""

    def __init__(self, model="gpt-4o-mini", reasoning=None):
        """
        Initialize configuration with optional model override and reasoning settings.

        Args:
            model (str, optional): The LLM model to use. Defaults to "gpt-4o-mini".
            reasoning (dict, optional): Reasoning settings for the model.
        """
        self.model = model
        self.max_tokens = 8000
        # Set minimal effort reasoning for GPT-5 models
        if model.lower() in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]:
            self.reasoning = {"effort": reasoning}
        else:
            self.reasoning = {}
     


class ServiceProvider:
    """
    Thread-safe service provider for LLM, agent, and client instances.
    Uses thread-local storage for request isolation in parallel environments.
    """

    _lock = threading.RLock()

    @classmethod
    def _get_thread_local_instance(cls):
        """Get the thread-local instance, creating if it doesn't exist."""
        if not hasattr(_thread_local, "service_provider"):
            with cls._lock:
                # Double-checked locking pattern
                if not hasattr(_thread_local, "service_provider"):
                    _thread_local.service_provider = cls(Config())
        return _thread_local.service_provider

    @classmethod
    def get_instance(cls, config=None):
        """
        Get or create the service provider instance for the current thread.

        Args:
            config (Config, optional): Configuration to use. If provided,
                                      reinitializes the service provider.

        Returns:
            ServiceProvider: The service provider instance for this thread.
        """
        if config is not None:
            # Create new instance with specified config
            with cls._lock:
                _thread_local.service_provider = cls(config)
        return cls._get_thread_local_instance()

    def __init__(self, config):
        """Initialize the service provider with a configuration."""
        self.config = config
        self._llm = None
        self._agent = None
        self._client = None

    @property
    def llm(self):
        """Get the LLM instance, initializing if needed."""
        if self._llm is None:
            with self._lock:
                if self._llm is None:
                    try:
                        from llama_index.multi_modal_llms.openai import OpenAIMultiModal
                        self._llm = OpenAIMultiModal(
                            model=self.config.model,
                            max_new_tokens=self.config.max_tokens,
                            reasoning=self.config.reasoning,
                        )
                    except Exception:
                        class DummyLLM:
                            def __init__(self, model):
                                self.model = model
                        self._llm = DummyLLM(self.config.model)
        return self._llm

    @property
    def agent(self):
        """Get the agent instance, initializing if needed."""
        if self._agent is None:
            with self._lock:
                if self._agent is None:
                    try:
                        from llama_index.llms.openai import OpenAI
                        from llama_index.core.agent import ReActAgent
                        from llama_index.tools.duckduckgo import DuckDuckGoSearchToolSpec
                        from public_app.src.prompts import ask_ddg_prompt

                        tools = DuckDuckGoSearchToolSpec().to_tool_list()
                        self._agent = ReActAgent(
                            tools=tools,
                            llm=OpenAI(
                                model=self.config.model,
                                temperature=0.0,
                                max_new_tokens=self.config.max_tokens,
                                reasoning=self.config.reasoning,
                            ),
                            system_prompt=ask_ddg_prompt.format(
                                today_data=datetime.now().strftime("%Y-%m-%d")
                            ),
                            verbose=False,
                        )
                    except Exception:
                        self._agent = None
        return self._agent

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = clientOpenAI(
                        timeout=float(os.getenv("OPENAI_TIMEOUT", "60")),
                        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3"))
                    )
        return self._client



# API functions
def initialize(model_name=None, reasoning=None):
    """
    Initialize or reinitialize services with a new model name and reasoning settings.
    Thread-safe and creates isolated instances per request thread.

    Args:
        model_name (str, optional): The model name to use. Defaults to None.
        reasoning (dict, optional): Reasoning settings for the model. Defaults to None.
    """
    config = Config(model=model_name, reasoning=reasoning) if model_name else Config()
    ServiceProvider.get_instance(config)


def get_llm():
    """
    Get the current LLM instance for this thread.
    Each parallel request gets its own isolated instance.
    """
    return ServiceProvider.get_instance().llm


def get_llm_name():
    """
    Return the model name of the current LLM instance to count the tokens.
    """
    return ServiceProvider.get_instance().llm.model


def get_agent():
    """
    Get the current agent instance for this thread.
    Each parallel request gets its own isolated instance.
    """
    return ServiceProvider.get_instance().agent
