"""Custom Streamlit styling and CSS for the Sudoku Book Generator app."""

APP_CSS = """
<style>
/* ── Global ─────────────────────────────────────────────────────────────── */
.stApp {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}

/* ── Tab styling ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--background-color);
    border-bottom: 2px solid rgba(128, 128, 128, 0.2);
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    padding: 8px 18px;
    font-weight: 500;
    color: rgba(128, 128, 128, 0.9);
    background: transparent;
    border: none;
    transition: background 0.2s;
}
.stTabs [aria-selected="true"] {
    background: rgba(82, 130, 255, 0.12) !important;
    color: #5282FF !important;
    border-bottom: 2px solid #5282FF;
}

/* ── Cards ───────────────────────────────────────────────────────────────── */
.kdp-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

/* ── Compliance badge ────────────────────────────────────────────────────── */
.badge-pass {
    display: inline-block;
    background: #1b8a3d;
    color: white;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 13px;
    font-weight: 600;
}
.badge-warn {
    display: inline-block;
    background: #c47c00;
    color: white;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 13px;
    font-weight: 600;
}
.badge-fail {
    display: inline-block;
    background: #b91c1c;
    color: white;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 13px;
    font-weight: 600;
}

/* ── Checklist items ─────────────────────────────────────────────────────── */
.check-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 14px;
}
.check-pass { color: #1b8a3d; }
.check-fail { color: #b91c1c; }

/* ── Section header ──────────────────────────────────────────────────────── */
.section-header {
    font-size: 18px;
    font-weight: 600;
    margin: 16px 0 8px;
    color: var(--text-color);
    border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    padding-bottom: 6px;
}

/* ── App header / branding ───────────────────────────────────────────────── */
.app-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 4px;
}
.app-title {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.2;
}
.app-subtitle {
    font-size: 14px;
    color: rgba(128, 128, 128, 0.9);
    margin-top: 2px;
}
.app-version {
    font-size: 11px;
    background: rgba(82, 130, 255, 0.15);
    color: #5282FF;
    border-radius: 4px;
    padding: 1px 6px;
    margin-left: 8px;
}

/* ── Metric boxes ────────────────────────────────────────────────────────── */
.metric-box {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.15);
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
}
.metric-value {
    font-size: 22px;
    font-weight: 700;
}
.metric-label {
    font-size: 12px;
    color: rgba(128, 128, 128, 0.85);
}

/* ── Help text ───────────────────────────────────────────────────────────── */
.help-text {
    font-size: 12px;
    color: rgba(128, 128, 128, 0.8);
    margin-top: 2px;
}

/* ── Step wizard ─────────────────────────────────────────────────────────── */
.step-indicator {
    display: flex;
    gap: 6px;
    align-items: center;
    margin-bottom: 16px;
}
.step-dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    background: rgba(128, 128, 128, 0.2);
    color: rgba(128, 128, 128, 0.7);
}
.step-dot-active {
    background: #5282FF;
    color: white;
}
.step-dot-done {
    background: #1b8a3d;
    color: white;
}
.step-line {
    flex: 1;
    height: 2px;
    background: rgba(128, 128, 128, 0.2);
}

/* ── Batch item ──────────────────────────────────────────────────────────── */
.batch-item {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
}
</style>
"""


STREAMLIT_CONFIG_TOML = """\
[theme]
primaryColor = "#5282FF"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1a1d27"
textColor = "#fafafa"
font = "sans serif"

[server]
headless = true
enableCORS = false
"""


def get_app_css() -> str:
    return APP_CSS


def get_streamlit_config() -> str:
    return STREAMLIT_CONFIG_TOML
