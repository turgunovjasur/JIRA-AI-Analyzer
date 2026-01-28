"""
Models Component - Model loading

Bu component model va helper'larni yuklash uchun.
Bug Analyzer'da ishlatiladi.
"""

import streamlit as st


@st.cache_resource
def load_models():
    """
    Model va helper'larni yuklash (cache)

    Bu function embedding, vectordb va gemini helper'larni
    yuklaydi va cache qiladi.

    Returns:
        tuple: (embedding_helper, vectordb_helper, gemini_helper)

    Example:
        >>> from ui.components import load_models
        >>> embedding, vectordb, gemini = load_models()
    """
    from utils.embedding_helper import EmbeddingHelper
    from utils.vectordb_helper import VectorDBHelper
    from utils.gemini_helper import GeminiHelper

    embedding_helper = EmbeddingHelper()
    vectordb_helper = VectorDBHelper()
    gemini_helper = GeminiHelper()

    return embedding_helper, vectordb_helper, gemini_helper