#!/usr/bin/env python3

import itertools
import json
import os
import re
import sys

import requests


class Char:
    def __init__(self, letter=None, position=None, color=None):
        self.letter = letter
        self.position = position
        self.color = color  # green is *, yellow is +

    def print(self):
        ESC_GREEN = "\033[42m"
        ESC_YELLOW = "\033[43m"
        ESC_END = "\033[0m"

        if self.color == wordle.SYMBOL_FOR_GREEN:
            print(ESC_GREEN + self.letter + ESC_END, end="")
        elif self.color == wordle.SYMBOL_FOR_YELLOW:
            print(ESC_YELLOW + self.letter + ESC_END, end="")
        else:
            print(self.letter, end="")

    def make_regex(self):
        if self.color == wordle.SYMBOL_FOR_GREEN:
            # (?=.a...)
            regex = "(?=" + "." * self.position + self.letter + "." * (Wordle.WORD_LENGTTH - self.position - 1) + ")"
        elif self.color == wordle.SYMBOL_FOR_YELLOW:
            # (?=....[^b])(?=.*b.*)
            regex = "(?=" + "." * self.position + "[^" + self.letter + "]" + "." * (Wordle.WORD_LENGTTH - self.position - 1) + ")" + "(?=" + ".*" + self.letter + ".*" + ")"
        else:
            # (?!.*c.*)
            regex = "(?!" + ".*" + self.letter + ".*" + ")"

        return regex


class Word:
    def __init__(self, raw_word):
        self.raw_word = raw_word

        chars = []

        position = 0
        for c in raw_word:
            if c == wordle.SYMBOL_FOR_GREEN or c == wordle.SYMBOL_FOR_YELLOW:
                chars[position - 1].color = c
            elif c in "abcdefghijklmnopqrstuvwxyz":
                chars.append(Char(c, position, None))  # `color` is determined by post-reading.
                position += 1
            else:
                raise ValueError(f"'{c}' is invalid character.")

        self.chars = chars

    def print(self):
        for c in self.chars:
            c.print()
        print("")

    def make_regex(self):
        regex = ""
        defacto_yellow = False
        for c in self.chars:
            if not c.color:
                for c2 in self.chars:
                    if c2.color == wordle.SYMBOL_FOR_GREEN and c2.letter == c.letter:
                        defacto_yellow = True

            if not defacto_yellow:
                regex += c.make_regex()

            defacto_yellow = False

        return regex


class Wordle:
    WORD_LENGTTH = 5
    SYMBOL_FOR_GREEN = "*"
    SYMBOL_FOR_YELLOW = "+"

    def __init__(self):
        DIC_FILE = "~/.wordle.dic.json"
        URL = "https://www.nytimes.com/games/wordle/main.3d28ac0c.js"

        if os.path.isfile(os.path.expanduser(DIC_FILE)):
            with open(os.path.expanduser(DIC_FILE)) as f:
                word_list = json.load(f)

        else:
            response = requests.get(URL)

            varMa = re.search(r"var Ma=([^\]]+])", response.text)
            word_list1 = json.loads(varMa.group(1))

            varOa = re.search(r",Oa=([^\]]+])", response.text)
            word_list2 = json.loads(varOa.group(1))

            word_list = word_list1 + word_list2
            # `varMa` contains the daily answers. I sorted it because it's boring as it is.
            word_list.sort()

            with open(os.path.expanduser(DIC_FILE), "w") as f:
                json.dump(word_list, f, indent=2)

        self.word_list = word_list

    def set_words(self, input_words):
        words = []
        for i, raw_word in enumerate(input_words):
            words.append(Word(raw_word))

        self.words = words

    def print_input_words(self):
        print("[Input words]")
        for w in self.words:
            w.print()

    def _search_regex(self, regex):
        self.candidates = [s for s in self.word_list if re.match(regex, s)]

        return self.candidates

    def search(self):
        regex = ""

        for w in self.words:
            regex += w.make_regex()

        self._search_regex(regex)

    def print_candidates(self):
        print("\n[Solution candidates]")
        for w in self.candidates:
            word = Word(w)
            word.print()

    def recommend(self):
        """Find words that contain as many unused letters as possible."""
        histogram = self._make_histogram()

        unused_raw_words = self._get_unused_raw_chars()

        sorted_unused_chars = [x[0] for x in histogram if x[0] in unused_raw_words]

        for top_n in reversed(range(2, Wordle.WORD_LENGTTH + 1)):
            regex = ""
            for chars in itertools.combinations(sorted_unused_chars[:Wordle.WORD_LENGTTH], top_n):
                for c in chars:
                    regex += "(?=.*" + c + ".*)"
                regex += "....."
                recommended_words = self._search_regex(regex)
                self.recommendations = recommended_words

                if len(recommended_words) > 0:
                    return recommended_words
        else:
            self.recommendations = None

    def print_recommendations(self):
        print("\n[Words that contain many unused and frequently occurring characters]")

        if not self.recommendations:
            print("No words to recommend.", file=sys.stderr)
            return

        for r in self.recommendations:
            print(r)

    def _make_histogram(self):
        histogram = {}
        for raw_words in self.candidates:
            for c in raw_words:
                try:
                    histogram[c] += 1
                except KeyError:
                    histogram[c] = 1

        histogram = sorted(histogram.items(), key=lambda x: x[1], reverse=True)

        return histogram

    def _get_unused_raw_chars(self):
        raw_chars = ""
        for w in self.words:
            for c in w.chars:
                raw_chars += c.letter

        return set("abcdefghijklmnopqrstuvwxyz") - set(raw_chars)


if __name__ == "__main__":
    input_words = sys.argv[1:]

    wordle = Wordle()
    wordle.set_words(input_words)
    wordle.print_input_words()
    candidates = wordle.search()

    if len(input_words) == 0:
        print("The command line arguments should be the words entered into Wordle.\n"
              "Add a '*' after the letter that is green in Wordle.\n"
              "Add a '+' after the letter that is yellow in Wordle.\n"
              "For example, if the answer is 'grade' and you type 'shine' and 'about', "
              "you would type `./wordle.py shine* a+bout` on the command line.")
    else:
        wordle.print_candidates()

    recommended = wordle.recommend()
    wordle.print_recommendations()
