from pipeline.preprocessor import clean_text, build_documents


class FakePost:
    def __init__(self, id, title, body, top_comments, subreddit, upvotes):
        self.id = id
        self.title = title
        self.body = body
        self.top_comments = top_comments
        self.subreddit = subreddit
        self.upvotes = upvotes


def test_clean_text_removes_urls():
    text = "Check this out https://example.com/page and more text"
    assert "https://example.com" not in clean_text(text)
    assert "more text" in clean_text(text)


def test_clean_text_removes_markdown_links():
    text = "See [this article](https://example.com) for details"
    result = clean_text(text)
    assert "this article" in result
    assert "https://example.com" not in result


def test_clean_text_strips_markdown_bold():
    text = "This is **bold** and *italic* text"
    result = clean_text(text)
    assert "bold" in result
    assert "**" not in result


def test_clean_text_collapses_whitespace():
    text = "lots   of    spaces\n\nand newlines"
    result = clean_text(text)
    assert "  " not in result


def test_build_documents_concatenates():
    posts = [
        FakePost(
            id=1,
            title="My kid won't sleep",
            body="Need help with bedtime routines",
            top_comments=["Try white noise", "Consistency is key", "Check with pediatrician"],
            subreddit="Parenting",
            upvotes=100,
        )
    ]
    df = build_documents(posts)
    assert len(df) == 1
    assert "won't sleep" in df.iloc[0]["document"]
    assert "bedtime routines" in df.iloc[0]["document"]
    assert "white noise" in df.iloc[0]["document"]
    assert df.iloc[0]["subreddit"] == "Parenting"


def test_build_documents_only_uses_top_3_comments():
    posts = [
        FakePost(
            id=1,
            title="Test",
            body="Body text here",
            top_comments=["c1", "c2", "c3", "c4", "c5"],
            subreddit="test",
            upvotes=10,
        )
    ]
    df = build_documents(posts)
    doc = df.iloc[0]["document"]
    assert "c3" in doc
    assert "c4" not in doc


def test_build_documents_handles_none():
    posts = [
        FakePost(
            id=1,
            title="Title only",
            body=None,
            top_comments=None,
            subreddit="test",
            upvotes=0,
        )
    ]
    df = build_documents(posts)
    assert len(df) == 1
    assert "Title only" in df.iloc[0]["document"]
