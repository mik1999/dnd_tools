import copy
import typing

from Levenshtein import distance as word_distance


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

