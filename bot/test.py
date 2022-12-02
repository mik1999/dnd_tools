import utils.words_suggester as words_suggerter
import pymongo


def test_words_suggester():
    words = ['hello', 'hell', 'he', 'hall', 'abcd']
    suggester = words_suggerter.WordsSuggester(words, max_dist=1)
    assert suggester.suggest('he') == ['he', 'hell', 'hello']
    assert suggester.suggest('hell') == ['hell', 'hello', 'hall']
    assert suggester.suggest('abce') == ['abcd']


test_words_suggester()


def test_pymongo():
    client = pymongo.MongoClient()
    db = client.get_database('dnd')
    user_potions = db.get_collection('user_potions')
    DOC = {'user': 'mik', 'name': 'Potion of strength'}
    user_potions.insert_one(DOC)
    doc = user_potions.find_one({'user': 'mik'})
    assert doc == DOC


test_pymongo()
