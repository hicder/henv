# henv

A lightweight local environment manager, similar to `venv`. It keeps project-specific tool shims in `.hicder/bin` and, if [direnv](https://direnv.net/) is installed, puts that directory on `PATH`.

## Install

```bash
pip install -e .
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install -e .
```

Requires Python 3.9+.

## Usage

### `henv init`

From the project directory:

```bash
henv init
```

This will:

- Create `.hicder/bin` if it does not exist
- If `direnv` is on `PATH`:
  - Create `.envrc` if it does not exist, with `PATH_add .hicder/bin` as the first line
  - Prepend that line if `.envrc` already exists and does not start with it
  - Run `direnv allow`

If `direnv` is not installed, `.hicder/bin` is still created and `.envrc` is skipped.

### `henv bin`

Create a symlink under `.hicder/bin`:

```bash
henv bin clang /opt/homebrew/opt/llvm@17/bin/clang
```

That makes `.hicder/bin/clang` point at the given binary. An existing symlink with the same name is replaced.

After `init`, direnv adds `.hicder/bin` to `PATH`, so `clang` in this directory resolves to the linked tool.

### `henv env`

Set a variable in `.envrc`:

```bash
henv env FOO bar
henv env CMAKE_EXTRA_ARGS '-DCMAKE_OSX_SYSROOT=$SDKROOT'
```

That writes `export FOO=bar`. Values may start with `-`. Use single quotes if the value should keep `$VARS` for direnv to expand later. If the variable is already exported, the existing line is replaced. After any change to `.envrc`, `direnv allow` is run if `direnv` is on `PATH`.

### `henv unenv`

Remove a variable from `.envrc`:

```bash
henv unenv FOO
```

That deletes the `export FOO=...` line. If `.envrc` changed, `direnv allow` is run if `direnv` is on `PATH`.

## Layout

```
.
├── .envrc          # PATH_add .hicder/bin
└── .hicder/
    └── bin/
        └── clang   # symlink to the real binary
```
