"""Universal research engine: pluggable live web search with honest source tracking."""
import asyncio
import html
import re
from typing import Dict, List
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.core.config import settings

MAX_RESULTS = 5
_TIMEOUT = 15.0


async def _tavily(query: str) -> List[Dict[str, str]]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": settings.TAVILY_API_KEY, "query": query, "max_results": MAX_RESULTS},
        )
        r.raise_for_status()
        return [
            {"title": x.get("title", ""), "url": x.get("url", ""), "snippet": (x.get("content") or "")[:400]}
            for x in r.json().get("results", [])
        ]


def _strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_duckduckgo(page: str) -> List[Dict[str, str]]:
    results = []
    blocks = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|$)', page, re.DOTALL)
    for href, title, rest in blocks:
        url = html.unescape(href)
        if "uddg=" in url:
            url = unquote(parse_qs(urlparse(url).query).get("uddg", [url])[0])
        if url.startswith("//"):
            url = "https:" + url
        snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.DOTALL)
        results.append({"title": _strip_tags(title), "url": url, "snippet": _strip_tags(snip.group(1))[:400] if snip else ""})
        if len(results) >= MAX_RESULTS:
            break
    return results


async def _duckduckgo(query: str) -> List[Dict[str, str]]:
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (AI Boardroom research)"}) as client:
        r = await client.post("https://html.duckduckgo.com/html/", data={"q": query})
        r.raise_for_status()
        return parse_duckduckgo(r.text)


async def search_web(query: str) -> List[Dict[str, str]]:
    """Return search results, or [] if no provider could answer (never raises)."""
    try:
        if settings.TAVILY_API_KEY:
            return await _tavily(query)
        return await _duckduckgo(query)
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError):
        return []
