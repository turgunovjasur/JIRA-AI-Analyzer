# ui/components.py
import streamlit as st
from utils.ai.embedding_helper import EmbeddingHelper
from utils.database.vectordb_helper import VectorDBHelper


@st.cache_resource
def load_models():
    """Embedding va VectorDB modellarni yuklash (global cache).
    GeminiHelper kompaniyaga xos — alohida company keys bilan yarating."""
    embedding_helper = EmbeddingHelper()
    vectordb_helper = VectorDBHelper()
    return embedding_helper, vectordb_helper, None


def render_header(title, subtitle, author="Developed by JASUR TURGUNOV"):
    """Sahifa headeri"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
        <p class="author">{author}</p>
    </div>
    """, unsafe_allow_html=True)


def render_loading_animation(text, subtext):
    """Modern loading animation"""
    st.markdown(f"""
    <div class="modern-loading">
        <div class="pulse-animation">
            <div class="pulse-ring"></div>
            <div class="pulse-ring"></div>
            <div class="pulse-ring"></div>
            <div class="pulse-core"></div>
        </div>
        <div class="loading-text">{text}</div>
        <div class="loading-subtext">{subtext}</div>
    </div>
    """, unsafe_allow_html=True)


def render_results_info(top_n, found, filtered, min_similarity):
    """Qidiruv natijasi info"""
    st.markdown(f"""
    <div class="results-info">
        <div class="results-info-icon">📊</div>
        <div class="results-info-text">
            <div class="results-info-title">Qidiruv natijasi</div>
            <div class="results-info-subtitle">
                {top_n} ta taskdan {found} ta {min_similarity:.0%} o'xshashlikka to'g'ri keldi 
                (Jami topildi: {filtered} ta)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Sidebar rendering"""

    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #e6edf3; font-weight: 700;">🔬 JIRA Analyzer</h2>
            <p style="color: #8b949e; font-size: 0.85rem;">AI-Powered Bug Analysis</p>
            <p style="color: #6e7681; font-size: 0.75rem; font-style: italic;">by JASUR TURGUNOV</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Page selection - TEXT ONLY (emoji muammosini hal qilish uchun)
        page = st.radio(
            "Sahifani tanlang",
            ["Bug Analyzer", "Sprint Statistics"],
            label_visibility="visible",
            horizontal=False
        )

        st.divider()

        # Settings
        st.markdown("### ⚙️ Sozlamalar")

        settings = {}

        if page == "Bug Analyzer":
            settings['top_n'] = st.slider(
                "🎯 Top tasklar soni",
                min_value=1,
                max_value=10,
                value=3,
                help="Qidiruv natijasida ko'rsatiladigan eng o'xshash tasklar soni"
            )

            settings['min_similarity'] = st.slider(
                "📊 Min o'xshashlik %",
                min_value=50,
                max_value=95,
                value=70,
                step=5,
                help="Minimal o'xshashlik foizi (threshold)"
            ) / 100

        st.divider()

        # Info
        st.markdown("""
        <div style="background: rgba(88, 166, 255, 0.1); padding: 1rem; border-radius: 10px; border: 1px solid #30363d;">
            <p style="color: #8b949e; font-size: 0.8rem; margin: 0;">
                <strong style="color: #58a6ff;">Model:</strong> multilingual-e5-large<br>
                <strong style="color: #58a6ff;">AI:</strong> Gemini 2.5 Flash<br>
                <strong style="color: #58a6ff;">DB:</strong> ChromaDB
            </p>
        </div>
        """, unsafe_allow_html=True)

    return page, settings