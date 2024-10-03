import requests


def raise_response(response: requests.Response, message: str = None):
    """
    Raises an exception with information about the response.

    Args:
        response: Response from a request
        message: (Optional) To add a message to the dictionary that is raised with the exception.

    Returns:
        None
    """

    feedback = {
        "status_code": response.status_code,
        "content": response.content,
        "text": response.text,
    }

    if message is not None:
        feedback["message"] = message

    # Try to add json, if available
    try:
        feedback["json"] = response.json()
    except Exception:
        pass

    raise Exception(feedback)
