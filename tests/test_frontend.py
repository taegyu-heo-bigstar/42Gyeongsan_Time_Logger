from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "calendar.html").read_text(encoding="utf-8")
JAVASCRIPT = (ROOT / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")


def test_day_details_use_right_sidebar():
    assert '<aside class="day-modal"' in HTML
    assert "justify-content: flex-end" in CSS
    assert "animation: sidebar-enter" in CSS


def test_log_list_is_scrollable():
    log_list_rule = CSS.split(".modal-log-list {", 1)[1].split("}", 1)[0]
    assert "overflow-y: auto" in log_list_rule
    assert "min-height: 0" in log_list_rule


def test_delete_confirmation_has_explicit_choices():
    assert "정말로 삭제하시겠습니까?" in HTML
    assert 'id="deleteConfirmYes"' in HTML
    assert 'id="deleteConfirmNo"' in HTML
    assert "window.confirm" not in JAVASCRIPT


def test_every_rendered_log_gets_a_delete_button():
    assert 'deleteButton.textContent = "×"' in JAVASCRIPT
    assert "openDeleteConfirm(log.id)" in JAVASCRIPT


def test_calendar_cells_render_only_daily_summary():
    summary_function = JAVASCRIPT.split("function makeDaySummary", 1)[1].split(
        "function setActionPending", 1
    )[0]
    assert 'class="day-summary-duration"' in summary_function
    assert 'class="day-summary-count"' in summary_function
    assert "formatTime(" not in summary_function
    assert "log.start_time" not in summary_function
