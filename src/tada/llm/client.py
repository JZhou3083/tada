from functools import lru_cache

from google.genai import Client


@lru_cache(maxsize=1)
def get_genai_client():
    return Client(
        vertexai=True,
        project="jlr-dl-cat",
        location="global",
    )
