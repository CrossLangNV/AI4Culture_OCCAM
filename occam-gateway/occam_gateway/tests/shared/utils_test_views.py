from rest_framework import status


class SharedTestAPIPermission:
    """
    Requires:
     - self.url
    """

    def test_no_api_key(self):
        response = self.client.post(self.url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
