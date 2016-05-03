__author__ = 'ksiek'

from sixpence import config as cfg

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
        return self._rewrite(self._remove_clutter(string.lower() if cfg.IGNORE_CASE else string))

    def _remove_clutter(self, string):
        clean_string = string
        for remove in cfg.REMOVE_FROM_ANSWERS:
            clean_string = clean_string.replace(remove, '')
        return clean_string

    def _rewrite(self, string):
        rewritten_string = string
        for before, after in cfg.REWRITE_RULES.items():
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
        answers_string = (" " + cfg.ANSWER_ALTERNATIVE_SEPARATOR + " ").join(self.answers)
        comment_string = " " + cfg.COMMENT + " " + self.comment if self.comment else ""
        question_string = self.question if self.type == "text" else cfg.TYPE_SIGIL + self.type + " " + self.question
        hint_string = " " + cfg.HINT_START + self.hint + cfg.HINT_END + " "

        if cfg.QUESTION_POSITION == "left":
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

    no_comment, comment = [e.strip() for e in string.split(cfg.COMMENT, 2)] if string.count(cfg.COMMENT) else (string.strip(), "")
    left, right_and_hint = no_comment.split(cfg.HINT_START, 2)
    hint, right = right_and_hint.split(cfg.HINT_END, 2)

    question_string = left.strip() if cfg.QUESTION_POSITION == "left" else right.strip()
    answers_string = right.strip() if cfg.QUESTION_POSITION == "left" else left.strip()
    answer_strings = answers_string.split(cfg.ANSWER_ALTERNATIVE_SEPARATOR)

    answers = [squeeze(answer.strip()) for answer in answer_strings if answer.strip() != ""]

    if question_string.startswith(cfg.TYPE_SIGIL):
        type_marker, actual_question = question_string.split(" ", 2)
        type = type_marker.split(cfg.TYPE_SIGIL,2)[1]
        question = squeeze(actual_question.strip())
    else:
        type = "text"
        question = squeeze(question_string.strip())

    if type not in cfg.TYPES:
       raise ParserException("Type " + type + " is not a known item type. Known types: " + ", ".join(cfg.TYPES) + ".")

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
    def incorrect(self):
        return self._attempted - self._correct

    @property
    def todo(self):
        return len(self._items)

    @property
    def percentage_correct(self):
        if self.attempted > 0:
            return int(100 * (float(self.correct) / float(self.attempted)))
        else:
            return None

    @property
    def grade(self):
        percentage_correct = self.percentage_correct

        if percentage_correct == float("inf") or percentage_correct == None:
            return None

        for range, grade in cfg.GRADE_SCALE.items():
            if percentage_correct in range:
                return grade

        raise GradeException("Value of " + str(percentage_correct) +
                             " not in range of grade scale " + str(cfg.GRADE_SCALE))

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