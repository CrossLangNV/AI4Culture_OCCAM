import json
import os

import iso639
from openai import OpenAI

client = OpenAI(base_url=os.environ.get("OPENAI_API_BASE"),api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ.get("OPENAI_MODEL")

def get_language_name(language_code: str) -> str:
    """
    Example:
    >>> get_language_name("en")
    'English'
    """
    return iso639.to_name(language_code)


def parse_output(output: str):
    # parse JSON

    output = output[output.find("{") : output.rfind("}") + 1]

    try:
        d = json.loads(output, strict=False)  # Handle newlines in text
    except Exception as e:
        raise ValueError(f"Could not parse as JSON: {output}")

    if "text" not in d:
        raise ValueError(f"JSON does not contain 'text' field: {d}")

    return d["text"]


def generate_output(
    sentence: str, lang_code: str = None, model: str = MODEL, prompt: str = None
) -> str:
    """
    Temperature is set to 0 to avoid randomization and be deterministic.
    """

    # Get language name
    lang = get_language_name(lang_code) if lang_code else "Unknown"

    if prompt:
        prompt_template = prompt

    elif lang_code:
        # prompt_template = "Correct the OCRed text in {language}: \"{sentence}\". Only correct character errors. Return a JSON with 'text' field."
        prompt_template = (
            "Correct the OCRed text in {language}. Only correct character errors. Return a JSON with 'text' field.\n"
            + "`{sentence}`"
        )

    else:
        prompt_template = (
            "Correct the OCRed text. Only correct character errors. Return a JSON with 'text' field.\n"
            + "`{sentence}`"
        )

    prompt = prompt_template.format(language=lang, sentence=sentence)

    response = client.chat.completions.create(model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0)
    corrected = response.choices[0].message.content

    return corrected
