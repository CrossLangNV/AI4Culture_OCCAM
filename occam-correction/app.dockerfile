FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

## Install needed packages specified in requirements.txt
COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip3 install torch==2.1.1 --index-url https://download.pytorch.org/whl/cpu

COPY ./src/requirements.txt ./requirements_src.txt
RUN pip install -r requirements_src.txt

# Local python package
COPY ./src /tmp/src
RUN pip install --no-cache-dir -e /tmp/src/.

WORKDIR /app/

COPY app/app /app/app
ENV PYTHONPATH=/app
