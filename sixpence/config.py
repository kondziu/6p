__author__ = 'ksiek'

DEBUG = True

COMMENT = "//"
HINT_START = "["
HINT_END = "]"
ANSWER_ALTERNATIVE_SEPARATOR = "|"

QUESTION_POSITION = "left" # or "right"

TYPE_SIGIL = "@"
TYPES = set(["image", "sound", "text"])

# This should obviously be a config file.
CLEAN_ANSWERS = True
IGNORE_CASE = True
REMOVE_FROM_ANSWERS = [ "?", "!", ",", ".", ";", ":" ]
REWRITE_RULES = { "isn't": "is not", "aren't": "are not" }

GRADE_SCALE = {
    range(0,  50):  2.0,
    range(50, 60):  3.0,
    range(60, 70):  3.5,
    range(70, 80):  4.0,
    range(80, 90):  4.5,
    range(90, 101): 5.0,
}

SHOW_HINTS = True
SHOW_ANSWERS_ON_FAIL = True


