# How to run tests from

1. Make sure you are in the correct folder
                    
       cd <OCR dir>

1. Get into container
   
       docker-compose exec django bash

1. Run a Django test

    e.g.:
    
       python manage.py test tests.test_get_ocr