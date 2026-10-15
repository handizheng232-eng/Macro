# Full Python data-test environment

The data suite includes real private-archive acceptance tests. A public checkout
alone is not a substitute for those originals. Do not skip them or synthesize a
research library.

## Inputs, code, and output are different roots

- `REPLAY_RESEARCH_ROOT`: explicit **absolute existing directory containing
  `美国宏观复盘`**. It is not a stage directory. Unset preserves the historical
  repository-local archive layout. Invalid explicit values fail; no sibling
  worktree is searched automatically.
- Code and public outputs remain rooted at this worktree (`REPO_ROOT`). External
  archive configuration does not redirect execution to another checkout.
- External research inputs are read-only. Builder CLI output guards reject writes
  into that root. The dedicated runner also installs a Python audit hook against
  mutations; this is defense in depth, not an OS sandbox for native code.
- Synthetic test PDFs, generated configuration and temporary baseline metadata
  use `tempfile` under private `TMPDIR`, never the original archive or `src/`.
  No original PDF, HTML, or full-text archive is copied into the public checkout.

## Reproducible execution

Use an interpreter with `scripts/requirements-data-tests.txt` installed. The pins
match the versions with which the existing original-page receipts were exercised;
changing PDF extraction versions requires rerunning all page/hash checks.

Bash example (supply your own authorized archive and interpreter paths):

```bash
export REPLAY_RESEARCH_ROOT='/absolute/private/archive-project'
export TMPDIR='/absolute/private/scratch'
export DATA_TEST_PYTHON='/absolute/test-venv/bin/python'
python scripts/run_data_tests.py
```

On Windows use native absolute paths such as `X:/private/archive-project` and
`X:/test-venv/Scripts/python.exe`. `--python` overrides `DATA_TEST_PYTHON`.
The runner uses the selected interpreter, performs **all** `scripts/test_*.py`
discovery, rejects any skips, checks discovered/run counts, and returns nonzero
on missing dependencies or any failed test. It never installs packages or fetches
private sources automatically.

To keep the current package command unchanged, prepend the selected interpreter's
folder to `PATH`, set `REPLAY_RESEARCH_ROOT`, and run `npm run test:data`. For the
stronger runner guard, the package owner can change that script to:

```json
"test:data": "python scripts/run_data_tests.py"
```

Do not make a deployment gate green by accepting a preflight-only result: actual
full discovery and execution must pass. Keep logs outside public build assets.

## Separate generated configuration

The history builder's Python API accepts `configuration_root` for an explicitly
selected temporary admission configuration directory. The parent-source manifest
and its generated presentation-baseline JSON must stay within that directory.
The baseline SHA is still checked. All source books, parent receipts, PDFs,
source artifacts, original bodies, market raw inputs and reviewed research remain
confined to the original evidence stage with their existing hashes and checks.
This is not a second allowlist for originals. Without this option, the prior
stage-local configuration behavior is unchanged. CLI stage restrictions remain
unchanged; synthetic CLI tests set a separate temporary archive root.

No secrets or private source body should be placed in this document, package
configuration, test logs shipped as assets, or committed test fixtures.
