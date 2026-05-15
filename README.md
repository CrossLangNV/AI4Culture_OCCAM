# AI4Culture OCCAM

## Overview
AI4Culture OCCAM is a modular system providing multilingual text recognition and processing tools. It integrates multiple services for OCR, text correction, translation, and segmentation.

## Repositories
The system consists of the following components:

### 1. **eTranslation-connector**
   - Connects to CEF eTranslation services for multilingual translation.
   
### 2. **occam-correction**
   - Provides multiple text correction methods, including SymSpell, LLM-based, and hybrid correction approaches.
   
### 3. **occam-gateway**
   - Acts as the main API gateway, orchestrating requests between different OCCAM modules.
   
### 4. **occam-ocr-ui/frontend**
   - A web-based user interface for interacting with OCCAM's OCR and text processing features.
   
### 5. **occam-pero-ocr**
   - OCR processing module based on the Pero OCR engine, used for text recognition in scanned documents.
   
### 6. **occam-segmentation**
   - Provides sentence and text segmentation functionalities using Okapi-based processing.
   
## Getting Started

### Running the System
Each service runs independently and requires specific configurations. Ensure you set up the necessary `.env` files and follow installation steps within each repository.

1. Clone all repositories.
2. Set up environment variables as per each service's requirements.
3. Start individual services using Docker Compose:
   ```bash
   docker compose up -d --build
   ```

## Release Builds

The checked-in `docker-compose.yml` files are mainly convenient for local/dev usage. For publishing immutable images, build the API and UI directly from this monorepo:

```bash
cd /path/to/AI4Culture_OCCAM
REGISTRY=docker2.crosslang.com \
NAMESPACE=ai4c \
API_IMAGE_NAME=occam-gateway-jwt \
UI_IMAGE_NAME=occam-ocr-ui-jwt \
TAG=2026-05-15 \
bash ./build-release-images.sh
```

This produces two images:
- the gateway API image from `occam-gateway/occam_gateway`
- the OCR UI image from `occam-ocr-ui/frontend`

The script only builds locally. Push to the registry yourself once you have validated the tags.

## API Documentation
For API details, refer to the documentation provided by each module. The main gateway API documentation is available at:
[http://localhost:18000/docs](http://localhost:18000/docs).
