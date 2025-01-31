#nvidia-docker run -it --rm -p 5000:5000 --entrypoint /bin/bash -v $PWD:/django django_pero_ocr
nvidia-docker run -it --rm -p 5000:5000 -v $PWD:/django django_pero_ocr

