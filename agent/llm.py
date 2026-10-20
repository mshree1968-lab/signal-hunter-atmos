"""Shared Anthropic client, cost tracker and the Claude-web-search backend for the document finder.
The API key is read by the SDK from the ANTHROPIC_API_KEY environment variable. It is never printed or saved."""
import os

import anthropic

MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5-5")

# US$ per 1M tokens for Claude Sonnet 5.5 (input, output, cache read, 5-minute cache write = 1.25x input)
PRICE = {"in": 2.00, "out": 10.00, "cache_read": 0.20, "cache_write": 2.50}
PRICE_PER_SEARCH = 0.01          # Anthropic web search: $10 per 1,000 searches

_client = None


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=3, timeout=180.0)
    return _client


class Cost:
    """Adds up token usage across every API call in this run."""
    def __init__(self):
        self.calls = 0
        self.tok = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
        self.searches = 0

    def add(self, usage):
        self.calls += 1
        self.tok["in"] += usage.input_tokens or 0
        self.tok["out"] += usage.output_tokens or 0
        self.tok["cache_read"] += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.tok["cache_write"] += getattr(usage, "cache_creation_input_tokens", 0) or 0
        stu = getattr(usage, "server_tool_use", None)
        if stu is not None:
            self.searches += getattr(stu, "web_search_requests", 0) or 0

    def usd(self):
        t = sum(self.tok[k] * PRICE[k] for k in PRICE) / 1e6
        return round(t + self.searches * PRICE_PER_SEARCH, 4)

    def summary(self):
        return dict(api_calls=self.calls, tokens=dict(self.tok), web_searches=self.searches,
                    estimated_usd=self.usd())


COST = Cost()


class AnthropicSearchBackend:
    """Search backend for finder.py, using Claude's built-in web search tool.
    One API call per query (results are cached on disk by finder.CachedBackend).
    Returns the raw result list (url, title) exactly as the search engine gave it: the model
    does not choose or rank anything here; finder.py scores every result by rule."""

    TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 1}

    def search(self, query, n=10):
        resp = client().messages.create(
            model=MODEL, max_tokens=1024,
            output_config={"effort": "low"},
            tools=[self.TOOL],
            messages=[{"role": "user", "content":
                       f"Run exactly one web search for this query and then reply only 'done'. "
                       f"Query: {query}"}])
        COST.add(resp.usage)
        out = []
        for block in resp.content:
            if block.type == "web_search_tool_result" and isinstance(block.content, list):
                for r in block.content:
                    if getattr(r, "type", "") == "web_search_result":
                        out.append(dict(url=r.url, title=r.title or "", snippet=getattr(r, "page_age", "") or ""))
        return out[:n]


class HybridBackend:
    """Free DuckDuckGo first; Claude web search only if DuckDuckGo fails or returns nothing."""
    def __init__(self):
        from finder import DDGBackend
        self.ddg, self.claude = DDGBackend(), AnthropicSearchBackend()
        self.used = {"ddg": 0, "claude": 0}

    def search(self, query, n=10):
        try:
            res = self.ddg.search(query, n)
        except Exception:
            res = []
        if res:
            self.used["ddg"] += 1
            return res
        self.used["claude"] += 1
        return self.claude.search(query, n)


def search_backend():
    """SEARCH_BACKEND=hybrid (default), anthropic (Claude web search only) or ddg (free only)."""
    from finder import DDGBackend
    kind = os.environ.get("SEARCH_BACKEND", "hybrid").lower()
    if kind == "ddg":
        return DDGBackend()
    if kind == "anthropic":
        return AnthropicSearchBackend()
    return HybridBackend()
