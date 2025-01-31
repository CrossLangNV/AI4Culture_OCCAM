import math
from pathlib import Path

import flair
import torch
from flair.embeddings import FlairEmbeddings
from flair.embeddings.token import replace_with_language_code
from flair.file_utils import cached_path
from flair.models import LanguageModel

from post_ocr_correction.model_utils import DIRNAME_FLAIR

flair.device = torch.device("cpu")
flair.cache_root = Path(DIRNAME_FLAIR)


class LanguageModelCL(LanguageModel):
    def calculate_perplexity(self, *args, **kwargs):
        return super().calculate_perplexity(*args, **kwargs)

    def calculate_perplexity_multi(self, l_text: list[str]) -> list[float]:
        l_max = max(len(text) for text in l_text)
        n_text = len(l_text)

        if l_max <= 1:
            # Can't calculate perplexity with no or one character length
            return [0.0] * n_text

        # Make a copy of the list
        _l_text = l_text[:]

        if not self.is_forward_lm:
            _l_text = [text[::-1] for text in _l_text]

        # Make all texts the same length. These will be discarded later before calculating the perplexity
        _l_text = [text.ljust(l_max) for text in _l_text]

        # input ids
        # Should be (n_chars x n_text), therefore transpose from (n_text x n_chars) to (n_chars x n_text)
        input_idx = torch.tensor(
            [
                [self.dictionary.get_idx_for_item(char) for char in text[:-1]]
                for text in _l_text
            ]
        ).T
        input_idx = input_idx.to(flair.device)

        # push list of character IDs through model
        hidden = self.init_hidden(n_text)
        prediction, _, hidden = self.forward(input_idx, hidden)
        # Shape prediction: d_chars, N_batch, N_classes
        # Should be N_batch, N_classes, d_chars
        prediction = prediction.permute(1, 2, 0)

        # the target is always the next character
        targets = torch.tensor(
            [
                [self.dictionary.get_idx_for_item(char) for char in text[1:]]
                for text in _l_text
            ]
        )  # Transpose
        targets = targets.to(flair.device)

        # use cross entropy loss to compare output of forward pass with targets
        cross_entropy_loss = torch.nn.CrossEntropyLoss(
            # reduction="none"
        )
        # Shapes should be (N_batch, N_classes, d_chars) and (N_batch, d_chars)

        # Crop to the length of the original text
        l_perplexity = []
        for i, text in enumerate(l_text):

            def slicer(arr):
                return arr[i : i + 1, ..., : len(text) - 1]

            prediction_i = slicer(prediction)
            targets_i = slicer(targets)

            loss_i = cross_entropy_loss(prediction_i, targets_i)
            perplexity_i = math.exp(loss_i)
            l_perplexity.append(perplexity_i)

        return l_perplexity


class FlairEmbeddingsCL(FlairEmbeddings):
    def __init__(self, model, *args, has_decoder: bool = False, **kwargs):
        # From super

        super().__init__(model, *args, has_decoder=has_decoder, **kwargs)

        cache_dir = Path("embeddings")

        if isinstance(model, str):
            # load model if in pretrained model map
            if model.lower() in self.PRETRAINED_MODEL_ARCHIVE_MAP:
                base_path = self.PRETRAINED_MODEL_ARCHIVE_MAP[model.lower()]

                # Fix for CLEF HIPE models (avoid overwriting best-lm.pt in cache_dir)
                if "impresso-hipe" in model.lower():
                    cache_dir = cache_dir / model.lower()
                    # CLEF HIPE models are lowercased
                    self.is_lower = True
                model = cached_path(base_path, cache_dir=cache_dir)

            elif replace_with_language_code(model) in self.PRETRAINED_MODEL_ARCHIVE_MAP:
                base_path = self.PRETRAINED_MODEL_ARCHIVE_MAP[
                    replace_with_language_code(model)
                ]
                model = cached_path(base_path, cache_dir=cache_dir)

            elif not Path(model).exists():
                raise ValueError(
                    f'The given model "{model}" is not available or is not a valid path.'
                )

        model = LanguageModelCL.load_language_model(model, has_decoder=has_decoder)

        self.lm = model
