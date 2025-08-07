import requests
from bs4 import BeautifulSoup

def needs_web(text):
    keywords = ["search", "look up", "find", "weather", "news", "time", "price"]
    return any(k in text.lower() for k in keywords)

def search_web(query):
    print("[Web] Searching online...")
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://duckduckgo.com/html/?q={query}"
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results = soup.find_all("a", class_="result__a", limit=1)
    if results:
        return results[0].text
    return "No results found online."

def maybe_search_online(text):
    if needs_web(text):
        result = search_web(text)
        print("Jarvis [Online]:", result)
        return True
    return False
