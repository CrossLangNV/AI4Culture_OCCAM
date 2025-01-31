import re
import warnings


def concatenate_text_lines(
    text_lines: list[str],
    delimiter: str = " ",
    filter_sentences=True,
    fix_hyphenation=True,
) -> str:
    """
    Concatenate the lines in the text into a single string.

    Args:
        :param text_lines: (list[str]): The text lines to concatenate.
        :param delimiter: (str = " "): The delimiter to use when concatenating sentences.
        :param fix_hyphenation: (bool): A flag indicating whether to fix hyphenated words.
        :param filter_sentences: (bool):

     Returns:
         str: The concatenated text.

    """

    if filter_sentences:
        text_lines = text_filter(text_lines)

    if fix_hyphenation:
        text_lines = hyphenation_fix(text_lines)

    result = f"{delimiter}".join(text_lines)
    if delimiter in "\r\n":
        # add a newline at the end of the text
        result += delimiter
    return result


def text_filter(sentences: list[str], remove_sent_punct_digit=False) -> list[str]:
    """
    Remove empty strings, strip trailing and leading newlines and spaces.

    :arg remove_sent_punct_digit: (bool): A flag indicating whether to remove sentences that only contain punctuation or digits.

    Returns:
        List[str]: The filtered sentences.
    """
    sentences = list(filter(None, map(str.strip, sentences)))

    if remove_sent_punct_digit:
        warnings.warn("remove_sent_punct_digit is not implemented yet.")

    return sentences


def hyphenation_fix(sentences: list[str]) -> list[str]:
    """
    Given a list of strings we concat last word of previous sentence
    with first word of current sentence if this word starts with a hyphen.

    Args:
        sentences (List[str]): The sentences to process.

    Returns:
        List[str]: The sentences with concatenated hyphenated words.
    """
    text = "\n".join(sentences)

    # find all words that are hyphenated due to a newline (we do not consider "-\n\n" )
    hyphenated_words = re.findall(r"(\w+-\n\w+)", text)
    # make the list unique
    hyphenated_words = list(set(hyphenated_words))

    for word in hyphenated_words:
        # TODO: add a check if the word is valid or not via dictionary i.e. something like if spell.unknown( [ word.replace("\n",'') ] )
        #  because we do not want to replace 'New-\nYork' with NewYork. Problem, no multilingual dictionary available.
        text = text.replace(word, word.replace("-\n", ""))

    return text.split("\n")
