# End-to-End (Playwright) Tests

This folder contains browser-driven tests that exercise the DNSSEC Validator
web interface as a real user would. They run against a fully booted Flask
instance, so they sit outside the default `pytest` collection (which is
configured to ignore `tests/e2e/` via `pytest.ini`).

## When to run

- Before releasing a UI change that touches `app/templates/` or
  `app/static/js/`.
- When validating that the `SHOW_VALIDATION_TLSA_DANE` feature flag still
  toggles the TLSA/DANE result block correctly.
- As a smoke check that `/api/docs/` (Flask-RESTX Swagger UI) renders.

## One-time setup

```bash
source .venv/bin/activate
pip install -r requirements-e2e.txt
playwright install chromium
```

`playwright install chromium` downloads the browser binary into Playwright's
cache (outside the repo). Use `playwright install` to install every supported
browser; the suite only requires Chromium.

## Running the suite

Start the server in one shell:

```bash
source .venv/bin/activate
python app/app.py
```

…then run the e2e tests in another:

```bash
source .venv/bin/activate
pytest tests/e2e --no-cov -p no:cacheprovider
```

`--no-cov` keeps coverage from being collected against `app/` for what are
effectively integration-by-HTTP tests. `-p no:cacheprovider` avoids polluting
`.pytest_cache` with browser-specific data.

### Configuration

| Variable                    | Default                  | Effect                                                                 |
| --------------------------- | ------------------------ | ---------------------------------------------------------------------- |
| `BASE_URL`                  | `http://localhost:8080`  | Target server (e.g. point at a Docker container or staging URL).       |
| `SHOW_VALIDATION_TLSA_DANE` | `false`                  | Must match the server's flag — controls the TLSA/DANE visibility test. |

If the server is not reachable on `BASE_URL`, every test is skipped with a
clear message rather than failing.

### Running a single test

```bash
pytest tests/e2e/test_validation_flow.py::test_validation_flow_renders_chain_of_trust \
    --no-cov -p no:cacheprovider
```

### Headed mode / debugging

```bash
pytest tests/e2e --no-cov -p no:cacheprovider --headed --slowmo 250
```

`pytest-playwright` provides `--browser`, `--headed`, `--slowmo`, and
`--video` switches; see `pytest --help | grep playwright` for the full list.

## Why are these tests opt-in?

- They require an extra ~300 MB download (Chromium).
- They need a running server, which is awkward in the default unit-test CI
  job.
- They are not counted toward unit/integration coverage targets.

The default quality gate (`pytest tests/`) is unchanged: `pytest.ini` lists
`--ignore=tests/e2e` and `norecursedirs = tests/e2e ...`, so this suite is
never collected unless you point pytest at it directly.
