import base64
from time import sleep

from fastapi.testclient import TestClient

from . import config, main
import os.path

# Trigger startup and shutdown of the app once
with TestClient(main.app) as _:
    pass
client = TestClient(main.app)

FILENAME = os.path.dirname(__file__) + "/../tests/data/test.txt"


def get_settings_override():
    return config.Settings(
        etranslation_username="CEF_AI4CULTURE_20240307",
        etranslation_password="zMAXgV4H3T8TquPJ",
        snippet_callback_url="https://18af248d68fceb.lhr.life/hook/snippet",
        document_callback_url="https://18af248d68fceb.lhr.life/hook/document",
        callback_url="https://18af248d68fceb.lhr.life",
        snippet_timeout=20,
        document_timeout=3000,
    )


main.app.dependency_overrides[main.get_settings] = get_settings_override


def test_read_main():
    response = client.get("/info")
    assert response.status_code == 200


def test_send_document():
    with open(FILENAME, "rb") as f:
        response = client.post(
            "/translate/document",
            data={"source": "en", "target": "nl"},
            files={"file": f},
        )
    assert response.status_code == 200
    # check if we retrieve the
    try:
        i = int(response.json())
    except:
        raise AssertionError("Expected an integer response")
    assert i > 0
    print(f"request sent successfully")


def test_translate_document():
    MOCK_TRANSLATION = b"Dit is een testbestand.\n"

    with open(FILENAME, "rb") as f:
        response = client.post(
            "/translate/document",
            data={"source": "en", "target": "nl"},
            files={"file": f},
        )
    i = int(response.json())
    assert i > 0, "Sanity check failed"

    # Mock the callback
    response = client.post(
        f"/hook/document?request-id={i}&target-language=nl",
        data=base64.b64encode(MOCK_TRANSLATION),
    )
    assert response.status_code == 200, "Callback failed"

    response = client.get(f"/translate/document/{i}")

    assert response.status_code == 200

    assert response.content == MOCK_TRANSLATION, response.content


def test_send_documents():
    for i in range(0, 300):
        with open(FILENAME, "rb") as f:
            response = client.post(
                "/translate/document",
                data={"source": "en", "target": "nl"},
                files={"file": f},
            )
        assert response.status_code == 200
        print(f"request {i} sent successfully")
        sleep(1)
