#FROM ubuntu:18.04
#gpu
FROM nvidia/cuda:10.0-cudnn7-devel-ubuntu18.04

MAINTAINER arne <arnedefauw@gmail.com>

# Install some basic utilities
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    sudo \
    git \
    bzip2 \
    libx11-6 \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# Install miniconda to /miniconda
RUN curl -LO http://repo.continuum.io/miniconda/Miniconda3-py37_4.8.2-Linux-x86_64.sh
RUN bash Miniconda3-py37_4.8.2-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda3-py37_4.8.2-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda

RUN conda install -y python=3.7.3 && \
conda install flask==1.1.1 && \
conda install --name base scikit-learn=0.20.0 && \
conda install pytorch==1.4.0 cudatoolkit=10.0 -c pytorch && \
#conda install pytorch==1.4.0 cpuonly -c pytorch &&\
conda install -y -c conda-forge opencv==4.2.0 && \
conda install -c conda-forge hdbscan==0.8.26 && \
conda install -c conda-forge pillow==7.1.2

#Cython 
#RUN apt-get update
#RUN apt-get -y install --reinstall build-essential && \
#RUN apt-get -y install gcc

RUN pip install Cython==0.29.15 \
                numpy==1.18.1 \
                opencv-python==4.2.0.32 \
                lxml==4.5.0 \
                scipy==1.4.1 \
                numba==0.48.0 \
                brnolm==0.1.1 \
                scikit-image==0.16.2 \
                tensorflow-gpu==1.14.0 \           
                Shapely==1.7.0 \
                pyamg==4.0.0 \
                green==3.1.0 \
                #hdbscan==0.8.26 \
                Django==3.0.5 \
                django-braces==1.14.0 \
                django-cleanup==4.0.0 \
                django-cors-headers==3.2.1 \
                django-crispy-forms==1.9.0 \
                django-oauth-toolkit==1.3.2 \
                django-rest-framework-social-oauth2==1.1.0 \
                djangorestframework==3.11.0 \
                jedi==0.15.2 \
                parso==0.5.2 \
                scikit-learn==0.22.2 \
                gunicorn==20.0.4 \
                pandas==1.0.1 \
                drf-yasg==1.17.0 \
                ipython \
                jupyter

# Set the working directory to e.g. /django
WORKDIR /backend

# Copy App
COPY . .

RUN chmod +x start.sh

#CMD python /django/manage.py makemigrations && python /django/manage.py migrate && python /django/manage.py runserver 0.0.0.0:5000
