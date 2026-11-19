"""Expose Word blocks omitted by the layout converter in a compact section."""
def append_unmapped_blocks(soup, text_blocks):
    mapped = {node.get("data-key") for node in soup.find_all(attrs={"data-key": True})}
    missing = [(key, info) for key, info in text_blocks.items()
               if key not in mapped and info.get("text", "").strip()]
    if not missing:
        return
    panel = soup.new_tag("details")
    # Open so search / click-to-locate works without a separate action; users
    # can collapse it. Original content is local, same as the main preview.
    panel["open"] = ""
    summary = soup.new_tag("summary")
    summary.string = f"附加内容与隐藏文字（{len(missing)} 块，已纳入扫描）"
    panel.append(summary)
    for key, info in missing:
        item = soup.new_tag("p")
        item["data-key"] = key
        item["data-original-text"] = info["text"]
        item["data-word-block"] = "1"
        item.string = info["text"]
        panel.append(item)
    (soup.body or soup).append(panel)


def replaced_preview_base(html):
    """Do not present unbound layout text as if it were the edited output.

    Its canonical XML blocks are available in the supplemental section. Leave
    the original pane and pictures intact, clearly redirect only unbound text.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for text in list((soup.body or soup).find_all(string=True)):
        if not text.strip() or not any(char.isalnum() for char in text):
            continue
        parent = text.parent
        if parent.name in ("style", "script", "summary", "title"):
            continue
        if parent.get("data-key") or parent.find_parent(attrs={"data-key": True}):
            continue
        text.replace_with("［请在下方附加内容中复核此段］")
    return str(soup)
