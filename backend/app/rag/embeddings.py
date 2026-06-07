from fastembed import TextEmbedding

_model: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="intfloat/multilingual-e5-large")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    return [vec.tolist() for vec in model.embed(texts)]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
