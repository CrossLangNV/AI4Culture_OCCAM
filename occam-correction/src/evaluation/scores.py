from sacrebleu import BLEU, TER, CHRF


def BLEU_corpus(references: list[str], hypotheses: list[str]) -> float:
    """
    Corpus score (single score for all sentences)
    Value between 0. and 1.
    """
    bleu = BLEU()

    corpus_bleu = bleu.corpus_score(hypotheses, [references])

    # Normalize the score
    score = corpus_bleu.score / 100

    return score


def CER_corpus(references: list[str], hypotheses: list[str]) -> float:
    """
    Character Error Rate:
    Levenshtein distance (Total number of edits) divided by the total number of characters in the references.
    Does not include number of elements in the list as newlines.
    """

    l_distance = [
        levenshtein_distance(reference, hypotheses)
        for reference, hypotheses in zip(references, hypotheses)
    ]
    distance = sum(l_distance)

    # Normalize the score
    def total_length(l: list[str]):
        return sum(map(len, l))

    n = total_length(references)

    norm = distance / max(n, 1)
    return norm


def ChrF_corpus(references: list[str], hypotheses: list[str]) -> float:
    """
    Corpus score (single score for all sentences)
    Value between 0 and 1
    """
    chrf = CHRF()
    corpus_chrf = chrf.corpus_score(hypotheses, [references])

    # Normalize the score
    score = corpus_chrf.score / 100

    return score


def edit_distance_corpus(references: list[str], hypotheses: list[str]) -> float:
    """
    Levenshtein distance
    :param references:
    :param hypotheses:
    :return:
    """

    l_distance = [
        levenshtein_distance(reference, hypotheses)
        for reference, hypotheses in zip(references, hypotheses)
    ]
    distance = sum(l_distance)

    # Normalize the score
    def total_length(l: list[str]):
        return sum(map(len, l))

    n_c_references = total_length(references)
    n_c_hypotheses = total_length(hypotheses)

    norm = distance / max(max(n_c_references, n_c_hypotheses), 1)
    return norm


def TER_corpus(references: list[str], hypotheses: list[str]) -> float:
    """
    Corpus score (single score for all sentences)
    Value between 0 and 1*
        *not necessarily, but usually
    """
    ter = TER()
    corpus_ter = ter.corpus_score(hypotheses, [references])

    # Normalize the score
    score = corpus_ter.score / 100

    return score


def levenshtein_distance(s: str, t: str) -> int:
    """
    The algorithm calculates the minimum edit distance between two strings s and t.
    """
    m = len(s)
    n = len(t)
    d = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        d[i][0] = i

    for j in range(1, n + 1):
        d[0][j] = j

    for j in range(1, n + 1):
        for i in range(1, m + 1):
            if s[i - 1] == t[j - 1]:
                cost = 0
            else:
                cost = 1
            d[i][j] = min(
                d[i - 1][j] + 1,  # deletion
                d[i][j - 1] + 1,  # insertion
                d[i - 1][j - 1] + cost,
            )  # substitution

    return d[m][n]
