from .general import Options
from .line_joiner import Dehypenation, JoinTextLines, SentenceSegmentationOkapi


class OptionsAll(Options):
    _options = [Dehypenation(), JoinTextLines(), SentenceSegmentationOkapi()]
