import time
import re
import random
import string
import pytest
import operator
from pathlib import Path
from itertools import chain
from collections import Counter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from locator import locator

URL = "https://www.nytimes.com/games/wordle/index.html"
DICT = "words.txt"
ALLOWABLE_CHARACTERS = set(string.ascii_lowercase)
ALLOWED_ATTEMPTS = 6
WORD_LENGTH = 5
FIRST_WORD = 'arose'
WORDS = {
  word.lower()
  for word in Path(DICT).read_text().splitlines()
  if len(word) == WORD_LENGTH and set(word) < ALLOWABLE_CHARACTERS
  }
LETTER_COUNTER = Counter(chain.from_iterable(WORDS))
LETTER_FREQUENCY = {
    character: value / sum(LETTER_COUNTER.values())
    for character, value in LETTER_COUNTER.items()
    }

class TestWordleSolver:

    def calculate_word_commonality(self, word):
        score = 0.0
        for char in word:
            score += LETTER_FREQUENCY[char]
        return score / (WORD_LENGTH - len(set(word)) + 1)

    def sort_by_word_commonality(self, words):
        sort_by = operator.itemgetter(1)
        return sorted(
            [(word, self.calculate_word_commonality(word)) for word in words],
            key=sort_by,
            reverse=True,
        )

    def display_word_table(self, word_commonalities):
        for (word, freq) in word_commonalities:
            (f"{word:<10} | {freq:<5.2}")

    def match_word_vector(self, word, word_vector):
        assert len(word) == len(word_vector)
        for letter, v_letter in zip(word, word_vector):
            if letter not in v_letter:
                return False
        return True

    def match(self, word_vector, possible_words):
        return [word for word in possible_words if self.match_word_vector(word, word_vector)]

    def setup_method(self):
        options = Options()
        options.add_argument('headless')
        options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=options)
    
    def test_wordle(self):
        possible_words = WORDS.copy()
        word_vector = [set(string.ascii_lowercase) for _ in range(WORD_LENGTH)]
        self.driver.get(URL)
        get_title = self.driver.title
        print(get_title)
        tile_index=0

        #closing the 'How to Play' page
        close_how_to_play = self.driver.find_element(By.XPATH, locator['close_sign'])
        close_how_to_play.click()

        print(f"Attempt 1 with {len(possible_words)} possible words")

        for attempt in range(1, ALLOWED_ATTEMPTS+1):

            input_word = random.choice(tuple(possible_words))
            word = input_word if tile_index else FIRST_WORD

            for letter in word:
                    self.driver.find_element(By.XPATH, locator[letter]).click()

            letter = WebDriverWait(self.driver,10).until(EC.element_to_be_clickable((By.XPATH, locator['ENTER'])))
            letter.click()

            time.sleep(2)
            
            self.driver.save_screenshot('wordle.png')

            Tiles = self.driver.find_elements(By.XPATH, '//*[@data-testid="tile"]')
            data_state_list=[]
            for _ in range(WORD_LENGTH):
                data_state_list.append(Tiles[tile_index].get_attribute('data-state'))
                tile_index=tile_index+1

            State_counter = Counter(data_state_list)

            print(f"In \'{word}\' \n \t Correct Letters:{State_counter['correct']} \
                 \n \t Present Letters:{State_counter['present']} \
                 \n \t  Absent Letters:{State_counter['absent']}")
            
            #If all letters are correct loop will be break
            if State_counter['correct'] == 5:
                print(f"Wordle Solved with : \'{word}\' word")
                break

            self.display_word_table(self.sort_by_word_commonality(possible_words)[:10])
            
            present_letter_list = []

            for idx, letter in enumerate(data_state_list):
                if letter == "correct":
                    word_vector[idx] = {word[idx]}
                elif letter == "present":
                    try:
                        present_letter_list.append(word[idx])
                        word_vector[idx].remove(word[idx])
                    except KeyError:
                        pass
                elif letter == "absent":
                    for vector in word_vector:
                        try:
                            vector.remove(word[idx])
                        except KeyError:
                            pass

            possible_words = self.match(word_vector, possible_words)

            for i in range(len(present_letter_list)):
                letter = re.compile(f".*{present_letter_list[i]}")
                possible_words = set(filter(letter.match, possible_words))
            
            print(f"Attempt {attempt+1} with {len(possible_words)} possible words")

            if not possible_words:
                assert False, "Sorry! Out of Words, Try again."

    def teardown_method(self):
        self.driver.quit()
