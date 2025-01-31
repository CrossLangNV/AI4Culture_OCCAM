import asyncio
import os
import unittest

import requests


class RequestsClient(requests.Session):
    def __init__(self, base_url=None):
        super().__init__()
        self.base_url = base_url

    def request(self, method, url, **kwargs):
        url = self.base_url + url
        return super().request(method, url, **kwargs)


if 0:
    # FastAPI test client
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
else:
    # Remote server
    if 1:
        URL_HOME = 'http://localhost:9065'  # Local
    else:
        URL_HOME = 'http://192.168.105.41:9065'  # GPU server
    client = RequestsClient(URL_HOME)

FILENAME_IMAGE = os.path.join(os.path.dirname(__file__), 'test image.jpg')
FILENAME_IMAGE2 = os.path.join(os.path.dirname(__file__), 'test image handwritten.jpg')

FILENAMES = [FILENAME_IMAGE,
             FILENAME_IMAGE2]


class TestAPI(unittest.TestCase):
    url = '/ocr'

    def test_ocr_post(self):

        with open(FILENAME_IMAGE, 'rb') as f:
            files = {'image': f}
            response = client.post(self.url,
                                   files=files)

        self.assertTrue(response.ok, [response, response.content])

        print(response.json())

        self._assert_response(response)

    def test_post_multiple_in_series(self):

        for filename_image in [FILENAME_IMAGE,
                               FILENAME_IMAGE2,
                               FILENAME_IMAGE
                               ]:
            with open(filename_image, 'rb') as f:
                files = {'image': f}
                response = client.post(self.url,
                                       files=files)

            with self.subTest(str(filename_image)):
                self._assert_response(response)

    def test_post_a_lot_in_series(self, n=10):

        for i in range(n):
            filename_image = FILENAMES[i % len(FILENAMES)]

            with open(filename_image, 'rb') as f:
                files = {'image': f}
                response = client.post(self.url,
                                       files=files)

            with self.subTest(f'Post {i}'):
                self._assert_response(response)

    def test_post_in_parallel(self, n_loop=10):
        """
        While the API might be able to handle a single call. We should check if the API can handle multiple calls at once, mainly to check if the GPU memory can take it.

        :return:
        """

        def func(self, i: int):
            filename = FILENAMES[i % len(FILENAMES)]

            with open(filename, 'rb') as f:
                files = {'image': f}
                response = requests.post(self.URL,
                                         files=files)

            self._assert_response(response, verbose=0)

            print(f'Finished async {i}')

        loop = asyncio.get_event_loop()

        for i in range(n_loop):
            loop.run_in_executor(None, func, self, i + 1)

        pass  # TODO
        # self.assertEqual(0, 1)

    def _assert_response(self, response, verbose=1):

        json = response.json()

        if verbose:
            print(response.json().get('text'))

        for key in ['name', 'xml', 'text']:
            self.assertIn(key, json.keys())

# class TestAPI2(unittest.TestCase):
#     URL = URL_HOME + '/ocr2/'
#
#     def test_ocr_post(self):
#
#         with open(FILENAME_IMAGE, 'rb') as f:
#             files = {'image': f}
#             response = requests.post(self.URL,
#                                      files=files)
#
#         print(response.json())
#
#         self._assert_response(response)
#
#     def test_post_multiple_in_series(self):
#
#         for filename_image in [FILENAME_IMAGE,
#                                FILENAME_IMAGE2,
#                                ]:
#             with open(filename_image, 'rb') as f:
#                 files = {'image': f}
#                 response = requests.post(self.URL,
#                                          files=files)
#
#             with self.subTest(str(filename_image)):
#                 self._assert_response(response)
#
#     def test_post_a_lot_in_series(self, n=5):
#         i = 0
#         for _ in range(n):
#             for filename_image in [FILENAME_IMAGE,
#                                    FILENAME_IMAGE2,
#
#                                    ]:
#                 with open(filename_image, 'rb') as f:
#                     files = {'image': f}
#                     response = requests.post(self.URL,
#                                              files=files)
#
#                 with self.subTest(f'Post {i}'):
#                     self._assert_response(response)
#
#                 i += 1
#
#     def test_post_in_parallel(self,
#                               n_loop=10  # TODO test higher number
#                               ):
#         """
#         While the API might be able to handle a single call. We should check if the API can handle multiple calls at once, mainly to check if the GPU memory can take it.
#
#         :return:
#         """
#
#         def func(self, i: int):
#             filename = FILENAMES[i % len(FILENAMES)]
#
#             with open(filename, 'rb') as f:
#                 files = {'image': f}
#                 response = requests.post(self.URL,
#                                          files=files)
#
#             self._assert_response(response, verbose=0)
#
#             print(f'Finished async {i}')
#
#         loop = asyncio.get_event_loop()
#
#         for i in range(n_loop):
#             loop.run_in_executor(None, func, self, i + 1)
#
#     def _assert_response(self, response, verbose=1):
#
#         json = response.json()
#
#         if verbose:
#             print(response.json().get('text'))
#
#         for key in ['name', 'xml', 'text']:
#             self.assertIn(key, json.keys())
