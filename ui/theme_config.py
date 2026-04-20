import json

STATE = json.loads(r"""{
    "bg_color": "#122C34",
    "chat_bg": "#1e3d4a",
    "input_bg": "#263238",
    "text_color": "#ECEFF1",
    "border_color": "#386173",
    "button_bg": "#264A59",
    "button_hover_bg": "#386173",
    "button_pressed_bg": "#4A788B",
    "border_radius": 6,
    "padding": 10,
    "header_height": 20,
    "input_height": 60,
    "show_line1": false,
    "show_line2": true,
    "show_line3": false,
    "show_line4": true,
    "show_line5": true,
    "show_header": true,
    "show_top_btns": false,
    "show_chat": true,
    "show_mid_btns": true,
    "show_input": true,
    "show_status": true,
    "header_text": "Gemeni agent",
    "header_font": "Arial",
    "header_font_size": 14,
    "header_color": "#CFD8DC",
    "header_icon": "",
    "header_icon_size": 18,
    "mid_btn_width": 52,
    "user_bubble_bg": "#264A59",
    "user_bubble_border": "#386173",
    "agent_bubble_bg": "#1a3540",
    "agent_bubble_border": "#264A59",
    "bubble_text_color": "#ECEFF1",
    "bubble_prefix_color": "#90A4AE",
    "window_width": 650,
    "window_height": 800
}""")

ICON_FONT = ("Segoe MDL2 Assets", 18)
MID_BUTTON_ICONS = ["\uE8A7", "\uE74D", "\uE721", "\uE715", "\uE713"]
SEND_ICON = "\uE724"
MIC_ICON = "\uE720"

UI_TEXTS = {
    "window_title": "Gemeni Agent",
    "chat_sample": "Chat content...",
    "input_placeholder": "Type a message...",
    "status": "Initializing...",
    "top_buttons": ["Button 1", "Button 2", "Button 3", "Button 4", "Button 5"]
}


def build_qss(state):
    bg = state["bg_color"]
    chat_bg = state.get("chat_bg", "transparent")
    input_bg = state.get("input_bg", "transparent")
    text = state["text_color"]
    border = state["border_color"]
    btn_bg = state["button_bg"]
    btn_hover_bg = state.get("button_hover_bg", "#c8c2b4")
    btn_pressed_bg = state.get("button_pressed_bg", "#a0998a")
    radius = state["border_radius"]
    padding = state["padding"]
    ubg = state.get("user_bubble_bg", "#d4cfc0")
    uborder = state.get("user_bubble_border", "#a89f90")
    abg = state.get("agent_bubble_bg", "#ece8de")
    aborder = state.get("agent_bubble_border", "#c8c3b5")
    btxt = state.get("bubble_text_color", "#3a3630")
    bpfx = state.get("bubble_prefix_color", "#6a5f4e")
    bradius = radius

    return f"""
/* Base: all widgets and dialogs use dark background */
QWidget, QDialog {{
    background-color: {bg};
    color: {text};
    font-size: 14px;
}}
QLabel {{
    color: {text};
    font-size: 14px;
    background-color: transparent;
}}

/* Input fields (QLineEdit) */
QLineEdit {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: {radius}px;
    padding: 6px 10px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {btn_hover_bg};
}}
QLineEdit::placeholder {{
    color: {bpfx};
}}

/* Chat bubble container (with border) */
QFrame#chat_bubble {{
    background-color: {chat_bg};
    border: 1px solid {border};
    border-radius: {radius}px;
}}

/* Chat scroll area — transparent */
QScrollArea#chat_scroll, QScrollArea#chat_scroll > QWidget,
QWidget#chat_content {{
    background-color: transparent;
    border: none;
}}

/* Message bubbles */
QFrame#bubble_user {{
    background-color: {ubg};
    border: 1px solid {uborder};
    border-radius: {bradius}px;
}}
QFrame#bubble_agent {{
    background-color: {abg};
    border: 1px solid {aborder};
    border-radius: {bradius}px;
}}
QLabel#bubble_prefix {{
    color: {bpfx};
    font-size: 9px;
    background-color: transparent;
}}
QLabel#bubble_text {{
    color: {btxt};
    font-size: 13px;
    background-color: transparent;
}}

/* Divider lines */
QFrame[frameShape="4"] {{
    border: none;
    background-color: {border};
    max-height: 1px;
}}

/* Buttons */
QPushButton {{
    background-color: {btn_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: {radius}px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    background-color: {btn_hover_bg};
}}
QPushButton:pressed {{
    background-color: {btn_pressed_bg};
}}

/* Input bubble container (with border) */
QFrame#input_bubble {{
    background-color: {input_bg};
    border: 1px solid {border};
    border-radius: {radius}px;
}}

/* Input field inside bubble (no border) */
QTextEdit#inner_input {{
    background-color: transparent;
    color: {text};
    border: none;
    padding: {padding}px;
}}

/* Icon buttons */
QPushButton#send_btn, QPushButton#mic_btn {{
    border-radius: {int(radius * 0.8)}px;
    font-family: 'Segoe MDL2 Assets';
    font-size: 16px;
}}

/* Status bar */
QFrame#status_bar_frame {{
    background-color: transparent;
}}
QLabel#status_label {{
    color: {bpfx};
    font-size: 11px;
}}
QLabel#status_label_right {{
    color: {border};
    font-size: 11px;
    font-style: italic;
}}

/* Mic button — red on hover/press */
QPushButton#mic_btn:hover {{
    background-color: #d97070;
    border-color: #c05050;
    color: #ffffff;
}}
QPushButton#mic_btn:pressed {{
    background-color: #d94f4f;
    border-color: #c03030;
    color: #ffffff;
}}

/* ── Settings dialog ──────────────────────────────────────────────────── */

QWidget#settings_title_bar, QWidget#settings_tab_bar, QWidget#settings_footer {{
    background-color: {abg};
}}

QLabel#settings_title {{
    font-size: 14px;
    font-weight: bold;
    color: {text};
}}

/* Tab buttons */
QPushButton#tab_btn {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: {radius}px;
    padding: 3px 14px;
    font-size: 12px;
}}
QPushButton#tab_btn:hover {{
    background-color: {btn_hover_bg};
    border-color: {border};
}}
QPushButton#tab_btn:checked {{
    background-color: {btn_bg};
    border-color: {border};
    font-weight: bold;
}}

/* Save button — slightly brighter */
QPushButton#settings_save_btn {{
    background-color: {ubg};
    border-color: {btn_hover_bg};
    font-weight: bold;
}}
QPushButton#settings_save_btn:hover {{
    background-color: {btn_hover_bg};
}}

/* Settings page content area */
QScrollArea#settings_scroll, QScrollArea#settings_scroll > QWidget,
QWidget#settings_page {{
    background-color: {input_bg};
    border: none;
}}
QWidget#settings_row_right {{
    background-color: transparent;
}}

/* Section label */
QLabel#settings_section_lbl {{
    font-size: 10px;
    font-weight: bold;
    color: {bpfx};
    margin-top: 8px;
    background-color: transparent;
}}

/* Row labels */
QLabel#settings_row_label {{
    font-size: 13px;
    background-color: transparent;
}}
QLabel#settings_row_sublabel {{
    font-size: 10px;
    color: {bpfx};
    background-color: transparent;
}}

/* Disabled controls */
QLineEdit:disabled {{
    color: {bpfx};
    background-color: {abg};
    border-color: {aborder};
}}
QComboBox:disabled {{
    color: {bpfx};
    background-color: {abg};
    border-color: {aborder};
}}

/* Combo box */
QComboBox {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: {radius}px;
    padding: 4px 8px;
    font-size: 13px;
}}
QComboBox:hover {{
    border-color: {btn_hover_bg};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    selection-background-color: {btn_bg};
    selection-color: {text};
    outline: none;
}}

/* "Soon" badge */
QLabel#settings_badge {{
    font-size: 10px;
    color: {bpfx};
    border: 1px solid {aborder};
    border-radius: 4px;
    padding: 2px 10px;
    background-color: transparent;
}}
""".strip()
