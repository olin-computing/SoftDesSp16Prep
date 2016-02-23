# SoftDesSp16Prep
This is for instructors to work on tools or assignments for the Software Design Spring 2016 course at Olin College.

## Usage

    ./tools/extract_answers_template.py GH_USERNAMES_CSV TEMPLATE_NOTEBOOK_FILE

Creates a Jupyter notebook in `./processed_notebooks`.
The notebook is based on the notebook at `TEMPLATE_NOTEBOOK_FILE`.
The tool searches each of the repositories
in `GH_USERNAMES_CSV` (a CSV file with a `gh_username` column) for notebooks with the same name, and collects
their respones.

    ./tools/diff_answers.y GH_USERNAMES_CSV TEMPLATE_NOTEBOOK_FILE

Take a student notebook and the starter assignment notebook and return the diff, but separated per problem.
This lets us see at a glance that the student answered something for each problem.

    ./tools/prettypatch_pull_requests.py GITHUB_USER GITHUB_REPO

## Install

    pip install -r requirements.txt

(`summarize_pull_request_patches.py` only:)
Set `HOMEBREW_GITHUB_API_TOKEN` to avoid Github's rate limit.

