# OCCAM Gateway

## Production

Publish the new version of the server:

1. Build the new version of the server:
   ```bash
   docker compose build
   ```

2. Push the new version to the server:
   ```bash
    docker compose push
    ```

## Dev

Start the Django server:

1. Set up the environment variables in `docker-compose.yml`
    1. `DEBUG` to `1`
2. Start the server with:
   ```bash
   docker compose up -d --build
   ```
3. Access the server at `http://localhost:18000`

4. To enter the container:
   ```bash
   docker compose exec web sh
   ```

5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

### New models

Start the service and enter the container.

```
docker compose exec web sh
```

Create a new migration:

```
python manage.py makemigrations
```

Apply the migration:

```
python manage.py migrate
```