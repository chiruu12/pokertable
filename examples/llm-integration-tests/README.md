# LLM Integration Tests

Manual integration tests that wire real LLM providers and agent frameworks
into the poker engine's tool system. **Not run in CI** — they hit live APIs
and cost money.

## Structure

```
providers/       — Direct LLM SDK adapters (Anthropic, OpenAI, Google)
frameworks/      — Agent framework adapters (Agno, LangChain, CrewAI, PydanticAI, Smolagents)
test_*.py        — Runnable test scripts
```

## Environment Variables

| Variable | Used By | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic SDK, Agno, LangChain, CrewAI, PydanticAI | Required for Claude models |
| `OPENAI_API_KEY` | OpenAI SDK, LangChain, CrewAI | Required for GPT models |
| `FIREWORKS_API_KEY` | OpenAI SDK (compat) | For Fireworks AI OSS models |
| `GOOGLE_API_KEY` | Google GenAI SDK | For Gemini models |
| `LMSTUDIO_BASE_URL` | OpenAI SDK (compat) | Default: `http://localhost:1234/v1` |

## Running Tests

```bash
# Provider tests
uv run python examples/llm-integration-tests/test_anthropic_sdk.py
uv run python examples/llm-integration-tests/test_openai_sdk.py
uv run python examples/llm-integration-tests/test_fireworks.py
uv run python examples/llm-integration-tests/test_lmstudio.py

# Framework tests
uv run python examples/llm-integration-tests/test_agno.py
uv run python examples/llm-integration-tests/test_langchain.py
uv run python examples/llm-integration-tests/test_crewai.py
uv run python examples/llm-integration-tests/test_pydantic_ai.py
uv run python examples/llm-integration-tests/test_smolagents.py

# Mixed tournaments
uv run python examples/llm-integration-tests/test_multi_provider.py
uv run python examples/llm-integration-tests/test_multi_framework.py
```

Each test skips gracefully if the required API key or server is unavailable.

## Installing Extra Dependencies

```bash
# Providers only
pip install anthropic openai google-genai

# All frameworks
pip install agno langchain langchain-anthropic langchain-openai crewai pydantic-ai smolagents
```
