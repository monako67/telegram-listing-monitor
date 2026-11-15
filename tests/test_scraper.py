from scraper import extract_items


def test_extracts_unique_same_host_links():
    html = """
    <a href='/item/1'> First item </a>
    <a href='https://example.com/item/1#details'>Duplicate</a>
    <a href='https://other.example/item/2'>External</a>
    <a href='/item/3'>Third item</a>
    """
    assert extract_items("https://example.com/search", html) == [
        ("https://example.com/item/1", "First item"),
        ("https://example.com/item/3", "Third item"),
    ]


def test_skips_empty_titles_and_respects_limit():
    html = "<a href='/empty'></a><a href='/one'>One</a><a href='/two'>Two</a>"
    assert extract_items("https://example.com/search", html, limit=1) == [
        ("https://example.com/one", "One")
    ]


