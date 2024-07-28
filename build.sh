#!/bin/bash
python -m pip install --upgrade pip==22.0.4
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
