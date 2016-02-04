#!/usr/bin/env python

""" This script is designed to support active reading.  It takes as input
    a set of ipython notebook as well as some target cells which define a set
    of reading exercises.  The script processes the collection of notebooks
    and builds a notebook which summarizes the responses to each question.

    TODO:
        (1) Currently there is only support for parsing a single notebook,
            however, it will be very easy to extend this to multiple notebooks

"""

import sys
import json
from numpy import argmin
import Levenshtein
from copy import deepcopy
import pandas as pd
import urllib
import os


class NotebookExtractor(object):
    """ The top-level class for extracting answers from a notebook.
        TODO: add support multiple notebooks
    """

    MATCH_THRESH = 10  # maximum edit distance to consider something a match

    def __init__(self, notebook_URLs, question_prompts):
        """ Initialize with the specified notebook URLs and
            list of question prompts """
        self.notebook_URLs = notebook_URLs
        self.question_prompts = question_prompts

    def extract(self):
        """ Filter the notebook at the notebook_URL so that it only contains
            the questions and answers to the reading.
        """
        nbs = {}
        for url in self.notebook_URLs:
            print url
            fid = urllib.urlopen(url)
            nbs[url] = json.load(fid)
            fid.close()
        filtered_cells = []
        for i, prompt in enumerate(question_prompts):
            for j, url in enumerate(nbs):
                response_cells = prompt.get_closest_match(nbs[url]['cells'], NotebookExtractor.MATCH_THRESH, j != 0)
                if not response_cells:
                    print "Missed", prompt.question_heading, " for ", url
                elif not response_cells[-1]['source']:
                    pass
                    #print "Blank", prompt.question_heading, " for ", url
                else:
                    #print "response cells length", len(response_cells)
                    #print response_cells[1]['source'], len(response_cells[1]['source'])
                    filtered_cells.extend(response_cells)

        leading, nb_name_full = os.path.split(self.notebook_URLs[0])
        nb_name_stem, extension = os.path.splitext(nb_name_full)

        print "Writing out values"
        fid = open(nb_name_stem + "_responses.ipynb", 'wt')

        answer_book = deepcopy(nbs[self.notebook_URLs[0]])
        answer_book['cells'] = filtered_cells
        json.dump(answer_book, fid)
        fid.close()

    @staticmethod
    def markdown_heading_cell(text, heading_level):
        """ A convenience function to return a markdown cell
            with the specified text at the specified heading_level.
            e.g. mark_down_heading_cell('Notebook Title','#')
        """
        return {u'cell_type': u'markdown',
                u'metadata': {},
                u'source': unicode(heading_level + " " + text)}


class QuestionPrompt(object):
    def __init__(self, question_heading, start_md, stop_md):
        """ Initialize a question prompt with the specified
            starting markdown (the question), and stopping
            markdown (the markdown from the next content
            cell in the notebook).  To read to the end of the
            notebook, set stop_md to the empty string.  The
            heading to use in the summary notebook before
            the extracted responses is contined in question_heading.
            To omit the question heading, specify the empty string.
        """
        self.question_heading = question_heading
        self.start_md = start_md
        self.stop_md = stop_md

    def get_closest_match(self, cells, matching_threshold, suppress_non_answer_cells=False):
        """ Returns a list of cells that most closely match
            the question prompt.  If no match is better than
            the matching_threshold, the empty list will be
            returned. """
        return_value = []
        distances = [Levenshtein.distance(self.start_md, u''.join(cell['source'])) for cell in cells]
        if min(distances) > matching_threshold:
            return return_value

        best_match = argmin(distances)
        if self.stop_md == u"next_cell":
            end_offset = 2
        elif len(self.stop_md) == 0:
            end_offset = len(cells) - best_match
        else:
            distances = [Levenshtein.distance(self.stop_md, u''.join(cell['source'])) for cell in cells[best_match:]]
            if min(distances) > matching_threshold:
                return return_value
            end_offset = argmin(distances)
        if len(self.question_heading) != 0 and not suppress_non_answer_cells:
            return_value.append(NotebookExtractor.markdown_heading_cell(self.question_heading,'##'))
        if not suppress_non_answer_cells:
            return_value.append(cells[best_match])
        return_value.extend(cells[best_match+1:best_match+end_offset])
        return return_value

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "USAGE: ./extract_answers.py ipynb-url problem_set"
        sys.exit(-1)
    question_prompts = []
    if sys.argv[2] == "1":
        question_prompts.append(QuestionPrompt(u"Chapter 1",
                                               u"""### Exercise 3

Type `help()` to start the online help utility. Or you can type help('print') to get information about the print statement.  You should type `q` and then hit `enter` in the text box to exit the help utility. 

Note: this exercise is pretty simple (and there's not much to put in the box)!  We just want to make sure that you have tried out this super-handy feature of Python!""",
                                               u"""next_cell"""))

        question_prompts.append(QuestionPrompt(u"Chapter 1",
                                               u"""### Exercise 4  

Start the Python interpreter and use it as a calculator. Python's syntax for math operations is almost the same as standard mathematical notation. For example, the symbols +, - and / denote addition, subtraction and division, as you would expect. The symbol for multiplication is *.

If you run a 10 kilometer race in 43 minutes 30 seconds, what is your average time per mile? What is your average speed in miles per hour? (Hint: there are 1.61 kilometers in a mile).""",
                                               u"""next_cell"""))
        question_prompts.append(QuestionPrompt(u"Chapter 2",
                                               u"""### Exercise 2  

Assume that we execute the following assignment statements:

width = 17
height = 12.0
delimiter = '.'

For each of the following expressions, write the value of the expression and the type (of the value of the expression).

1. `width/2`
2. `width/2.0`
3. `height/3`
4. `1 + 2 * 5`
5. `delimiter * 5`

Please use the following markdown cell to provide your answer.""",
                                               u"""next_cell"""))
        question_prompts.append(QuestionPrompt(u"""Chapter 2""",
                                               u"""The volume of a sphere with radius r is 4/3 $\pi r^3$. What is the volume of a sphere with radius 5? Hint: 392.7 is wrong!""",
                                               u"""next_cell"""))


        question_prompts.append(QuestionPrompt(u"",
                                               u"""Suppose the cover price of a book is \$24.95, but bookstores get a 40% discount. Shipping costs \$3 for the first copy and 75 cents for each additional copy. What is the total wholesale cost for 60 copies?""",
                                               u"""next_cell"""))

        question_prompts.append(QuestionPrompt(u"",
                                               u"""If I leave my house at 6:52 am and run 1 mile at an easy pace (8:15 per mile), then 3 miles at tempo (7:12 per mile) and 1 mile at easy pace again, what time do I get home for breakfast? """,
                                               u"""next_cell"""))

        question_prompts.append(QuestionPrompt(u"""Chapter 3""",
                                               u"""### Exercise 3

Python provides a built-in function called len that returns the length of a string, so the value of len('allen') is 5.
Write a function named right_justify that takes a string named s as a parameter and prints the string with enough leading spaces so that the last letter of the string is in column 70 of the display.

```
>>> right_justify('allen')
                                                                 allen```""",
                                               u"""next_cell"""))

        question_prompts.append(QuestionPrompt(u"""Chapter 3""",
                                               u"""### Exercise 5

This exercise can be done using only the statements and other features we have learned so far.

(a) Write a function that draws a grid like the following:
```
+ - - - - + - - - - +
|         |         |
|         |         |
|         |         |
|         |         |
+ - - - - + - - - - +
|         |         |
|         |         |
|         |         |
|         |         |
+ - - - - + - - - - +
```
**Hint:** to print more than one value on a line, you can print a comma-separated sequence:
print '+', '-'
If the sequence ends with a comma, Python leaves the line unfinished, so the value printed next appears on the same line.
print '+', 
print '-'
The output of these statements is '+ -'.
A print statement all by itself ends the current line and goes to the next line.""",
                                               u"""next_cell"""))

        question_prompts.append(QuestionPrompt(u"",
                                               u"""(b) Write a function that draws a similar grid with four rows and four columns.""",
                                               u"""next_cell"""))
        question_prompts.append(QuestionPrompt(u"""Chapter 5""",
                                               u"""### Exercise 3  

Fermat's Last Theorem says that there are no positive integers a, b, and c such that $a^n + b^n = c^n$ for any values of n greater than 2.

(a) Write a function named 'check_fermat' that takes four parameters-a, b, c and n-and that checks to see if Fermat's theorem holds. If n is greater than 2 and it turns out to be true that
$a^n + b^n = c^n$ the program should print, "Holy smokes, Fermat was wrong!" Otherwise the program should print, "No, that doesn't work." """,
                                               u"""next_cell"""))
        question_prompts.append(QuestionPrompt(u"",
                                               u"""(b) Write a function that prompts the user to input values for a, b, c and n, converts them to integers, and uses check_fermat to check whether they violate Fermat's theorem.""",
                                               u"""next_cell"""))
        question_prompts.append(QuestionPrompt(u"""Chapter 5""",
                                               u"""### Exercise 4  

If you are given three sticks, you may or may not be able to arrange them in a triangle. For example, if one of the sticks is 12 inches long and the other two are one inch long, it is clear that you will not be able to get the short sticks to meet in the middle. For any three lengths, there is a simple test to see if it is possible to form a triangle:
> If any of the three lengths is greater than the sum of the other two, then you cannot form a triangle. Otherwise, you can. (If the sum of two lengths equals the third, they form what is called a "degenerate" triangle.)

(a) Write a function named 'is_triangle` that takes three integers as arguments, and that prints either "Yes" or "No," depending on whether you can or cannot form a triangle from sticks with the given lengths.""",
                                               u"""next_cell"""))
        question_prompts.append(QuestionPrompt(u"",
                                               u"""(b) Write a function that prompts the user to input three stick lengths, converts them to integers, and uses is_triangle to check whether sticks with the given lengths can form a triangle.""",
                                               u"""next_cell"""))
        question_prompts.append(QuestionPrompt(u"",
        									   u"""## Notes for the Instructors

Please use the space below to write comments to help us plan the next class session.  For instance, if you want to see us go over an example of a particular type of problem, you can indicate that here.

Please remember that the best way to get quick feedback from the instructors as well as your peers, is to use Piazza.  However, consider using this channel if it doesn't make sense to post your note to Piazza.""",
											   u""))


    if not question_prompts:
        print "Unknown problem set"
        sys.exit(-1)

    survey_data = pd.read_csv(sys.argv[1])
    github_usernames = survey_data["...and on GitHub I'm known as"]
    is_valid = []
    for gh_name in github_usernames:
        fid = urllib.urlopen("http://github.com/" + gh_name)
        page = fid.readlines()
        is_valid.append(fid.getcode() == 200)

        if not is_valid[-1]:
            print "Invalid github username", gh_name

    urls = []
    survey_data['valid_github'] = is_valid
    valid_users = survey_data[survey_data.valid_github]["...and on GitHub I'm known as"]
    urls = ["https://raw.githubusercontent.com/" + u + "/ReadingJournal/master/day1_reading_journal.ipynb" for u in valid_users]
    nbe = NotebookExtractor(urls, question_prompts)
    nbe.extract()
