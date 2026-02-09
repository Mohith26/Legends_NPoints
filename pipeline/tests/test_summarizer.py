from pipeline.summarizer import SYSTEM_PROMPT


def test_system_prompt_has_json_instructions():
    assert "JSON" in SYSTEM_PROMPT
    assert "label" in SYSTEM_PROMPT
    assert "summary" in SYSTEM_PROMPT


def test_system_prompt_has_parenting_context():
    assert "parenting" in SYSTEM_PROMPT.lower()
