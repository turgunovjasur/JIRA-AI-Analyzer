"""
UI Components Module - Umumiy UI komponentlar

Bu module barcha sahifalar uchun umumiy UI komponentlarni o'z ichiga oladi:
- Header: Sahifa sarlavhalari
- Loading: Loading animatsiyalar va progress barlar
- History: So'nggi tahlillar tarixi
- Metrics: Statistika ko'rsatish
- Error: Xatolik xabarlari
"""

from .header import render_header
from .loading import render_loading_animation, render_progress_bar, clear_loading, ProgressManager
from .history import render_history, save_to_history, HistoryManager
from .metrics import render_metric_card, render_metrics_grid, render_results_info
from .error import render_error, render_warning, render_info, render_success
from .models import load_models

__all__ = [
    # Header
    'render_header',

    # Loading
    'render_loading_animation',
    'render_progress_bar',
    'clear_loading',
    'ProgressManager',

    # History
    'render_history',
    'save_to_history',
    'HistoryManager',

    # Metrics
    'render_metric_card',
    'render_metrics_grid',
    'render_results_info',

    # Error
    'render_error',
    'render_warning',
    'render_info',
    'render_success',

    # Models
    'load_models',
]