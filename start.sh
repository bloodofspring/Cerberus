#! /usr/bin/bash
touch start_log.txt
git pull

if python 2> start_log.txt
then echo "Python detected" && echo "creating env..." && python -m venv .venv
else echo "No python detected. Searching for python3..."
fi

if python3 2> start_log.txt
then echo "Python3 detected" && echo "creating env..." && python3 -m venv .venv
else echo "No python3 detected. Searching for python3..."
fi

if cd .venv/bin 2> start_log.txt
then
  echo "Installing requirements.txt..."
  pip install -r requirements.txt
  echo "Starting code..."
  python run.py
else "No virtual environment!"
fi
