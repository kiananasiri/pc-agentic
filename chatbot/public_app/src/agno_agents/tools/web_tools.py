import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

def _ddg_html_search(query: str, max_results: int = 5) -> str:
    """
    Fallback DuckDuckGo search using HTML endpoint when DDGS API hits rate limits.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        url = 'https://html.duckduckgo.com/html/'
        resp = requests.post(url, data={'q': query}, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        for i, result in enumerate(soup.find_all('div', class_='result'), start=1):
            if i > max_results:
                break
            title_tag = result.find('a', class_='result__a')
            snippet_tag = result.find('a', class_='result__snippet')
            if title_tag:
                title = title_tag.get_text(strip=True)
                href = title_tag.get('href', '')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                results.append(f"[{i}] {title}\nSnippet: {snippet}\nURL: {href}\n")
        return "\n".join(results)
    except Exception as e:
        return f"HTML fallback search error: {str(e)}"

def web_search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo to answer real-time market or news questions.
    Uses DDGS API with automatic HTML endpoint fallback to guarantee reliable search results.
    """
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(keywords=query, max_results=max_results))
        if raw_results:
            formatted = []
            for i, r in enumerate(raw_results, start=1):
                formatted.append(f"[{i}] {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('href')}\n")
            return "\n".join(formatted)
    except Exception:
        pass

    # Fallback search if DDGS API encounters rate limits or errors
    fallback_res = _ddg_html_search(query, max_results=max_results)
    if fallback_res:
        return fallback_res

    return "No web search results found."
