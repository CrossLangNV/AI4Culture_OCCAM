# OCCAM Gateway API

## Getting Started

### Start the Server
1. Create an `.env` file based on `secrets/.env.sample` and fill in the required values.
2. Set up environment variables in `docker-compose.yml`.
3. Build and start the server:
   ```bash
   docker compose up -d --build
   ```
4. Access the server at `http://localhost:18000`.

### Managing the Server
- Enter the container:
   ```bash
   docker compose exec web sh
   ```
- Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
- Create and apply new migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

## Key Components

### Services
- **Web (Django App)**: Runs the OCCAM Gateway API.
- **Nginx**: Serves as a reverse proxy, handling requests and forwarding them to the Django backend.
- **Celery Workers**: Process OCR and translation tasks asynchronously.
- **Redis**: Acts as a message broker for Celery.

### Modules
- **Core**: Handles user management functionality.
- **Correction**: Implements post-OCR correction methods including:
  - Manual correction
  - LLM-based correction
  - SymSpell-based correction
  - SymSpell + Flair hybrid correction
- **Evaluation**: OCR evaluation powered by [Dinglehopper](https://github.com/qurator-spk/dinglehopper).
- **Segmentation**: Handles document segmentation.
- **Translation**: Integrates with CEF eTranslation for multilingual text translation.

### Authentication
- Uses JWT-based authentication (`rest_framework_simplejwt`).
- API keys can be used as an alternative authentication method.

### OCR & Translation
- The API includes OCR correction and text translation functionalities.
- Tasks are processed asynchronously using Celery and Redis queues.
- URLs for connected services (eTranslation, correction, segmentation) must be configured in `.env`.

### Logging
- Logs are output to the console with different verbosity levels based on `DEBUG` mode.

### Database
- Uses SQLite by default but can be configured to use PostgreSQL or another database.

## API Documentation
For available endpoints and usage, visit the Swagger documentation at:
[http://localhost:8000/docs](http://localhost:8000/docs).
