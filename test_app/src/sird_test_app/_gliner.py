"""Local GLiNER loading with the tokenizer compatibility patch."""

from __future__ import annotations

from pathlib import Path


def _load_fixed_tokenizer(
    _tokenizer_class: type[object],
    _tokenizer_config: object,
    model_dir: Path,
    cache_dir: Path | None = None,
) -> object:
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        model_dir,
        cache_dir=cache_dir,
        fix_mistral_regex=True,
    )


def _restore_tokenizer_loader(
    tokenizer_owner: type[object],
    original_loader: object,
) -> None:
    tokenizer_owner._load_tokenizer = original_loader


def load_gliner_model(model_dir: Path) -> object:
    from gliner import GLiNER
    from gliner.model import UniEncoderSpanGLiNER

    tokenizer_owner = next(
        tokenizer_base
        for tokenizer_base in UniEncoderSpanGLiNER.__mro__
        if "_load_tokenizer" in tokenizer_base.__dict__
    )
    original_loader = tokenizer_owner.__dict__["_load_tokenizer"]

    tokenizer_owner._load_tokenizer = classmethod(_load_fixed_tokenizer)
    try:
        model = GLiNER.from_pretrained(str(model_dir), local_files_only=True)
    except BaseException:
        _restore_tokenizer_loader(tokenizer_owner, original_loader)
        raise
    _restore_tokenizer_loader(tokenizer_owner, original_loader)
    return model
