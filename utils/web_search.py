"""
WebSearch — DuckDuckGo orqali internet qidiruvi
temp_master_zip loyihasi uchun. API kalit talab etmaydi.
"""
import requests
import re
from urllib.parse import quote

def web_search(query: str, max_results: int = 3) -> str:
    """
    DuckDuckGo Instant Answer + HTML fallback.
    Sinxron versiya (asyncio ichida run_in_executor bilan ishlatiladi).
    """
    # 1. DuckDuckGo Instant Answer API
    try:
        url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(url, timeout=8)
        resp.encoding = "utf-8"
        data = resp.json()

        results = []
        if data.get("AbstractText"):
            heading = data.get("Heading", query)
            results.append(f"[{heading}]: {data['AbstractText'][:400]}")
            if data.get("AbstractURL"):
                results.append(f"Manba: {data['AbstractURL']}")

        related = data.get("RelatedTopics", [])
        count = 0
        for item in related:
            if count >= max_results:
                break
            if isinstance(item, dict) and item.get("Text"):
                results.append(f"- {item['Text'][:200]}")
                count += 1

        if results:
            return f"[INTERNET QIDIRUVI: '{query}']\n" + "\n".join(results)

    except Exception:
        pass

    # 2. HTML fallback (Google Search Scraper - More robust)
    try:
        url = f"https://www.google.com/search?q={quote(query)}&hl=uz"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "uz-UZ,uz;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.encoding = "utf-8"
        html = resp.text

        # Google Search Snippets (div class "BNeawe s3v9rd AP7Wnd")
        results = []
        snippets = re.findall(r'<div class="BNeawe s3v9rd AP7Wnd">.*?>(.*?)</div>', html, re.DOTALL)
        
        # Dollar kursi uchun maxsus (BNeawe iBp4i AP7Wnd - katta raqamlar)
        quick_info = re.findall(r'<div class="BNeawe iBp4i AP7Wnd">.*?>(.*?)</div>', html, re.DOTALL)
        if quick_info:
            results.append(f"TEZKOR MA'LUMOT: {quick_info[0]}")

        for s in snippets[:max_results]:
            clean = re.sub(r'<[^>]+>', '', s).strip()
            if len(clean) > 20:
                results.append(f"- {clean[:300]}")

        if results:
            return f"[GOOGLE QIDIRUVI: '{query}']\n" + "\n".join(results)

    except Exception as e:
        print(f"DEBUG: WebSearch Scraper error: {e}")

    return ""
