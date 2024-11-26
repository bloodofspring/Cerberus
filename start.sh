#! /usr/bin/bash
touch start_log.txt
git pull

if python -V 2> start_log.txt
then
  echo "Python detected"
  echo "creating virtual environment..."
  python -m venv .venv || echo "Error while creating .venv"
else
  echo "No python detected. Searching for python3..."
  if python3 -V 2> start_log.txt
  then
    echo "Python3 detected"
    echo "Python detected"
    echo "creating virtual environment..."
    python -m venv .venv || echo "Error while creating .venv"
  else echo "No python3 detected!"
fi
fi

if [ -d "$.venv" ]
then
  echo "Installing requirements.txt..."
  .venv/bin/pip install -r requirements.txt
  echo "Starting code..."
  .venv/bin/python run.py
else "No virtual environment!"
fi
