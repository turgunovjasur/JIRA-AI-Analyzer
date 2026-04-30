"""
Loading Component - Loading va Progress

Bu component loading animatsiyalar va progress barlarni
boshqaradi.

Hozir 3 ta sahifada bir xil loading pattern takrorlanardi:
- bug_analyzer.py
- tz_pr_checker.py
- testcase_generator.py
"""

import time
import streamlit as st
from typing import Optional, List


def render_loading_animation(text: str, subtext: str = "Iltimos kuting..."):
    """
    Modern loading animation

    Pulse animation bilan loading ko'rsatadi.

    Args:
        text: Asosiy text (masalan: "🔧 Modellar yuklanmoqda...")
        subtext: Qo'shimcha text (masalan: "Iltimos kuting...")

    Example:
        >>> loading_placeholder = st.empty()
        >>> with loading_placeholder.container():
        >>>     render_loading_animation(
        >>>         "🔧 Modellar yuklanmoqda...",
        >>>         "Iltimos kuting..."
        >>>     )
    """
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


def render_progress_bar(
        current_step: int,
        total_steps: int,
        message: str,
        show_percentage: bool = True
):
    """
    Progress bar ko'rsatish

    Bu function progress bar va status textni bir vaqtda
    ko'rsatadi.

    Args:
        current_step: Joriy qadam (1, 2, 3, ...)
        total_steps: Jami qadamlar soni
        message: Status xabari
        show_percentage: Foizni ko'rsatish (default: True)

    Returns:
        tuple: (progress_bar, status_text) - Streamlit elementlar

    Example:
        >>> progress_bar, status_text = render_progress_bar(1, 4, "TZ olinmoqda...")
        >>> # Keyinroq yangilash:
        >>> progress_bar.progress(2 / 4)
        >>> status_text.info("**[2/4]** PR qidirilmoqda...")
    """
    progress_value = current_step / total_steps

    # Progress bar
    progress_bar = st.progress(progress_value)

    # Status text
    if show_percentage:
        percentage = int(progress_value * 100)
        status_msg = f"**[{current_step}/{total_steps}] {percentage}%** {message}"
    else:
        status_msg = f"**[{current_step}/{total_steps}]** {message}"

    status_text = st.empty()
    status_text.info(status_msg)

    return progress_bar, status_text


class ProgressManager:
    """
    Animated step-by-step progress manager.

    Har bir qadam vizual ko'rsatiladi: bajarildi / jarayonda / kutilmoqda.
    Yon panelida o'tgan vaqt va joriy holat xabari ham chiqadi.

    Example:
        >>> progress = ProgressManager(
        ...     total_steps=4,
        ...     step_labels=["JIRA", "PR", "AI tahlil", "Natija"]
        ... )
        >>> progress.update(1, "JIRA dan ma'lumot olinmoqda...")
        >>> progress.update(3, "Gemini AI tahlil qilmoqda...")
        >>> progress.clear()
    """

    def __init__(
        self,
        total_steps: int,
        show_percentage: bool = True,
        step_labels: Optional[List[str]] = None,
    ):
        self.total_steps = total_steps
        self.show_percentage = show_percentage
        self.current_step = 0
        self.current_message = "Tayyorlanmoqda..."
        self.start_time = time.time()
        self.step_labels = step_labels or [f"Qadam {i + 1}" for i in range(total_steps)]
        self._ph = st.empty()
        self._render()

    # ── internal ──────────────────────────────────────────────────────

    def _elapsed(self) -> str:
        s = int(time.time() - self.start_time)
        return f"{s // 60:02d}:{s % 60:02d}"

    def _build_steps(self) -> str:
        parts = []
        for i, label in enumerate(self.step_labels):
            n = i + 1
            if n < self.current_step:
                ic_cls, lb_cls, st_cls = "pm-ic-done", "pm-lb-done", "pm-st-done"
                icon, sub = "✓", "Bajarildi"
            elif n == self.current_step:
                ic_cls, lb_cls, st_cls = "pm-ic-act", "pm-lb-act", "pm-st-act"
                icon = '<span class="pm-spin">&#8635;</span>'
                sub = "Jarayonda..."
            else:
                ic_cls, lb_cls, st_cls = "pm-ic-pend", "pm-lb-pend", "pm-st-pend"
                icon, sub = str(n), "Kutilmoqda"

            parts.append(
                f'<div class="pm-cell">'
                f'<div class="pm-ic {ic_cls}">{icon}</div>'
                f'<div class="pm-lb {lb_cls}">{label}</div>'
                f'<div class="pm-st {st_cls}">{sub}</div>'
                f'</div>'
            )
            if i < len(self.step_labels) - 1:
                if n < self.current_step:
                    cc = "pm-cn-done"
                elif n == self.current_step:
                    cc = "pm-cn-act"
                else:
                    cc = "pm-cn-pend"
                parts.append(f'<div class="pm-cn {cc}"></div>')

        return "".join(parts)

    def _render(self):
        import streamlit.components.v1 as components

        elapsed_secs = int(time.time() - self.start_time)
        pct = int(self.current_step / self.total_steps * 100) if self.current_step else 0
        steps_html = self._build_steps()
        msg = self.current_message.replace("'", "&#39;").replace('"', "&quot;")

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
.pm-box{{background:rgba(15,23,42,.72);border:1px solid rgba(99,102,241,.25);border-radius:12px;
  padding:1rem 1.3rem;}}
.pm-hdr{{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;}}
.pm-ttl{{font-weight:700;font-size:.88rem;color:#e2e8f0;}}
.pm-clk{{font-size:.76rem;color:#94a3b8;background:rgba(99,102,241,.14);
  padding:.14rem .55rem;border-radius:20px;min-width:52px;text-align:center;}}
.pm-row{{display:flex;align-items:flex-start;justify-content:center;margin-bottom:1rem;}}
.pm-cell{{display:flex;flex-direction:column;align-items:center;min-width:68px;max-width:90px;}}
.pm-cn{{flex:1;height:2px;margin-top:14px;border-radius:2px;}}
.pm-cn-done{{background:#10b981;}}
.pm-cn-act{{background:linear-gradient(90deg,#10b981,rgba(99,102,241,.18));}}
.pm-cn-pend{{background:rgba(148,163,184,.15);}}
.pm-ic{{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:.88rem;font-weight:700;border:2px solid;}}
.pm-ic-done{{background:rgba(16,185,129,.12);border-color:#10b981;color:#10b981;}}
.pm-ic-act{{background:rgba(99,102,241,.18);border-color:#6366f1;color:#6366f1;
  box-shadow:0 0 10px rgba(99,102,241,.35);}}
.pm-ic-pend{{background:rgba(148,163,184,.07);border-color:rgba(148,163,184,.27);color:#64748b;}}
.pm-lb{{font-size:.66rem;font-weight:600;text-align:center;margin-top:.3rem;line-height:1.3;}}
.pm-lb-done{{color:#6ee7b7;}}.pm-lb-act{{color:#a5b4fc;}}.pm-lb-pend{{color:#64748b;}}
.pm-st{{font-size:.6rem;text-align:center;margin-top:.1rem;}}
.pm-st-done{{color:#10b981;}}.pm-st-act{{color:#818cf8;}}.pm-st-pend{{color:#475569;}}
.pm-bar-bg{{background:rgba(99,102,241,.11);border-radius:99px;height:5px;margin-bottom:.8rem;overflow:hidden;}}
.pm-bar{{height:100%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:99px;
  transition:width .4s ease;}}
.pm-msg{{font-size:.78rem;color:#94a3b8;text-align:center;padding:.35rem .7rem;
  background:rgba(99,102,241,.05);border-radius:7px;border:1px solid rgba(99,102,241,.12);}}
@keyframes pm-spin{{to{{transform:rotate(360deg);}}}}
.pm-spin{{display:inline-block;animation:pm-spin .85s linear infinite;}}
</style></head>
<body>
<div class="pm-box">
  <div class="pm-hdr">
    <span class="pm-ttl">&#9881; Jarayon davom etmoqda</span>
    <span class="pm-clk" id="pm-clk">&#9201; {elapsed_secs // 60:02d}:{elapsed_secs % 60:02d}</span>
  </div>
  <div class="pm-row">{steps_html}</div>
  <div class="pm-bar-bg"><div class="pm-bar" style="width:{pct}%"></div></div>
  <div class="pm-msg">{msg}</div>
</div>
<script>
(function(){{
  var offset = Date.now() - {elapsed_secs} * 1000;
  var el = document.getElementById('pm-clk');
  function tick(){{
    var s = Math.floor((Date.now()-offset)/1000);
    var m = Math.floor(s/60), sec = s%60;
    el.textContent = '⏱ ' + String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
  }}
  tick();
  setInterval(tick, 1000);
}})();
</script>
</body></html>"""

        with self._ph:
            components.html(html, height=210, scrolling=False)

    # ── public API (backward-compatible) ─────────────────────────────

    def update(self, step: int, message: str):
        self.current_step = step
        self.current_message = message
        self._render()

    def complete(self, message: str = "✅ Tayyor!"):
        self.current_step = self.total_steps
        self.current_message = message
        self._render()

    def error(self, message: str):
        self._ph.error(message)

    def clear(self):
        self._ph.empty()


def clear_loading(loading_placeholder):
    """
    Loading animatsiyani tozalash

    Args:
        loading_placeholder: st.empty() dan yaratilgan placeholder

    Example:
        >>> loading_placeholder = st.empty()
        >>> with loading_placeholder.container():
        >>>     render_loading_animation("Loading...")
        >>> # Ishlar tugagach:
        >>> clear_loading(loading_placeholder)
    """
    if loading_placeholder:
        loading_placeholder.empty()


# CSS Styles
LOADING_STYLES = """
<style>
.modern-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 0;
}

.pulse-animation {
    position: relative;
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.pulse-ring {
    position: absolute;
    width: 100%;
    height: 100%;
    border: 3px solid #238636;
    border-radius: 50%;
    animation: pulse 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
    opacity: 0;
}

.pulse-ring:nth-child(2) {
    animation-delay: 0.5s;
}

.pulse-ring:nth-child(3) {
    animation-delay: 1s;
}

.pulse-core {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
    border-radius: 50%;
    box-shadow: 0 0 20px rgba(35, 134, 54, 0.5);
}

@keyframes pulse {
    0% {
        transform: scale(0.5);
        opacity: 0;
    }
    50% {
        opacity: 1;
    }
    100% {
        transform: scale(1.5);
        opacity: 0;
    }
}

.loading-text {
    margin-top: 1.5rem;
    font-size: 1.2rem;
    font-weight: 600;
    color: #e6edf3;
    text-align: center;
}

.loading-subtext {
    margin-top: 0.5rem;
    font-size: 0.95rem;
    color: #8b949e;
    text-align: center;
}
</style>
"""


def inject_loading_styles():
    """Loading styles ni inject qilish"""
    st.markdown(LOADING_STYLES, unsafe_allow_html=True)