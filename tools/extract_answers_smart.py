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

    def __init__(self, notebook_URLs, notebook_template_file):
        """ Initialize with the specified notebook URLs and
            list of question prompts """
        self.notebook_URLs = notebook_URLs
        self.question_prompts = self.build_question_prompts(notebook_template_file)

    def build_question_prompts(self, notebook_template_file):
        fid = open(notebook_template_file,'r')
        self.template = json.load(fid)
        fid.close()
        prompts = []
        prev_prompt = None
        for c in self.template['cells']:
            print c['metadata']
            if c['metadata'].get('is_question','false') == 'true':
                if prev_prompt != None:
                    prompts[-1].stop_md = u''.join(c['source'])
                prompts.append(QuestionPrompt(question_heading=u"",
                                              start_md=u''.join(c['source']),
                                              stop_md=u'next_cell'))
                if c['metadata'].get('allow_multi_cell','false') == 'true':
                    prev_prompt = prompts[-1]
                else:
                    prev_prompts = None

        return prompts

    def extract(self):
        """ Filter the notebook at the notebook_URL so that it only contains
            the questions and answers to the reading.
        """
        nbs = {}
        for url in self.notebook_URLs:
            fid = urllib.urlopen(url)
            try:
                nbs[url] = json.load(fid)
            except Exception as ex:
                print "error loading", url, ex
                nbs[url] = None
            fid.close()
        filtered_cells = []
        for i, prompt in enumerate(self.question_prompts):
            suppress_non_answer = False
            for j, url in enumerate(nbs):
                if nbs[url] == None:
                    continue
                response_cells = prompt.get_closest_match(nbs[url]['cells'], NotebookExtractor.MATCH_THRESH, suppress_non_answer)
                if not response_cells:
                    print "Missed", prompt.question_heading, " for ", url
                elif not response_cells[-1]['source']:
                    print "Blank", prompt.question_heading, " for ", url
                else:
                    filtered_cells.extend(response_cells)
                    suppress_non_answer = True

        leading, nb_name_full = os.path.split(self.notebook_URLs[0])
        nb_name_stem, extension = os.path.splitext(nb_name_full)

        fid = open(nb_name_stem + "_responses.ipynb", 'wt')

        answer_book = deepcopy(self.template)
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
        print "USAGE: ./extract_answers_smart.py gh_usernames template_notebook_file"
        sys.exit(-1)
    question_prompts = []
    start = sys.argv[2].find('day')
    clipped = sys.argv[2][start:]
    stop = clipped.find('_')
    notebook_number = clipped[3:stop]

    survey_data = pd.read_csv(sys.argv[1])
    github_usernames = survey_data["gh_username"]
    is_valid = []
    for gh_name in github_usernames:
        fid = urllib.urlopen("http://github.com/" + gh_name)
        page = fid.readlines()
        is_valid.append(fid.getcode() == 200)

        if not is_valid[-1]:
            print "Invalid github username", gh_name

    urls = []
    survey_data['valid_github'] = is_valid
    valid_users = survey_data[survey_data.valid_github]["gh_username"]
    urls = ["https://raw.githubusercontent.com/" + u + "/ReadingJournal/master/day" + notebook_number + "_reading_journal.ipynb" for u in valid_users]
    nbe = NotebookExtractor(urls, sys.argv[2])
    nbe.extract()
