__author__ = 'Konrad Siek'

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
    range(0,  49):  2.0,
    range(50, 59):  3.0,
    range(60, 69):  3.5,
    range(70, 79):  4.0,
    range(80, 89):  4.5,
    range(90, 100): 5.0,
}


class Item(object):
    def __init__(self, question, answers, hint, comment, type):
        self._comment = comment
        self._question = question
        self._answers = answers
        self._hint = hint
        self._type = type

        self._clean_answers = None # initialized lazily

    @property
    def comment(self): return self._comment

    @property
    def question(self): return self._question

    @property
    def answers(self): return self._answers

    @property
    def hint(self): return self._hint

    @property
    def type(self): return self._type

    @property
    def clean_answers(self):
        if self._clean_answers == None:
            self._clean_answers = [self._clean(answer) for answer in self.answers]
        return self._clean_answers

    def _clean(self, string):
        return self._rewrite(self._remove_clutter(string.lower() if IGNORE_CASE else string))

    def _remove_clutter(self, string):
        clean_string = string
        for remove in REMOVE_FROM_ANSWERS:
            clean_string = clean_string.replace(remove, '')
        return clean_string

    def _rewrite(self, string):
        rewritten_string = string
        for before, after in REWRITE_RULES.items():
            rewritten_string = rewritten_string.replace(before, after)
        return rewritten_string

    def matches(self, string):
        clean_string = self._clean(string)
        for clean_answer in self.clean_answers:
            if clean_answer == clean_string:
                return True
        return False

    def matchesPerfectly(self, string):
        for answer in self.answers:
            if string == answer:
                return True
        return False

    def __str__(self):
        answers_string = (" " + ANSWER_ALTERNATIVE_SEPARATOR + " ").join(self.answers)
        comment_string = " " + COMMENT + " " + self.comment if self.comment else ""
        question_string = self.question if self.type == "text" else TYPE_SIGIL + self.type + " " + self.question
        hint_string = " " + HINT_START + self.hint + HINT_END + " "

        if QUESTION_POSITION == "left":
            return question_string + hint_string + answers_string + comment_string
        else:
            return answers_string + hint_string + question_string + comment_string


class ParserException(Exception): pass

def parse_item(string):
    """
    Create an item by parsing a string.

    :param string: String
    :return: List of items
    """

    # TODO: catch exceptions, re-raise them with sensible messages

    def squeeze(string):
        from re import sub
        return sub(" +", " ", string)

    no_comment, comment = [e.strip() for e in string.split(COMMENT, 2)] if string.count(COMMENT) else (string.strip(), "")
    left, right_and_hint = no_comment.split(HINT_START, 2)
    hint, right = right_and_hint.split(HINT_END, 2)

    question_string = left.strip() if QUESTION_POSITION == "left" else right.strip()
    answers_string = right.strip() if QUESTION_POSITION == "left" else left.strip()
    answer_strings = answers_string.split(ANSWER_ALTERNATIVE_SEPARATOR)

    answers = [squeeze(answer.strip()) for answer in answer_strings if answer.strip() != ""]

    if question_string.startswith(TYPE_SIGIL):
        type_marker, actual_question = question_string.split(" ", 2)
        type = type_marker.split(TYPE_SIGIL,2)[1]
        question = squeeze(actual_question.strip())
    else:
        type = "text"
        question = squeeze(question_string.strip())

    if type not in TYPES:
       raise ParserException("Type " + type + " is not a known item type. Known types: " + ", ".join(TYPES) + ".")

    if DEBUG:
        print("question:", question, "hint:", hint, "answers:", answers, "comment:", comment, "type:", type)

    return Item(question=question, answers=answers, hint=hint, comment=comment, type=type)

def read_test_file(path):
    items = []
    line = 1
    with open(path) as file:
        while True:
            unprocessed_string = file.readline()

            if not unprocessed_string:
                break

            try:
                item = parse_item(unprocessed_string.strip())
            except Exception as e:
                raise ParserException(path + ":" + str(line) + "> " + str(e))

            items.append(item)
            line += 1

    return items

class GradeException (Exception): pass

class Scheduler(object):
    def __init__(self, items=[]):
        self._items = items
        self._correct = 0
        self._attempted = 0

    @property
    def attempted(self):
        return self._attempted

    @property
    def correct(self):
        return self._correct

    @property
    def todo(self):
        return len(self._items)

    @property
    def percentage_correct(self):
        if self.attempted > 0:
            return int(100 * (float(self.correct) / float(self.attempted)))
        else:
            return float("inf")

    @property
    def grade(self):
        percentage_correct = self.percentage_correct

        if percentage_correct == float("inf"):
            return None

        for range, grade in GRADE_SCALE.items():
            if percentage_correct in range:
                return grade

        raise GradeException("Value of " + str(percentage_correct) +
                             " not in range of grade scale " + str(GRADE_SCALE))

    @property
    def current_item(self):
        return self._items[0] if self._items else None

    def next_item(self, correct=True):
        if not self._items:
            return None

        del self._items[0]

        if correct:
            self._correct += 1
        self._attempted += 1

        return self.current_item

    def cycle_item(self, correct=False):
        if not self._items:
            return None

        item = self._items[0]
        del self._items[0]
        self._items.append(item)

        if correct:
            self._correct += 1
        self._attempted += 1

        return self.current_item

    def append(self, items):
        if isinstance(items, list):
            self._items += items
        else:
            self._items.append(items)

# Starts from here.
if __name__ == '__main__':
    items = read_test_file("exercises/exercise1.6p")

    print([str(item) for item in items])

    scheduler = Scheduler(items)

    items = read_test_file("exercises/exercise2.6p")

    scheduler.append(items)

    print([str(item) for item in items])
    print([str(item.clean_answers) for item in items])
    print([item.matchesPerfectly("answer answer") for item in items])
    print([item.matches("answer answer") for item in items])
    print([item.matches("are not we all") for item in items])

    import random
    while scheduler.todo > 0:
        correct = random.choice((True, False))
        print(scheduler.todo, scheduler.attempted, scheduler.correct, str(scheduler.percentage_correct)+"%", scheduler.grade, correct, scheduler.current_item)
        if correct:
            scheduler.next_item()
        else:
            scheduler.cycle_item()
