"""
Models Component - Model loading with Lazy Loading

Bu component model va helper'larni yuklash uchun.
Bug Analyzer'da ishlatiladi.

Yangilik v4.0:
- Lazy loading - o'chirilgan modullar yuklanmaydi
- Resurslarni tejash

Author: JASUR TURGUNOV
Version: 2.0
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)


@st.cache_resource
def load_models():
    """
    Model va helper'larni yuklash (cache) - WITH LAZY LOADING

    Bu function embedding, vectordb va gemini helper'larni
    yuklaydi va cache qiladi.

    MUHIM: Agar Bug Analyzer moduli o'chirilgan bo'lsa,
    modellar yuklanmaydi va (None, None, None) qaytariladi.

    Returns:
        tuple: (embedding_helper, vectordb_helper, gemini_helper)
               yoki (None, None, None) agar modul o'chirilgan bo'lsa

    Example:
        >>> from ui.components import load_models
        >>> embedding, vectordb, gemini = load_models()
        >>> if embedding is None:
        >>>     st.warning("Bug Analyzer moduli o'chirilgan")
    """
    from config.app_settings import get_app_settings

    settings = get_app_settings()

    # Bug Analyzer o'chirilgan bo'lsa - modellar yuklanmasin!
    if not settings.modules.bug_analyzer_enabled:
        logger.info("Bug Analyzer moduli o'chirilgan - modellar yuklanmaydi")
        return None, None, None

    # Modellarni yuklash
    logger.info("Bug Analyzer modellari yuklanmoqda...")

    from utils.embedding_helper import EmbeddingHelper
    from utils.vectordb_helper import VectorDBHelper
    from utils.gemini_helper import GeminiHelper

    embedding_helper = EmbeddingHelper()
    vectordb_helper = VectorDBHelper()
    gemini_helper = GeminiHelper()

    logger.info("Bug Analyzer modellari yuklandi!")

    return embedding_helper, vectordb_helper, gemini_helper


def get_gemini_only():
    """
    Faqat Gemini helper yuklash - embedding yuklashsiz

    Bu funksiya TZ-PR Checker va Testcase Generator uchun.
    Embedding model yuklanmaydi, faqat Gemini API.

    Returns:
        GeminiHelper instance
    """
    from utils.gemini_helper import GeminiHelper
    return GeminiHelper()


def is_models_loaded() -> bool:
    """
    Modellar yuklangan yoki yo'qligini tekshirish

    Returns:
        bool: True agar modellar yuklangan bo'lsa
    """
    from config.app_settings import get_app_settings

    settings = get_app_settings()
    return settings.modules.bug_analyzer_enabled


def clear_model_cache():
    """
    Model cache'ni tozalash

    Bu funksiya modul o'chirilganda chaqirilishi mumkin.
    """
    load_models.clear()
    logger.info("Model cache tozalandi")
