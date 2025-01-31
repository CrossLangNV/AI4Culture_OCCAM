FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

ADD ./requirements.docker.txt .
RUN pip install -r requirements.docker.txt

# https://stackoverflow.com/questions/72980064/from-typing-extensions-import-paramspec-importerror-cannot-import-name-paramsp
RUN pip uninstall -y typing_extensions
RUN pip uninstall -y fastapi
RUN pip install --no-cache fastapi==0.97.0