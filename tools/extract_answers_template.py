#!/usr/bin/env python
""" This script is designed to support active reading.  It takes as input
    a set of ipython notebook as well as some target cells which define a set
    of reading exercises.  The script processes the collection of notebooks
    and builds a notebook which summarizes the responses to each question.
"""

import argparse
import json
import os
import re
import sys
import urllib
from collections import OrderedDict
from copy import deepcopy
from multiprocessing import Pool
from numpy import argmin
import Levenshtein
import pandas as pd


def read_json_from_url(url):
    """Given an URL, return its contents as JSON; or None if no JSON exists at that URL.

    Prints exceptions except 404.

    This is a global function so that it can be used as an argument to `p.map`"""

    fid = urllib.urlopen(url)
    try:
        if 200 <= fid.getcode() <= 299:
            return json.load(fid)
    except Exception as ex:
        print >> sys.stderr, "error loading {}: {}".format(url, ex)
    finally:
        fid.close()
    return None


class NotebookExtractor(object):
    """ The top-level class for extracting answers from a notebook.
        TODO: add support multiple notebooks
    """

    MATCH_THRESH = 10  # maximum edit distance to consider something a match

    def __init__(self, notebook_URLs, notebook_template_file, include_usernames=False):
        """ Initialize with the specified notebook URLs and
            list of question prompts """
        self.notebook_URLs = notebook_URLs
        self.question_prompts = self.build_question_prompts(notebook_template_file)
        self.include_usernames = include_usernames

    def build_question_prompts(self, notebook_template_file):
        """Returns a list of `QuestionPrompt`. Each cell with metadata `is_question` truthy
        produces an instance of `QuestionPrompt`."""
        with open(notebook_template_file, 'r') as fid:
            self.template = json.load(fid)
        prompts = []
        prev_prompt = None
        for idx, c in enumerate(self.template['cells']):
            if c['metadata'].get('is_question', False):
                if prev_prompt is not None:
                    prompts[-1].stop_md = u''.join(c['source'])
                prompts.append(QuestionPrompt(question_heading=u"",
                                              start_md=u''.join(c['source']),
                                              stop_md=u'next_cell',
                                              is_poll=c['metadata'].get('is_poll', False)
                                              ))
                if c['metadata'].get('allow_multi_cell', False):
                    prev_prompt = prompts[-1]
                    # if it's the last cell, take everything else
                    if idx + 1 == len(self.template['cells']):
                        prompts[-1].stop_md = u""
                else:
                    prev_prompt = None
        return prompts

    def fetch_notebooks(self):
        """Returns a dictionary {github_username -> url, json?}.

        Unavailable notebooks have a value of None."""

        def repo_url_to_github_username(url):
            return url.split('/')[3]  # TODO pass the username in instead of recovering it

        p = Pool(20)  # HTTP fetch parallelism. This number is empirically good.
        print "Retrieving %d notebooks" % len(self.notebook_URLs)
        return dict(zip(map(repo_url_to_github_username, self.notebook_URLs),
                        p.map(read_json_from_url, self.notebook_URLs)))

    def extract(self):
        """ Filter the notebook at the notebook_URL so that it only contains
            the questions and answers to the reading.
        """

        nbs = self.fetch_notebooks()
        if self.include_usernames:
            # Sort by username iff including the usernames in the output.
            # This makes it easier to find students.
            nbs = OrderedDict(sorted(nbs, key=lambda t: t[0].lower()))

        filtered_cells = []
        for prompt in self.question_prompts:
            suppress_non_answer = False
            answer_strings = set()  # answers to this question, as strings; used to avoid duplicates
            for gh_username, notebook_content in nbs.items():
                if notebook_content is None:
                    continue
                response_cells = \
                    prompt.get_closest_match(notebook_content['cells'],
                                             NotebookExtractor.MATCH_THRESH,
                                             suppress_non_answer)
                if not response_cells:
                    print "Missed", prompt.question_heading, "for", gh_username
                elif not response_cells[-1]['source']:
                    print "Blank", prompt.question_heading, "for", gh_username
                else:
                    answer_string = "\n".join("".join(cell['source']) for cell in response_cells).strip()
                    if self.include_usernames:
                        title = "#### " + gh_username
                        filtered_cells.append({'cell_type': 'markdown', 'source': [title], 'metadata': {}})
                    elif not answer_string:
                        continue
                    elif not prompt.is_poll and answer_string in answer_strings:
                        continue
                    answer_strings.add(answer_string)
                    filtered_cells.extend(response_cells)
                    suppress_non_answer = True

        leading, nb_name_full = os.path.split(self.notebook_URLs[0])
        nb_name_stem, extension = os.path.splitext(nb_name_full)

        output_dir = os.path.join(os.path.dirname(__file__), "../processed_notebooks")
        suffix = "_responses_with_names" if self.include_usernames else "_responses"
        output_file = os.path.join(output_dir, nb_name_stem + suffix + ".ipynb")
        print "Writing", output_file
        with open(output_file, 'wt') as fid:
            answer_book = deepcopy(self.template)
            answer_book['cells'] = filtered_cells
            json.dump(answer_book, fid)

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

    def __init__(self, question_heading, start_md, stop_md, is_poll=False):
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
        self.is_poll = is_poll

    def get_closest_match(self,
                          cells,
                          matching_threshold,
                          suppress_non_answer_cells=False):
        """ Returns a list of cells that most closely match
            the question prompt.  If no match is better than
            the matching_threshold, the empty list will be
            returned. """
        return_value = []
        distances = [Levenshtein.distance(self.start_md,
                                          u''.join(cell['source']))
                     for cell in cells]
        if min(distances) > matching_threshold:
            return return_value

        best_match = argmin(distances)
        if self.stop_md == u"next_cell":
            end_offset = 2
        elif len(self.stop_md) == 0:
            end_offset = len(cells) - best_match
        else:
            distances = [Levenshtein.distance(self.stop_md,
                                              u''.join(cell['source']))
                         for cell in cells[best_match:]]
            if min(distances) > matching_threshold:
                return return_value
            end_offset = argmin(distances)
        if len(self.question_heading) != 0 and not suppress_non_answer_cells:
            return_value.append(NotebookExtractor.markdown_heading_cell(
                self.question_heading, '##'))
        if not suppress_non_answer_cells:
            return_value.append(cells[best_match])
        return_value.extend(cells[best_match + 1:best_match + end_offset])
        return return_value


def validate_github_username(gh_name):
    """Return `gh_name` if that Github user has a `repo_name` repository; else None."""
    fid = urllib.urlopen("http://github.com/" + gh_name)
    fid.close()
    return gh_name if 200 <= fid.getcode() <= 299 else None


def validate_github_usernames(gh_usernames, repo_name):
    """Returns a set of valid github usernames.

    A name is valid iff a GitHub user with that name exists, and owns a repository named `repo_name`.

    `gh_usernames_path` is a path to a CSV file with a `gh_username` column.

    Prints invalid names as errors."""
    p = Pool(20)
    valid_usernames = filter(None, p.map(validate_github_username, gh_usernames))
    invalid_usernames = set(gh_usernames) - set(valid_usernames)
    if invalid_usernames:
        print >> sys.stderr, "Invalid github username(s):", ', '.join(invalid_usernames)
    return valid_usernames


def get_github_user_raw_repo_url(gh_username, repo_name):
    return "https://raw.githubusercontent.com/{username}/{repo_name}".format(username=gh_username, repo_name=repo_name)


def get_github_user_notebook_url(gh_username, template_nb_path, repo_name):
    m = re.match(r'.*day(\d+)_', template_nb_path)
    assert m, "template file must include day\d+_"
    notebook_number = m.group(1)
    notebook_filename = "day{}_reading_journal.ipynb".format(notebook_number)
    repo_url = get_github_user_raw_repo_url(gh_username, repo_name)
    return "{repo_url}/{branch}/{path}".format(repo_url=repo_url, branch="master", path=notebook_filename)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Summarize a set of Jupyter notebooks.')
    parser.add_argument('--repo', type=str, default='ReadingJournal', help='Github repository name')
    parser.add_argument('--include-usernames', action='store_true', help='include user names in the summary notebook')
    parser.add_argument('gh_users', type=str, metavar='GH_USERNAME_CSV_FILE')
    parser.add_argument('template_notebook', type=str, metavar='JUPYTER_NOTEBOOK_FILE')
    args = parser.parse_args()

    repo_name = args.repo
    github_username_csv = pd.read_csv(args.gh_users)
    github_usernames = validate_github_usernames(github_username_csv["gh_username"], repo_name)

    template_nb_path = args.template_notebook
    notebook_urls = [get_github_user_notebook_url(u, template_nb_path, repo_name) for u in github_usernames]
    nbe = NotebookExtractor(notebook_urls, template_nb_path, include_usernames=args.include_usernames)
    nbe.extract()
