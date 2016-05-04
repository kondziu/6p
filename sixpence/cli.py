__author__ = 'ksiek'

import textwrap

import curses
from curses.textpad import Textbox

from sixpence.engine import Item, Scheduler, read_test_file
from sixpence import config as cfg

class ResultArea (object):
    def __init__(self, x, y, height, width, show_answers_on_fail=True): # TODO assertion for size
        self._width = width
        self._height = height
        self._x = x
        self._y = y

        self._message_height = 3
        self._message_window = curses.newwin(self._message_height , width, y, x)

        self._show_answers_on_fail = show_answers_on_fail
        if show_answers_on_fail:
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


            if self._show_answers_on_fail:
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

from os import listdir
import os.path
from os.path import isfile, isdir, join, abspath

class FilePicker (object):
    def __init__(self, height, width, y, x, columns=4):
        self._width = width
        self._height = height
        self._x = x
        self._y = y

        self._columns = 4
        self._column_width = int((self._width - 2) / self._columns)

        self._window = curses.newwin(height, width, y, x)
        self._window.keypad(1)

        self._path = "."

        # self._selector_border = curses.newwin(height - 2, width - 2, y + 1, x + 1)
        # self._selector_window = curses.newwin(height - 5, width - 4, y + 3, x + 2)

    def select(self, path=None):
        if path == None:
            path = self._path
        assert (isdir(path))
        return self._display(path)


    def _display(self, starting_path):

        def fill_to(width, string):
            return string + (" " * (width - len(string)))

        def shorten(width, string):
            return textwrap.shorten(string, width, placeholder="...")

        def list_files(path):
            all_files = listdir(path)

            directories = [ (dir, True) for dir in all_files if isdir(join(path, dir)) ]
            directories.sort()
            directories = [ ("..", True) ] + directories

            files = [ (file, False) for file in all_files if not isdir(join(path, file)) ]
            files.sort()

            items = directories + files

            return [items[i:i+self._columns] for i in range(0, len(items), self._columns)]

        def display_item(highlight, row, column, name):
            display_name = fill_to(self._column_width - 1, shorten(self._column_width - 1, name))
            if highlight:
                self._window.addstr(row + 1, column * self._column_width + 1, display_name, curses.A_REVERSE)
            else:
                self._window.addstr(row + 1, column * self._column_width + 1, display_name)

        def handle_input():
            pass

            self._window.addstr(self._height-1, 20, str(key) + " " + str(curses.KEY_ENTER) + "        ")

        def move_horizontal(direction, position, last_position):
            module = (self._columns if position[1] < last_position[1] else (last_position[0] + 1))
            column = (position[0] + direction) % module
            return (column, position[1])

        def move_vertical(direction, position, last_position):
            row = (position[1] + direction) % (last_position[1] + (1 if position[0] <= last_position[0] else 0))
            return (position[0], row)

        fresh = False
        path = abspath(starting_path)

        while True:
            if not fresh:
                self._window.clear()
                self._window.border()

                self._window.addstr(0, 1, "[%s/]" % path)

                grid = list_files(path)
                last_row = len(grid) - 1
                last_column_in_last_row = len(grid[last_row]) - 1

                position = (0, 0)
                fresh = True

            for i, row in enumerate(grid):
                for j, cell in enumerate(row):
                    file, is_dir = cell
                    highlight = (j, i) == position
                    display_item(highlight=highlight, row=i, column=j, name=(file + "/") if is_dir else file)

            self._window.refresh()

            key = self._window.getch()

            self._window.addstr(self._height - 1, 1,str(key) + "   ")

            if curses.KEY_LEFT == key:
                position = move_horizontal(-1, position, (last_column_in_last_row, last_row))

            elif curses.KEY_RIGHT == key:
                position = move_horizontal(+1, position, (last_column_in_last_row, last_row))

            elif curses.KEY_UP == key:
                position = move_vertical(-1, position, (last_column_in_last_row, last_row))

            elif curses.KEY_DOWN == key:
                position = move_vertical(+1, position, (last_column_in_last_row, last_row))

            elif 10 == key: # ENTER
                file, is_dir = grid[position[1]][position[0]]
                file_path = abspath(join(path, file))

                if is_dir:
                    path = file_path
                    fresh = False

                else:
                    self._window.clear()
                    self._window.refresh()

                    return file_path

            # elif key == 27: # ALT or ESC
            #     self._window.addstr(self._height - 1, 1,":" + str(key) + "  ")
            #
            #     self._window.nodelay(True)
            #
            #     kk = self._window.getch()
            #     if kk == -1: # ESC
            #        #self._window.clear()
            #        #self._window.refresh()
            #
            #        #self._window.nodelay(False)
            #        pass
            #        self._window.addstr(self._height - 1, 30,":::" + str(kk) + "  ")
            #        return None
            #
            #     self._window.addstr(self._height - 1, 20,"::" + str(kk) + "  ")
            #
            #     self._window.nodelay(False)


class Cli6p (object):
    def __init__(self):
        pass

    def start(self):
        def run(screen):
            self._max_width = curses.COLS - 1
            self._max_height = curses.LINES - 1
            self._screen = screen
            curses.curs_set(False)
            self.run()

        curses.wrapper(run)

    def _pick_file(self):
        file_picker = FilePicker(width=self._max_width, height=self._max_height, x=0, y=0)

        while True:
            path = file_picker.select() #"exercises/exercise1.sixpence" #self.select_file()

            if path:
                return path
            else:
                pass # TODO dialogue box


    def run(self):
        # Init components


        self.status_bar = StatusBar(x=0, y=0, width=self._max_width) # smallest possible width is no of fiels * 5-ish
        self.question_area = QuestionArea(x=0, y=4,width=self._max_width, height=10) # smallest possible height is 3
        self.answer_area = AnswerArea(x=0, y=15,width=self._max_width, height=5) # smallest possible height is 3
        self.result_area = ResultArea(x=0, y=21,width=self._max_width, height=10) # smallest possible height is 6, width is like 5-ish


        path = self._pick_file()

        self.status_bar.empty()
        self.question_area.empty()
        self.answer_area.empty()
        self.result_area.empty()


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

