# Developing the code

## Branches

- `main`: tested and stable version used for releases (runs on the prod environment on the GAE).
- `dev`: testing area before merging into `main` (runs on the staging environment on the GAE).
- Your work on feature branches

You should make a new branch for each feature and use pull requests to `dev` to test it live, then pull requests to `main` once it is fully reviewed and tested.

Branch naming convention:
`<area of code>/<issue number>-name-of-feature` e.g. `api/1003-spc-pain`
with the `<area of code>` being api or ui for features or bugfix for bugs.

Informative commit messages appear in the `git tag` description which we use as release notes and should be comprehensible by the clinicians.

## Code style

Please run the [`pre-commit` command](https://pre-commit.com) from the
PROJECT_ROOT directory before committing any code. This will run automatic code
formatting and check python style and type hints.

```
git add <your files>
pre-commit run
git commit -m <what you changed>
```

Alternatively you can use pre-commit (the tool) to install a git pre-commit hook
which runs the suite of linters and code formatters before every commit.

```
ls .git/hooks | grep -v .sample # just to check what is installed already
pre-commit install  # invoke the tool
ls .git/hooks | grep -v .sample # should now see a new pre-commit hook
```

At the moment, we're using:

- [`ruff` and `ruff-format`](https://docs.astral.sh/ruff/) for python code formatting,
- [nbstribout](https://github.com/kynan/nbstripout) to clear notebook output.
- A small selection of line-endings fixers.

If you want to run them individually you can do so with:

```
pre-commit run ruff-format --all
```

for example. This should be equivalent to just running the tool standalone:

```
ruff-format api/
```

Noting that pre-commit handles some arguments for you (so it's probably better
to use that for consistency).

### Problems with pre-commit?

If the linters are flagging false positives, you can remove them or comment them
out in [the configuration](./.pre-commit-config.yaml). If you've accidentally
commited something that is failing the linting step in CI, you can fix this
with:

```
git pull # just to be sure
pre-commit run --all
git add -u
git commit -m "Making pre-commit pass."
git push
```

## Testing

No tests yet.
### API tests

from PROJECT_ROOT directory

```shell script
./tools/run-tests.sh
```
