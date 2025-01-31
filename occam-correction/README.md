# Post-OCR correction

This repository contains code for the correction of OCRed text.

## LLM

We are experimenting with Large Language Models (LLM) for the correction.

These can be further explored in the Jupyter Notebooks

## Installation

```bash
docker compose up -d --build
```

Get the access token from the logs

```bash
docker compose logs -f notebook
```

Go to http://localhost:18888 and enter the access token.