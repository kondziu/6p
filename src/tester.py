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
    range(0,  50):  2.0,
    range(50, 60):  3.0,
    range(60, 70):  3.5,
    range(70, 80):  4.0,
    range(80, 90):  4.5,
    range(90, 101): 5.0,
}

SHOW_HINTS = True
SHOW_ANSWERS_ON_FAIL = True


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

import curses
from curses.textpad import Textbox, rectangle
import os.path

import textwrap

class ResultArea (object):
    def __init__(self, x, y, height, width): # TODO assertion for size
        self._width = width
        self._height = height
        self._x = x
        self._y = y

        self._message_height = 3
        self._message_window = curses.newwin(self._message_height , width, y, x)

        if SHOW_ANSWERS_ON_FAIL:
            self._answers_height = height - 3
            self._answers_window = curses.newwin(self._answers_height, width, y+4, x)


    def empty(self):
        self._message_window.clear()
        self._answers_window.clear()
        self._message_window.refresh()
        self._answers_window.refresh()

    def correct(self, answer, item):
        return self._display(correct=True, answer=answer, answers=item.answers)

    def wrong(self, answer, item):
        return self._display(correct=False, answer=answer, answers=item.answers)

    def update(self, correct, answer, item):
        return self._display(correct=correct, answer=answer, answers=item.answers)

    def _display(self, correct, answer, answers=None):
        self._message_window.refresh()
        self._message_window.border()

        text_width = self._width - 2
        text_height = self._height - 2

        self._message_window.refresh()

        if correct:
            self._message_window.addstr(1, int((text_width - 8)/2), "CORRECT!")
        else:
            self._message_window.addstr(1, int((text_width - 6)/2), "WRONG!")


            if SHOW_ANSWERS_ON_FAIL:
                self._answers_window.clear()
                self._answers_window.border()
                self._answers_window.addstr(0, 1, "[Accepted answers]")

                max_answers = self._answers_height - 2
                display_all_answers = len(answers) <= max_answers
                displayed_answers = answers if display_all_answers else answers[0:max_answers]

                if not display_all_answers:
                    self._answers_window.addstr(self._answers_height - 1, self._width - 7, "[...]")

                for index, answer in enumerate(displayed_answers):
                    self._answers_window.addstr(index + 1, 1, textwrap.shorten(answer, text_width, placeholder = "..."))

                self._answers_window.refresh()



    def wait(self):
        self._message_window.getkey()


class AnswerArea (object):
    def __init__(self, x, y, height, width):
        self._width = width
        self._height = height
        self._x = x
        self._y = y

        self._window = curses.newwin(height, width, y, x)

    def empty(self):
        return self._display(edit=False)

    def update(self, text=None):
        return self._display(text, edit=False)

    def edit(self, text=None):
        return self._display(text)

    def _display(self, text=None, edit=True):
        self._window.refresh()
        self._window.border()

        text_width = self._width - 2
        text_height = self._height - 2

        self._window.addstr(0, 1, "[%s]" % "Your answer"[0:text_width - 2])
        self._window.addstr(self._height - 1, text_width - 8, "[Ctrl+G]")
        #self._window.move(1,1)
        self._window.refresh()

        if edit:
            temporary_edit_window = curses.newwin(text_height, text_width, self._y + 1, self._x + 1)
            curses.curs_set(True)

            edit_box = Textbox(temporary_edit_window)
            edit_box.edit()
            curses.curs_set(False)
            content = edit_box.gather().strip()
            del temporary_edit_window

            return content

        else:
            return None

    def wait(self):
        self._window.getkey()


class QuestionArea (object):
    def __init__(self, x, y, height, width):
        self._width = width
        self._height = height
        self._x = x
        self._y = y

        self._window = curses.newwin(height, width, y, x)

    def empty(self):
        self._display("")

    def update(self, item):
        self._display(item.question, item.hint)

    def _display(self, text, hint=None):
        self._window.clear()
        self._window.border()

        text_width = self._width - 2
        text_height = self._height - 2
        self._window.addstr(0, 1, "[%s]" % "Question"[0:text_width - 2])

        lines = textwrap.wrap(text, width=text_width,
                              max_lines=text_height,
                              fix_sentence_endings=True,
                              tabsize=4,
                              placeholder = " (...)")

        for index, line in enumerate(lines):
            self._window.addstr(index + 1, 1, line)

        if hint:
            hint_label = "hint"
            hint_content = textwrap.shorten(hint, text_width - 4 - len(hint_label) - 1, placeholder = "...")
            hint_text = "[%s: %s]" % (hint_label, hint_content)
            self._window.addstr(self._height - 1, self._width - len(hint_text) - 2, hint_text)

        self._window.refresh()

    def wait(self):
        self._window.getkey()

class StatusBar (object):
    def __init__(self, x, y, width):
        self._width = width
        self._x = x
        self._y = y

        self._window = curses.newwin(3, width, y, x)

    def empty(self):
        return self._display([
            ("Attempted", ""), ("To do", ""),
            ("Correct", ""), ("Incorrect", ""),
            ("Percentage", ""), ("Grade", "")
        ])

    def update_from_scheduler(self, scheduler):
        return self._display([
            ("Attempted", str(scheduler.attempted)), ("To do", str(scheduler.todo)),
            ("Correct", str(scheduler.correct)), ("Incorrect", str(scheduler.incorrect)),
            ("Percentage", str(scheduler.percentage_correct) + "%" if scheduler.percentage_correct != None else ""),
            ("Grade", str(scheduler.grade) if scheduler.grade != None else "")
        ])

    def update(self, todo, attempted, correct, incorrect, percentage, grade):
        return self._display([
            ("Attempted", str(attempted)), ("To do", str(todo)),
            ("Correct", str(correct)), ("Incorrect", str(incorrect)),
            ("Percentage", str(percentage) + "%" if percentage != None else ""),
            ("Grade", str(grade) if grade != None else "")
        ])
        
    def _display(self, values):
        self._window.clear()
        self._window.border()

        column_width = int((self._width) / len(values))

        index = 0
        for key, value in values:
            column_position = 1 + column_width * index

            if index:
                self._window.addstr(0, column_position - 1, "┬")
                self._window.addstr(1, column_position - 1, "│")
                self._window.addstr(2, column_position - 1, "┴")

            printable_key = "[%s]" % key[0:column_width - 2 - 0]
            printable_value = value[0:column_width - 2 - 1]

            self._window.addstr(0, column_position + 0, printable_key)
            self._window.addstr(1, column_position + 1, printable_value)

            index += 1

        self._window.refresh()

    def wait(self):
        self._window.getkey()


class App6p (object):
    def __init__(self):
        pass

    def start(self):
        def run(screen):
            self._screen = screen
            curses.curs_set(False)
            self.run()

        curses.wrapper(run)


    def run(self):
        # Init components
        max_width = curses.COLS - 1

        self.status_bar = StatusBar(x=0, y=0, width=max_width) # smallest possible width is no of fiels * 5-ish
        self.question_area = QuestionArea(x=0, y=4,width=max_width, height=10) # smallest possible height is 3
        self.answer_area = AnswerArea(x=0, y=15,width=max_width, height=5) # smallest possible height is 3
        self.result_area = ResultArea(x=0, y=21,width=max_width, height=10) # smallest possible height is 6, width is like 5-ish

        self.status_bar.empty()
        self.question_area.empty()
        self.answer_area.empty()
        self.result_area.empty()

        path = "exercises/exercise1.6p" #self.select_file()
        items = read_test_file(path)
        scheduler = Scheduler(items)

        while scheduler.todo > 0:

            self.status_bar.update_from_scheduler(scheduler)
            self.question_area.update(scheduler.current_item)
            answer = self.answer_area.edit()

            correct = scheduler.current_item.matches(answer)
            self.result_area.update(correct, answer, scheduler.current_item)

            if correct:
                scheduler.next_item()
            else:
                scheduler.cycle_item()

            self.status_bar.update_from_scheduler(scheduler)
            self.result_area.wait()
            self.result_area.empty()

# Starts from here.
if __name__ == '__main__':
    app = App6p()
    app.start()
