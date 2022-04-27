python -m pip install --upgrade pip
pip install black flake8 isort pylint mypy

black --check .

isort --profile black .

flake8 . --max-line-length 88 --extend-ignore E203 --select B950

pylint main.py --disable C0330,C0301,E0401,E1136,R0914

mypy .