#!/usr/bin/env python

import re
import os
from glob import glob

import flask
from flask import Flask

import nbformat
import nbconvert
import pandas as pd

COURSE_NAME = 'SoftDes'

PROJECT_DIR = os.path.dirname(__file__)
SUMMARY_DIR = os.path.join(PROJECT_DIR, 'summaries')

DATAFRAME_TABLE_CLASSES = 'table-condensed table-striped table-hover'

RESPONSE_SUMMARY_PATH_TEMPLATE_RE = re.compile(
    r'(.+)_reading_journal_(.+)(?:responses|response_counts)?(?:_with_names).csv')


app = Flask(__name__)

pd.set_option('display.max_colwidth', -1)

assignments = {}

for path in glob(os.path.join(SUMMARY_DIR, '*.csv')):
    m = RESPONSE_SUMMARY_PATH_TEMPLATE_RE.match(os.path.basename(path))
    if not m:
        continue
    assignment_id, summary_type = m.groups()
    assignment_name = assignment_id.replace('day', 'day ').capitalize()
    df = pd.read_csv(path, index_col=0)
    assignment = assignments.get(assignment_id)
    if not assignment:
        assignment = (assignment_id, assignment_name, [])
        assignments[assignment_id] = assignment
    assignment[2].append((summary_type, df))


def natural_sort_key(s):
    int_re = re.compile(r'(-?\d+)')
    return tuple(int(c) if int_re.match(c) else c
                 for c in int_re.split(s))


@app.route('/')
def index():
    return flask.render_template(
        'index.html',
        title=COURSE_NAME,
        assignments=sorted(assignments.values(), key=lambda t: natural_sort_key(t[1]))
    )


@app.route('/assignment/<assignment_id>')
def assignment(assignment_id):
    def summary_type_to_title(s):
        return s.replace('_', ' ').capitalize()
    assignment_name = assignments[assignment_id][1]
    tables = [(summary_type_to_title(summary_type), df.to_html(classes=DATAFRAME_TABLE_CLASSES))
              for summary_type, df in assignments[assignment_id][2]]
    return flask.render_template(
        'assignment.html',
        assignment_id=assignment_id,
        title=COURSE_NAME + ' ' + assignment_name,
        tables=tables)


@app.route('/assignment/<assignment_id>/processed')
def processed_notebook(assignment_id):
    with open('processed_notebooks/%s_reading_journal_responses.ipynb' % assignment_id) as f:
        nb = nbformat.reads(f.read(), as_version=4)
    str, _ = nbconvert.export_html(nb)
    assignment_name = assignments[assignment_id][1]
    title = ' '.join([COURSE_NAME, assignment_name, 'Processed Notebook'])
    return flask.render_template('processed_notebook.html', title=title, nb_html=str)


if __name__ == '__main__':
    app.run(debug=True)
