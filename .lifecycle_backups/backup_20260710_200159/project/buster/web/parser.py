from bs4 import BeautifulSoup

def html_to_text(html: str, max_chars: int = 12000) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    parts = []
    for elem in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = " ".join(elem.get_text(" ", strip=True).split())
        if text:
            parts.append(text)
    return title, "\n".join(parts)[:max_chars]
