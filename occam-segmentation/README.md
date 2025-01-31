# OCCAM Segmentation API

## Overview
The OCCAM Segmentation API provides text segmentation functionalities, including sentence extraction from lines and Okapi-based segmentation.

## Getting Started

### Running the API
1. Set up the required environment variables in `.env`.
2. Build and start the server:
   ```bash
   docker compose up -d --build
   ```
3. Access the API at `http://localhost:8000`.

### API Endpoints
- **Health Check**: `GET /health`
- **Sentence Extraction**: `POST /process/tools/sentence_from_lines`
- **File-based Sentence Extraction**: `POST /process/tools/sentence_from_lines/file`
- **Okapi Segmentation**: `POST /process/tools/okapi_segmentation`
- **Pipeline Processing**: `POST /process/pipeline`

## Documentation
For full API details, visit:
[http://localhost:8000/docs](http://localhost:8000/docs).
