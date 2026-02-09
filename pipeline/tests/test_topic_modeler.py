from pipeline.topic_modeler import DOMAIN_STOP_WORDS


def test_domain_stop_words_exist():
    assert "kid" in DOMAIN_STOP_WORDS
    assert "parent" in DOMAIN_STOP_WORDS
    assert "baby" in DOMAIN_STOP_WORDS
    assert "mom" in DOMAIN_STOP_WORDS
    assert "dad" in DOMAIN_STOP_WORDS


def test_domain_stop_words_no_duplicates():
    assert len(DOMAIN_STOP_WORDS) == len(set(DOMAIN_STOP_WORDS))
