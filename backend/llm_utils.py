try:
    from backend.config import OLLAMA_BASE_URL, DEEPSEEK_API_KEY, HUGGINGFACE_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY
except ModuleNotFoundError:
    from config import OLLAMA_BASE_URL, DEEPSEEK_API_KEY, HUGGINGFACE_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY
from typing import Callable, Optional
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.callbacks.base import BaseCallbackHandler


class BufferedStreamingHandler(BaseCallbackHandler):
    def __init__(self, buffer_limit: int = 60, ui_callback: Optional[Callable[[str], None]] = None):
        self.buffer = ""
        self.buffer_limit = buffer_limit
        self.ui_callback = ui_callback

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.buffer += token
        if "\n" in token or len(self.buffer) >= self.buffer_limit:
            print(self.buffer, end="", flush=True)
            if self.ui_callback:
                self.ui_callback(self.buffer)
            self.buffer = ""

    def on_llm_end(self, response, **kwargs) -> None:
        if self.buffer:
            print(self.buffer, end="", flush=True)
            if self.ui_callback:
                self.ui_callback(self.buffer)
            self.buffer = ""


# --- Configuration Data ---
# Instantiate common dependencies once
_common_callbacks = [BufferedStreamingHandler(buffer_limit=60)]

# Define common parameters for most LLMs
_common_llm_params = {
    "temperature": 0,
    "streaming": True,
    "callbacks": _common_callbacks,
}

# Map input model choices (lowercased) to their configuration
# Each config includes the class and any model-specific constructor parameters
_llm_config_map = {
    'gpt-4.1': { 
        'class': ChatOpenAI,
        'constructor_params': {'model_name': 'gpt-4.1', 'api_key': OPENAI_API_KEY} 
    },
    'gpt-5.1': { 
        'class': ChatOpenAI,
        'constructor_params': {'model_name': 'gpt-5.1', 'api_key': OPENAI_API_KEY} 
    },
    'gpt-5-mini': { 
        'class': ChatOpenAI,
        'constructor_params': {'model_name': 'gpt-5-mini', 'api_key': OPENAI_API_KEY} 
    },
    'gpt-5-nano': { 
        'class': ChatOpenAI,
        'constructor_params': {'model_name': 'gpt-5-nano', 'api_key': OPENAI_API_KEY} 
    },
    'claude-sonnet-4-5': {
        'class': ChatAnthropic,
        'constructor_params': {
            'model': 'claude-3-5-sonnet-20241022',
            'api_key': ANTHROPIC_API_KEY
        }
    },
    'claude-sonnet-4-0': {
        'class': ChatAnthropic,
        'constructor_params': {
            'model': 'claude-3-sonnet-20240229',
            'api_key': ANTHROPIC_API_KEY
        }
    },
    'gemini-2.5-flash': {
        'class': ChatGoogleGenerativeAI,
        'constructor_params': {'model': 'gemini-2.5-flash', 'google_api_key': GOOGLE_API_KEY}
    },
    'gemini-2.5-flash-lite': {
        'class': ChatGoogleGenerativeAI,
        'constructor_params': {'model': 'gemini-2.5-flash-lite', 'google_api_key': GOOGLE_API_KEY}
    },
    'gemini-2.5-pro': {
        'class': ChatGoogleGenerativeAI,
        'constructor_params': {'model': 'gemini-2.5-pro', 'google_api_key': GOOGLE_API_KEY}
    },
    'gemini-1.5-pro': {
        'class': ChatGoogleGenerativeAI,
        'constructor_params': {'model': 'gemini-1.5-pro', 'google_api_key': GOOGLE_API_KEY}
    },
    'llama3.2': { 
        'class': ChatOllama,
        'constructor_params': {'model': 'llama3.2:latest', 'base_url': OLLAMA_BASE_URL}
    },
    'llama3.1': { 
        'class': ChatOllama,
        'constructor_params': {'model': 'llama3.1:latest', 'base_url': OLLAMA_BASE_URL}
    },
    'gemma3': { 
        'class': ChatOllama,
        'constructor_params': {'model': 'gemma3:latest', 'base_url': OLLAMA_BASE_URL}
    },
    'deepseek-r1': { 
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'deepseek-r1', 
            'api_key': DEEPSEEK_API_KEY,
            'base_url': 'https://api.deepseek.com'
        }
    },
    'llama-3.1-70b-hf': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'meta-llama/Meta-Llama-3.1-70B-Instruct',
            'api_key': HUGGINGFACE_API_KEY,
            'base_url': 'https://router.huggingface.co/v1',
            'max_tokens': 2048,
            'temperature': 0.1
        }
    },
    'llama-3.1-8b-hf': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'meta-llama/Meta-Llama-3.1-8B-Instruct',
            'api_key': HUGGINGFACE_API_KEY,
            'base_url': 'https://router.huggingface.co/v1',
            'max_tokens': 2048,
            'temperature': 0.1
        }
    },
    'mistral-7b-hf': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'mistralai/Mistral-7B-Instruct-v0.3',
            'api_key': HUGGINGFACE_API_KEY,
            'base_url': 'https://router.huggingface.co/v1',
            'max_tokens': 2048,
            'temperature': 0.1
        }
    },
    'llama-3.1-70b-groq': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'llama-3.1-70b-versatile',
            'api_key': GROQ_API_KEY,
            'base_url': 'https://api.groq.com/openai/v1',
            'max_tokens': 2048,
            'temperature': 0.1
        }
    },
    'llama-3.1-8b-groq': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'llama-3.1-8b-instant',
            'api_key': GROQ_API_KEY,
            'base_url': 'https://api.groq.com/openai/v1',
            'max_tokens': 2048,
            'temperature': 0.1
        }
    },
    'mixtral-8x7b-groq': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'mixtral-8x7b-32768',
            'api_key': GROQ_API_KEY,
            'base_url': 'https://api.groq.com/openai/v1',
            'max_tokens': 2048,
            'temperature': 0.1
        }
    },
    'kimi-k2.5': {
        'class': ChatOllama,
        'constructor_params': {
            'model': 'kimi-k2.5:cloud',
            'base_url': OLLAMA_BASE_URL
        }
    },
    'minimax-m2': {
        'class': ChatOllama,
        'constructor_params': {
            'model': 'minimax-m2:cloud',
            'base_url': OLLAMA_BASE_URL
        }
    },
    'minimax-m2.5': {
        'class': ChatOllama,
        'constructor_params': {
            'model': 'minimax-m2.5:cloud',
            'base_url': OLLAMA_BASE_URL
        }
    },

    # ===== NVIDIA NIM =====
    # Base URL: https://integrate.api.nvidia.com/v1
    # Get your free API key at: https://build.nvidia.com
    'nemotron-70b-nim': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'nvidia/llama-3.1-nemotron-70b-instruct',
            'api_key': NVIDIA_NIM_API_KEY,
            'base_url': 'https://integrate.api.nvidia.com/v1',
            'max_tokens': 4096,
        }
    },
    'nemotron-ultra-nim': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'nvidia/nemotron-4-340b-instruct',
            'api_key': NVIDIA_NIM_API_KEY,
            'base_url': 'https://integrate.api.nvidia.com/v1',
            'max_tokens': 4096,
        }
    },
    'mistral-large-nim': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'mistralai/mistral-large-2-instruct',
            'api_key': NVIDIA_NIM_API_KEY,
            'base_url': 'https://integrate.api.nvidia.com/v1',
            'max_tokens': 4096,
        }
    },
    'mistral-medium-nim': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'mistralai/mistral-medium-3.5',
            'api_key': NVIDIA_NIM_API_KEY,
            'base_url': 'https://integrate.api.nvidia.com/v1',
            'max_tokens': 4096,
        }
    },
    'nemotron-mini-nim': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'nvidia/nemotron-mini-4b-instruct',
            'api_key': NVIDIA_NIM_API_KEY,
            'base_url': 'https://integrate.api.nvidia.com/v1',
            'max_tokens': 2048,
        }
    },

    # ===== OpenRouter =====
    # Base URL: https://openrouter.ai/api/v1
    # Get your API key at: https://openrouter.ai/keys
    # 75+ providers, pay-per-use, many models have free tiers
    'llama-4-scout-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'meta-llama/llama-4-scout',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },
    'llama-4-maverick-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'meta-llama/llama-4-maverick',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },
    'deepseek-v3-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'deepseek/deepseek-chat',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },
    'deepseek-r1-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'deepseek/deepseek-r1',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },
    'qwen3-coder-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'qwen/qwen3-coder',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },
    'qwen3-max-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'qwen/qwen3-max',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },
    'mistral-medium-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'mistralai/mistral-medium-3',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },
    'claude-3-7-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'anthropic/claude-3.7-sonnet',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 4096,
        }
    },

    # ===== OpenRouter FREE Tier =====
    # These models are 100% FREE — only requires a free OpenRouter account.
    # Get your key at: https://openrouter.ai/keys (no credit card needed)
    # Rate limits: ~20 req/min, ~200 req/day per model.
    # Model availability can change — check https://openrouter.ai/models?pricing=free
    'auto-free-or': {
        # Special OpenRouter meta-router: auto-picks the best available free model
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'openrouter/auto',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
    'llama-4-scout-free-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'meta-llama/llama-4-scout:free',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
    'llama-4-maverick-free-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'meta-llama/llama-4-maverick:free',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
    'deepseek-r1-free-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'deepseek/deepseek-r1:free',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
    'deepseek-v4-flash-free-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'deepseek/deepseek-v4-flash:free',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
    'qwen3-coder-free-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'qwen/qwen3-coder:free',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
    'gemma-4-31b-free-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'google/gemma-4-31b-it:free',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
    'llama-3-3-70b-free-or': {
        'class': ChatOpenAI,
        'constructor_params': {
            'model_name': 'meta-llama/llama-3.3-70b:free',
            'api_key': OPENROUTER_API_KEY,
            'base_url': 'https://openrouter.ai/api/v1',
            'max_tokens': 2048,
        }
    },
}