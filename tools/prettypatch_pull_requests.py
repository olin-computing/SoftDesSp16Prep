#!/usr/bin/env python

import argparse
import io
import os
import sys
import subprocess
import github3

PROJECT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
BUILD_DIR = os.path.join(PROJECT_DIR, './build')

GITHUB_API_TOKEN = os.environ.get('HOMEBREW_GITHUB_API_TOKEN')
if GITHUB_API_TOKEN:
    gh = github3.login(token=GITHUB_API_TOKEN)
else:
    print >> sys.stderr, "Warning: GITHUB_API_TOKEN. Github API calls will be rate-limited."
    gh = github3


def file_diff2htmls(patch_file):
    """Returns a string."""
    cmd = os.path.join(PROJECT_DIR, './PrettyPatch/prettify.rb')
    return subprocess.check_output(cmd + ' ' + patch_file, shell=True)


def main(user, repo_name):
    # do this first, to elicit an error before making directories
    repo = gh.repository(user, repo_name)

    # create directories
    repo_build_dir = os.path.join(BUILD_DIR, repo_name)
    patch_dir = os.path.join(repo_build_dir, 'patches')
    html_dir = os.path.join(repo_build_dir, 'html')
    for dirname in ['build', repo_build_dir, patch_dir, html_dir]:
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

    for pr in repo.iter_pulls():
        print pr.user.login

        patch_file = os.path.join(patch_dir, pr.user.login + '.patch')
        with open(patch_file, 'w') as f:
            print >> f, pr.diff()

        html_file = os.path.join(html_dir, pr.user.login + '-patch.html')
        html_diff = file_diff2htmls(patch_file)
        with open(html_file, 'w') as f:
            print >> f, pr.body_html.encode('utf8')
            print >> f, html_diff


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create *.patch and *-patch.html for pull requests.')
    parser.add_argument('user', type=str, metavar='GITHUB_USER')
    parser.add_argument('repo', type=str, metavar='GITHUB_REPO')
    args = parser.parse_args()
    main(args.user, args.repo)
