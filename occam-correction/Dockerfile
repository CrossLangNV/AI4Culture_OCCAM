# FROM jupyter/base-notebook
FROM jupyter/minimal-notebook:python-3.10

# The enviroment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

USER root

## Install needed packages specified in requirements.txt
#ADD ./src/requirements.txt .
#RUN pip install -r requirements.txt

# try to fix https://stackoverflow.com/questions/64905531/connection-to-the-jupyter-notebook-server-could-not-be-established
RUN pip uninstall -y tornado && pip install tornado==5.1.1

COPY ./notebooks/requirements.txt ./requirements_notebooks.txt
RUN pip install -r requirements_notebooks.txt

# https://stackoverflow.com/questions/71435874/pip-these-packages-do-mot-match-the-hashes-from-the-requirements-file
RUN rm ~/.cache/pip -rf
RUN pip install --no-cache-dir torch==2.1.1

RUN apt-get update && apt-get install -y gcc g++

COPY src /tmp/src
RUN pip install --no-cache-dir -e /tmp/src/.

# Set the working directory
WORKDIR /lab

# Copy the src code into the container
# ADD ./src /lab
