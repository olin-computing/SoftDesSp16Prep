#!/usr/bin/env python

import argparse
import os
import sys
import subprocess
import github3


GITHUB_API_TOKEN = os.environ.get('HOMEBREW_GITHUB_API_TOKEN')
if GITHUB_API_TOKEN:
    gh = github3.login(token=GITHUB_API_TOKEN)
else:
    gh = github3


def main(user, repo_name):
    # create directories
    build_dir = os.path.join('build', repo_name)
    patch_dir = os.path.join(build_dir, 'patches')
    html_dir = os.path.join(build_dir, 'html')
    for dirname in ['build', build_dir, patch_dir, html_dir]:
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

    repo = gh.repository(user, repo_name)
    for pr in repo.iter_pulls():
        print pr.user.login

        patch_file = os.path.join(patch_dir, pr.user.login + '.patch')
        with open(patch_file, 'w') as f:
            print >> f, pr.diff()

        html_file = os.path.join(html_dir, pr.user.login + '-patch.html')
        with open(html_file, 'w') as f:
            print >> f, pr.body_html
        cmd = 'ruby PrettyPatch/prettify.rb ' + patch_file + ' >> ' + html_file
        status = subprocess.call(cmd, shell=True)
        if status:
            print 'status=%d:' % status, cmd
            sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create *.patch and *-patch.html for pull requests.')
    parser.add_argument('user', type=str, metavar='GITHUB_USER')
    parser.add_argument('repo', type=str, metavar='GITHUB_REPO')
    args = parser.parse_args()
    main(args.user, args.repo)
