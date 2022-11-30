import utils.words_suggester as words_suggerter


def test_words_suggester():
    words = ['hello', 'hell', 'he', 'hall', 'abcd']
    suggester = words_suggerter.WordsSuggester(words, max_dist=1)
    assert suggester.suggest('he') == ['he', 'hell', 'hello']
    assert suggester.suggest('hell') == ['hell', 'hello', 'hall']
    assert suggester.suggest('abce') == ['abcd']


test_words_suggester()
