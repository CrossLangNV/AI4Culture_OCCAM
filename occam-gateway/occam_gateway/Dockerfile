FROM python:3.11.9-bullseye

# The enviroment variable ensures that the pydthon output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PIP_NO_CACHE_DIR=1

RUN apt-get update \
	&& apt-get install -y --no-install-recommends poppler-utils openssh-client \
	&& rm -rf /var/lib/apt/lists/*

# Install needed packages specified in requirements.txt
COPY ./requirements.txt ./
RUN pip install --upgrade pip \
	&& pip install -r requirements.txt

# create root directory for our project in the container
WORKDIR /app

## Copy except the files in .dockerignore
COPY . /app

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "120", "occam_gateway.wsgi:application"]
