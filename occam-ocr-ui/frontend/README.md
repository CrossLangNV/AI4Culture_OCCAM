# OCCAM OCR UI

A single-page React application that:
- **Performs OCR on image files** (PDF support is not included).
- **Applies post-OCR text corrections** (manual transcription or automated approaches).
- **Translates** extracted text into multiple languages.
- **Allows in-browser viewing and downloading** of results.
- **Supports** JWT or API Key authentication with the backend.

---

## Overview

**OCCAM OCR UI** is designed as the front-end interface for an OCR workflow, communicating with a backend that offers:
- Image-based OCR
- Automated correction (e.g., SymSpell, Flair, LLM)
- Translation APIs

This project uses:
- [React](https://reactjs.org/) + [React Redux](https://react-redux.js.org/) for state management
- [PrimeReact](https://primereact.org/) for UI components (FileUpload, Dialog, Buttons, etc.)
- [Axios](https://axios-http.com/) with interceptors for secure HTTP requests
- [JSZip](https://stuk.github.io/jszip/) for bundling results for download
- [xml2js](https://www.npmjs.com/package/xml2js) for parsing PageXML outputs
- [js-file-download](https://www.npmjs.com/package/js-file-download) for triggering browser downloads

---

## Prerequisites

- **Node.js** (v14 or higher)
- **npm** (v6 or higher) or **Yarn** (v1 or higher)
- **OCR-enabled backend** that accepts image files and returns OCR data (PDF OCR is not supported by this UI).
- **API Key** or **JWT token** (if your backend requires authentication).

---

## Installation

1. **Clone or download** this repository:

2. **Navigate** into the project folder:
   ```bash
   cd occam-ocr-ui
   ```
3. **Install dependencies**:
   ```bash
   npm install
   ```
   or
   ```bash
   yarn install
   ```

---

## Configuration

### Environment Variables

Set environment variables in a `.env` or `.env.local` file at the project root. Example:

```bash
REACT_APP_API_URL=<API_URL>
REACT_APP_DJANGO_CLIENT_ID=<DJANGO_CLIENT_ID>
REACT_APP_DJANGO_CLIENT_SECRET=<DJANGO_CLIENT_SECRET>
REACT_APP_VERSION=<VERSION>
REACT_APP_API_KEY=<API_KEY>
```

These values can be accessed in the code (e.g., `process.env.REACT_APP_API_BASE_URL`) and passed through an **Axios** interceptor or directly in requests for authentication.

### Docker Deployment

- `Dockerfile` and `DockerfileDebug` are included for container-based deployments.
- If you need dynamic environment variables, consider using `env.sh` or `env-config.js`.

---

## Usage

### Development Mode

Start a local development server, typically at `http://localhost:3000`:

```bash
npm start
```
or
```bash
yarn start
```

The application will hot-reload whenever you save changes in the source code.

### Production Build

To create an optimized build of the UI in the `build` folder:

```bash
npm run build
```
or
```bash
yarn build
```

You can then serve the contents of `build` on any static hosting service (e.g., Nginx, Netlify, AWS S3).

---

## Project Structure

Below is the core layout of the **frontend** directory. Key folders inside `src` are highlighted:

```
frontend/
├── Dockerfile
├── DockerfileDebug
├── env-config.js
├── env.sh
├── license_report.html
├── license_report_config.json
├── nginx/
├── node_modules/
├── package.json
├── package-lock.json
├── public/
└── src/
    ├── actions/
    ├── assets/
    │   ├── css/
    │   │   ├── app/
    │   │   ├── demo/
    │   │   └── themes/
    │   └── images/
    ├── constants/
    ├── containers/
    │   ├── core/
    │   ├── ocr/         <-- Main OCR logic in Ocr.js
    │   └── utils/
    ├── interceptors/    <-- Axios interceptors and request config
    ├── locales/         <-- i18n files (English, French, Dutch)
    ├── reducers/
    ├── themes/
    └── utils/
```

- **`src/containers/ocr/Ocr.js`** – The core OCR component for:
  - Image upload
  - OCR calls to the backend
  - Text correction (manual or automated)
  - Optional translation of text
  - Downloading results (text, PageXML, etc.)

---

## License

```
MIT License
```

For more details, see the `LICENSE` file in this repository.
