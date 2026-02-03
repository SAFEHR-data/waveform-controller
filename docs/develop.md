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

Even though we are largely running in docker, you may wish to let your IDE have access to a venv for running tests in.

Create the venv in the parent of the repo root and activate it (example for macOS/Linux shown, Windows can differ).
```
uv venv --python=3.13
source .venv/bin/activate
```

From the repo root, install the software and its deps:
```
uv pip install -e '.[dev]'
```

Some tests run in Docker and require the hasher to be configured with dev key vault credentials, which
it likely already is if you've followed the steps in [azure and hasher setup](azure_hashing.md) .

The tests bring up temporary containers as needed, so you don't need to manually pre-start
any containers to make the tests work, and they shouldn't interfere with anything you might already have running.

When these tests run on GitHub Actions, they use GitHub Secrets to get the creds for the dev key vault.

### API tests

from PROJECT_ROOT directory

```shell script
./tools/run-tests.sh
```

## Manual hash lookup

Use `docker ps` to find the ephemeral port of the hasher you are running locally. It should only be listening on
127.0.0.1.

Use curl to send it HTTP requests as below. Don't forget the prefix "csn:" that indicates what type of value you
want to hash.

```bash
# example port 32801
curl 'http://localhost:32801/hash?project_slug=waveform-exporter&message=csn:SECRET_CSN_1235'
ea2fda353f54926ae9d43fbc0ff4253912c250a137e9bd38bed860abacfe03ef
```
