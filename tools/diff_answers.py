#!/usr/bin/env python

# Take a student notebook and the starter assignment notebook and return the diff, but separated per problem. This
# lets us see at a glance that the student answered something for each problem.

import json
import os
import sys
from multiprocessing import Pool
from extract_answers_template import get_user_repo_urls, get_user_notebook_urls, read_json_from_url


def get_output_string(output):
    """Return a Jupyter cell's output as a single string; or None."""
    lines = []
    lines.extend(output.get('text', []))
    lines.extend(output.get('data', {}).get('text/plain', []))
    return ''.join(lines)


def get_cell_eq_key(cell):
    """Return an non-mutable object that can be used to distinguish two cells based on their inputs and outputs."""
    return ''.join(cell.get('source', [])), ''.join(map(get_output_string, cell.get('outputs', [])))


def cell_is_keeper(cell):
    return bool(cell['metadata'].get('is_question', None))

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "USAGE: ./diff_answers.py gh_users.csv template_nb_file"
        sys.exit(-1)

    user_repo_urls = get_user_repo_urls(sys.argv[1])
    template_nb_path = sys.argv[2]
    notebook_urls = get_user_notebook_urls(user_repo_urls, template_nb_path)
    with open(template_nb_path) as f:
        template = json.load(f)

    template_cell_indices = set(get_cell_eq_key(cell)
                                for cell in template['cells']
                                if not cell_is_keeper(cell))

    p = Pool(20)
    for notebook_url, nb in zip(notebook_urls, p.map(read_json_from_url, notebook_urls)):
        if not nb:
            continue
        github_username = notebook_url.split('/')[3]  # TODO preserve the name from the list of users
        nb['cells'] = [cell for cell in nb['cells'] if get_cell_eq_key(cell) not in template_cell_indices]
        root, ext = os.path.splitext(os.path.basename(template_nb_path))
        output_path = 'processed_notebooks/{}_{}{}'.format(root, github_username, ext)
        print 'writing', output_path
        with open(output_path, 'w') as f:
            json.dump(nb, f)
