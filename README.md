# yen

The easiest Python environment manager. Create virtual environments for any Python version, without needing Python pre-installed.

## Installation

Get the tool by running the following command:

- MacOS / Linux:

  ```bash
  curl -L yen.tushar.lol/install.sh | sh
  ```

- Windows:

  ```cmd
  curl -L yen.tushar.lol/install.bat | cmd
  ```

or if you prefer, get it by `pip`:

```bash
pip install yen
```

## Usage

```console
$ yen list
Available Pythons:
3.11.5
3.10.13
3.9.18
3.8.17

$ yen create venv -p 3.11
Downloading 3.11.5 ━━━━━━━━━━━━━━━━━━━━━━━━━ 100.0% • 17.4/17.4 MB • 12.4 MB/s • 0:00:00
Created venv with Python 3.11.5 ✨

By default the python-installation will be done in ~/.yen_pythons.
You can change this location by setting a different path using the environment variable `YEN_PYTHONS_PATH`.

$ source venv/bin/activate

(venv) $ python --version
Python 3.11.5
```

## Local Development / Testing

- Create and activate a virtual environment
- Run `pip install -r requirements-dev.txt` to do an editable install
- Run `pytest` to run tests

## Type Checking

Run `mypy .`

## Create and upload a package to PyPI

Make sure to bump the version in `setup.cfg`.

Then run the following commands:

```bash
rm -rf build dist
python setup.py sdist bdist_wheel
```

Then upload it to PyPI using [twine](https://twine.readthedocs.io/en/latest/#installation):

```bash
twine upload dist/*
```
