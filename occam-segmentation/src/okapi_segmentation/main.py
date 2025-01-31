import os.path
import subprocess
import tempfile
import warnings


DIR_JAVA = os.path.join(os.path.dirname(__file__), "okapi_java")
if not os.path.exists(DIR_JAVA):
    warnings.warn(f"OKAPI JAVA: Directory {DIR_JAVA} does not exist")


def main(filename_in: str = None, filename_out: str = None, language: str = None):
    if language is None:
        language = "en"

    assert os.path.exists(filename_in), f"File {filename_in} does not exist"

    if os.path.exists(filename_out):
        warnings.warn(f"File {filename_out} already exists. Overwriting.")

    try:
        subprocess.check_call(
            [
                "sh",
                os.path.join(
                    DIR_JAVA,
                    "segment.sh",
                ),
                filename_in,
                filename_out,
                language,
                os.path.join(DIR_JAVA, "config/seg.srx"),
            ],
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"command {e.cmd} returned with error (code {e.returncode})")


def okapi_segmentation(text: list[str], language=None) -> list[str]:
    """
    This method extracts individual sentences from a list of text lines,
    employing the Okapi sentence splitter.
    :param text: a list of sentences/text lines
    :return:
         a list of automatically segmented sentences
    """

    if language is None:
        language = "en"

    # Temporary files
    with tempfile.TemporaryDirectory() as tmpdirname:
        filename_in = os.path.join(tmpdirname, "in.txt")
        filename_out = os.path.join(tmpdirname, "out.txt")

        # Write text to file
        with open(filename_in, "w") as f:
            for line in text:
                text = line + "\n"
                f.write(text)

        # Run segmentation
        main(filename_in, filename_out, language)

        # Read segmented text
        with open(filename_out) as f:
            text_segmented = f.read()

    # Split text into lines
    text_segmented = list(map(str.strip, text_segmented.splitlines()))
    return text_segmented
