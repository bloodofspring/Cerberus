#! /usr/bin/bash
git pull
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
