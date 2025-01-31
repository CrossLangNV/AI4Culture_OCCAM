# FROM jupyter/base-notebook
FROM jupyter/minimal-notebook:python-3.10

# The enviroment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

USER root

# Install needed packages specified in requirements.txt
ADD ./requirements.txt .
RUN pip install -r requirements.txt

COPY src /tmp/src
#COPY src/setup.py /tmp/setup.py
#COPY src/setup.py /tmp/setup.py
RUN pip install -e /tmp/src/.

# Set the working directory
WORKDIR /lab

# Copy the src code into the container
# ADD ./src /lab
