import collections
import copy
import logging
import string
import typing

from Levenshtein import distance as word_distance


logger = logging.getLogger()


class TooManySuggestionsError(Exception):
    pass


class StorageLimitExceededError(Exception):
    pass


class WordsSuggester:
    def __init__(self, words: typing.List[str], max_dist: int = 5):
        self.words = copy.deepcopy(words)
        self.max_dist = max_dist

    def suggest(self, word: str, max_size: int = 5) -> typing.List[str]:
        word = word.lower().strip()
        prefix_inds_list = []
        inds_with_dist = []
        result = []
        for index, candidate in enumerate(self.words):
            if candidate.lower().startswith(word):
                prefix_inds_list.append(index)
            inds_with_dist.append((word_distance(word, candidate), index))
        prefix_inds_list = sorted(prefix_inds_list, key=(lambda x: len(self.words[x])))
        inds_with_dist = sorted(inds_with_dist, key=(lambda x: x[0]))
        prefix_words_count = min(len(prefix_inds_list), max(1, max_size - 2))
        for i in range(prefix_words_count):
            result.append(self.words[prefix_inds_list[i]])
        current_words_count = prefix_words_count
        for dist, index in inds_with_dist:
            if dist > self.max_dist:
                break
            word = self.words[index]
            if word in result:
                continue
            result.append(word)
            current_words_count += 1
            if current_words_count >= max_size:
                break
        return result


class WordsSuggesterV2:
    MAX_STORAGE_SIZE = 10 ** 6
    SYMBOLS = 'ёйцукенгшщзхъфывапролджэячсмитьбю -,.'
    SYMBOLS_WITH_LATINS = SYMBOLS + string.ascii_lowercase

    def __init__(self, words: typing.List[str], max_dist: int = 1, use_latin: bool=False):
        logger.info(f'Start building word suggester for {words[:0]}, {words[1]}, ...')
        self.words = copy.deepcopy(words)
        self.lower_words = [word.lower() for word in self.words]
        self.words_hashes = {hash(word): i for i, word in enumerate(self.lower_words)}
        self.max_dist = max_dist
        self.use_latin = use_latin
        self.subwords: typing.Dict[int, typing.Set[int]] = collections.defaultdict(set)
        self.typos: typing.Dict[int, typing.Set[int]] = collections.defaultdict(set)
        self.total_size = 0
        for index, word in enumerate(self.lower_words):
            for i in range(len(word)):
                for j in range(i + 1, len(word) + 1):
                    subword = word[i:j]
                    self.subwords[hash(subword)] |= {index}
                    self.total_size += 1
        for index, word in enumerate(self.lower_words):
            self._similar_words_rec(word, 0, max_dist, index)
        logger.info(f'Finished building word suggester. Collected {self.total_size} suggestions')

    def _similar_words_rec(self, word: str, dist: int, max_dist: int, word_number: int):
        if dist >= max_dist:
            if word_number not in self.subwords[hash(word)]:
                self.typos[hash(word)] |= {word_number}
                self.total_size += 1
                if self.total_size >= self.MAX_STORAGE_SIZE:
                    raise StorageLimitExceededError
            return
        for i in range(len(word)):
            new_word = word[:i] + word[i + 1:]
            self._similar_words_rec(new_word, dist + 1, max_dist, word_number)
        all_symbols = self.SYMBOLS_WITH_LATINS if self.use_latin else self.SYMBOLS
        for i in range(len(word)):
            for symbol in all_symbols:
                new_word = word[:i] + symbol + word[i + 1:]
                self._similar_words_rec(new_word, dist + 1, max_dist, word_number)
        for i in range(len(word)):
            for symbol in all_symbols:
                new_word = word[:i] + symbol + word[i:]
                self._similar_words_rec(new_word, dist + 1, max_dist, word_number)

    def suggest(self, word: str, max_size: int = 5) -> typing.List[str]:
        if not word:
            raise TooManySuggestionsError
        word = word.lower()
        word_hash = hash(word)
        if self.words_hashes.get(word_hash):
            return [self.words[self.words_hashes[word_hash]]]
        subword_inds = self.subwords[word_hash]
        typo_inds = self.typos[word_hash]
        if len(subword_inds) > max_size:
            raise TooManySuggestionsError
        subwords = [self.words[i] for i in subword_inds]
        if len(subword_inds) + len(typo_inds) > max_size:
            return subwords
        return subwords + [self.words[i] for i in typo_inds]
