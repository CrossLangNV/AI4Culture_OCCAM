FROM python:3.11.9-bullseye

# The enviroment variable ensures that the pydthon output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

RUN apt-get update

# PDF2Image package
RUN apt-get install -y poppler-utils

# Install needed packages specified in requirements.txt
ADD ./requirements.txt .
RUN pip install -r requirements.txt

# create root directory for our project in the container
RUN mkdir /app
WORKDIR /app

## Copy except the files in .dockerignore
COPY . /app

#ENTRYPOINT ["python3"]
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
