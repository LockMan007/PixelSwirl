# pip install tkinter
# pip install PyQt6 PyQt6-WebEngine
# pip install PySide6 PySide6-WebEngine
# the below error in dark red is fine. Ignore it:
# ERROR: Ignored the following versions that require a different python version:

import sys
import os
import re
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPushButton, QLineEdit, QLabel, QListWidget,
    QTextEdit, QFileDialog, QMessageBox, QCheckBox, QStatusBar,
    QToolBar, QMenu, QSlider, QComboBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
# Corrected import: remove 'Signal', add 'pyqtSignal'
from PyQt6.QtCore import Qt, QUrl, QRegularExpression, QEvent, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument, QFont, QSyntaxHighlighter, QWheelEvent

# --- Custom QTextEdit for Mouse Wheel Event ---
class ZoomableTextEdit(QTextEdit):
    # Signal to notify parent about font size change
    font_size_changed = pyqtSignal(int) # <<<--- CORRECTED: Use pyqtSignal

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            current_font_size = self.font().pointSize()
            
            new_font_size = current_font_size
            if delta > 0:
                new_font_size = min(current_font_size + 1, 72) # Max font size 72
            else:
                new_font_size = max(current_font_size - 1, 6) # Min font size 6
            
            if new_font_size != current_font_size:
                # Emit signal so parent can update slider/textbox and other widgets
                self.font_size_changed.emit(new_font_size)
            event.accept()
        else:
            super().wheelEvent(event)

# --- QSyntaxHighlighter Class for HTML ---
class HtmlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        self.formats = {} # This will be populated by set_theme_colors
        self.rules = []
        self._init_rules() # Initialize rules once

    def _init_rules(self):
        # HTML Comments: (handles multi-line comments by matching the whole block)
        self.rules.append((r'', "comment"))

        # DOCTYPE
        self.rules.append((r'<!DOCTYPE.*?>', "doctype"))

        # HTML Tags (e.g., <div>, <p>, <span>, <br/>, </head>)
        # This matches the tag name itself, not attributes within it.
        # It covers opening tags, closing tags, and self-closing tags.
        self.rules.append((r'<\s*[/]?\s*[\w:]+\b', "tag")) # Matches "<div", "</div", "< span"
        self.rules.append((r'\b[\w:]+\s*/>', "tag")) # Matches "div/>"
        self.rules.append((r'>', "tag")) # Matches the closing angle bracket

        # Attributes (e.g., href="...", class="...")
        # This focuses on the attribute name itself, not the value.
        self.rules.append((r'\b([a-zA-Z_][\w\-\:]*)\s*=', "attribute", 1)) # attr=

        # String values inside attributes (e.g., "value", 'value')
        self.rules.append((r'"[^"]*"', "string")) # double quoted strings
        self.rules.append((r"'[^']*'", "string")) # single quoted strings

        # HTML Entities (&amp;, &nbsp;, &#123;)
        self.rules.append((r'&[a-zA-Z0-9#]+;', "entity"))

        # Basic highlighting for script/style tag blocks (highlights the whole block)
        self.rules.append((r'<script\b[^>]*>[\s\S]*?</script>', "script_tag"))
        self.rules.append((r'<style\b[^>]*>[\s\S]*?</style>', "style_tag"))

    def create_format(self, color: QColor, font_weight: QFont.Weight = QFont.Weight.Normal, font_italic: bool = False):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        fmt.setFontWeight(font_weight)
        fmt.setFontItalic(font_italic)
        return fmt

    def set_theme_colors(self, theme_name: str):
        if theme_name == "light":
            self.formats = {
                "tag": self.create_format(QColor("#000080"), QFont.Weight.Bold),      # Dark blue
                "attribute": self.create_format(QColor("#800080")),                   # Purple
                "string": self.create_format(QColor("#008000")),                      # Green
                "comment": self.create_format(QColor("#808080"), font_italic=True),   # Gray italic
                "doctype": self.create_format(QColor("#008080"), QFont.Weight.Bold),  # Teal
                "entity": self.create_format(QColor("#8B0000")),                      # Dark red
                "script_tag": self.create_format(QColor("#0000FF"), QFont.Weight.Bold), # Blue
                "style_tag": self.create_format(QColor("#FF00FF"), QFont.Weight.Bold), # Magenta
            }
        else: # dark
            self.formats = {
                "tag": self.create_format(QColor("#569CD6"), QFont.Weight.Bold),      # Light blue for tags
                "attribute": self.create_format(QColor("#9CDCFE")),                   # Lighter blue for attributes
                "string": self.create_format(QColor("#D69D85")),                      # Orange/brown for strings
                "comment": self.create_format(QColor("#6A9955"), font_italic=True),   # Lighter green for comments
                "doctype": self.create_format(QColor("#808000"), QFont.Weight.Bold),  # Dark yellow for DOCTYPE
                "entity": self.create_format(QColor("#FFD700")),                      # Gold for entities
                "script_tag": self.create_format(QColor("#4EC9B0"), QFont.Weight.Bold), # Teal for script tags
                "style_tag": self.create_format(QColor("#C586C0"), QFont.Weight.Bold), # Pink/purple for style tags
            }
        self.rehighlight() # Force re-highlight of the entire document with new colors

    def highlightBlock(self, text: str):
        self.setCurrentBlockState(0)

        for pattern_str, format_key, *group_index in self.rules:
            pattern = QRegularExpression(pattern_str)
            
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                if group_index:
                    start = match.capturedStart(group_index[0])
                    length = match.capturedLength(group_index[0])
                    if start != -1 and length > 0:
                        self.setFormat(start, length, self.formats[format_key])
                else:
                    start = match.capturedStart()
                    length = match.capturedLength()
                    self.setFormat(start, length, self.formats[format_key])

# --- Main Application Class ---
class HTMLHelperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HTML Project Helper (PyQt6)")
        self.setGeometry(100, 100, 1600, 900)

        self.current_html_path = ""
        self.current_html_content = ""
        self.sections = {}
        self.auto_refresh_enabled = True
        
        # --- Initialize QTextEdit elements and their related formats/highlighters FIRST ---
        self.full_html_text = ZoomableTextEdit() # Use our custom ZoomableTextEdit
        self.full_html_text_format = QTextCharFormat() # Used for the current selection highlight

        self.html_syntax_highlighter = HtmlHighlighter(self.full_html_text.document())

        self.code_block_text = QTextEdit()
        self.section_listbox = QListWidget() # Needs to be initialized before apply_stylesheet for the guard


        # --- Font and Theme Initialization ---
        self.current_theme = "dark" # Start in dark mode by default
        self.font_size = 12 # Default font size for code editors
        self.current_font_family = "Consolas" # Default font family for code editors
        
        self.light_stylesheet = self.get_light_stylesheet()
        self.dark_stylesheet = self.get_dark_stylesheet()
        self.apply_stylesheet(self.current_theme) # This will also set initial highlighter colors and font

        # Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status("Application started.")

        # Set up the central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Bar: File Management ---
        top_frame = QWidget()
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(0, 0, 0, 0)

        top_layout.addWidget(QLabel("HTML File:"))
        self.path_entry = QLineEdit()
        self.path_entry.setReadOnly(True)
        top_layout.addWidget(self.path_entry, 1)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)
        top_layout.addWidget(browse_button)

        load_button = QPushButton("Load HTML")
        load_button.clicked.connect(self.load_html_file)
        top_layout.addWidget(load_button)

        self.theme_toggle_button = QPushButton("Toggle Theme")
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        top_layout.addWidget(self.theme_toggle_button)

        main_layout.addWidget(top_frame)

        # --- Main Content Area: QSplitter for Left/Middle/Right ---
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter, 1)

        # --- Left Pane: Section List ---
        left_frame = QWidget()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(5, 5, 5, 5)

        left_layout.addWidget(QLabel("HTML Sections:"))
        self.section_listbox.itemSelectionChanged.connect(self.display_selected_section)
        left_layout.addWidget(self.section_listbox)
        main_splitter.addWidget(left_frame)

        # --- Middle Pane: HTML Display & Code Block Editor ---
        middle_frame = QWidget()
        middle_layout = QVBoxLayout(middle_frame)
        middle_layout.setContentsMargins(5, 5, 5, 5)

        # Font controls for Full HTML Code
        font_controls_frame = QWidget()
        font_controls_layout = QHBoxLayout(font_controls_frame)
        font_controls_layout.setContentsMargins(0,0,0,0)
        font_controls_layout.addWidget(QLabel("Font Size:"))
        
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(6, 72)
        self.font_size_slider.setValue(self.font_size)
        self.font_size_slider.setTickInterval(2)
        self.font_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_size_slider.valueChanged.connect(self.change_font_size_slider)
        font_controls_layout.addWidget(self.font_size_slider)

        self.font_size_textbox = QLineEdit()
        self.font_size_textbox.setFixedWidth(40)
        self.font_size_textbox.setText(str(self.font_size))
        self.font_size_textbox.editingFinished.connect(self.change_font_size_text)
        font_controls_layout.addWidget(self.font_size_textbox)
        
        font_controls_layout.addWidget(QLabel("Font:"))
        self.font_family_combobox = QComboBox()
        # Common code editor fonts. Add more if desired.
        self.available_fonts = ["Consolas", "Courier New", "Monaco", "Cascadia Code", "Arial", "Verdana"]
        self.font_family_combobox.addItems(self.available_fonts)
        self.font_family_combobox.setCurrentText(self.current_font_family)
        self.font_family_combobox.currentIndexChanged.connect(self.change_font_family)
        font_controls_layout.addWidget(self.font_family_combobox)
        font_controls_layout.addStretch(1) # Pushes controls to the left

        middle_layout.addWidget(font_controls_frame)


        middle_content_splitter = QSplitter(Qt.Orientation.Vertical)
        middle_layout.addWidget(middle_content_splitter, 1)

        full_html_section = QWidget()
        full_html_layout = QVBoxLayout(full_html_section)
        full_html_layout.setContentsMargins(0, 0, 0, 0)
        full_html_layout.addWidget(QLabel("Full HTML Code:"))
        
        full_html_layout.addWidget(self.full_html_text, 1)
        self.full_html_text.font_size_changed.connect(self.update_font_size_from_wheel) # Connect signal
        middle_content_splitter.addWidget(full_html_section)


        selected_code_section = QWidget()
        selected_code_layout = QVBoxLayout(selected_code_section)
        selected_code_layout.setContentsMargins(0, 0, 0, 0)
        selected_code_layout.addWidget(QLabel("Selected Code Block:"))
        selected_code_layout.addWidget(self.code_block_text, 1)
        middle_content_splitter.addWidget(selected_code_section)

        middle_content_splitter.setSizes([700, 200])

        block_buttons_frame = QWidget()
        block_buttons_layout = QHBoxLayout(block_buttons_frame)
        block_buttons_layout.setContentsMargins(0, 0, 0, 0)

        self.copy_block_button = QPushButton("Copy Block")
        self.copy_block_button.clicked.connect(self.copy_selected_block)
        block_buttons_layout.addWidget(self.copy_block_button)

        self.update_block_button = QPushButton("Update Block")
        self.update_block_button.clicked.connect(self.update_selected_block)
        self.update_block_button.setEnabled(False)
        block_buttons_layout.addWidget(self.update_block_button)
        
        block_buttons_layout.addStretch(1)

        middle_layout.addWidget(block_buttons_frame)
        main_splitter.addWidget(middle_frame)

        # --- Right Pane: Embedded Browser (QWebEngineView) ---
        right_frame = QWidget()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(5, 5, 5, 5)

        right_layout.addWidget(QLabel("Web Browser Preview:"))
        self.browser_view = QWebEngineView()
        right_layout.addWidget(self.browser_view, 1)

        refresh_controls_frame = QWidget()
        refresh_controls_layout = QHBoxLayout(refresh_controls_frame)
        refresh_controls_layout.setContentsMargins(0,0,0,0)

        refresh_browser_button = QPushButton("Refresh Browser")
        refresh_browser_button.clicked.connect(self.refresh_browser)
        refresh_controls_layout.addWidget(refresh_browser_button)

        self.auto_refresh_checkbox = QCheckBox("Auto Refresh on Update")
        self.auto_refresh_checkbox.setChecked(self.auto_refresh_enabled)
        self.auto_refresh_checkbox.stateChanged.connect(self.toggle_auto_refresh)
        refresh_controls_layout.addWidget(self.auto_refresh_checkbox)

        refresh_controls_layout.addStretch(1)

        right_layout.addWidget(refresh_controls_frame)

        main_splitter.addWidget(right_frame)
        main_splitter.setSizes([200, 800, 600])

        # Apply initial font settings to all affected widgets
        self.apply_all_code_fonts()


    def get_timestamp(self):
        return datetime.now().strftime("%m/%d/%Y %I:%M%p").lower()

    def update_status(self, message):
        self.statusBar.showMessage(f"{message} {self.get_timestamp()}")

    def get_light_stylesheet(self):
        return """
            QMainWindow, QWidget {
                background-color: #f0f0f0;
                color: #333333;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit, QListWidget, QComboBox { /* QComboBox also affected */
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
            }
            /* QTextEdit styling for light mode, separate for specific font settings */
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QCheckBox {
                color: #333333;
            }
            QStatusBar {
                background-color: #e0e0e0;
                color: #333333;
                border-top: 1px solid #cccccc;
            }
            QSplitter::handle {
                background-color: #cccccc;
            }
            QTextEdit {
                 selection-background-color: #add8e6;
                 selection-color: black;
            }
            QListWidget::item:selected {
                background-color: #a0c0e0;
                color: black;
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #d3d3d3;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #808080;
                border: 1px solid #777;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #808080;
                border-radius: 4px;
            }
        """

    def get_dark_stylesheet(self):
        return """
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QLabel {
                color: #dddddd;
            }
            QLineEdit, QListWidget, QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
            }
            QTextEdit {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
            }
            QPushButton {
                background-color: #505050;
                color: #eeeeee;
                border: 1px solid #666666;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
            QCheckBox {
                color: #cccccc;
            }
            QStatusBar {
                background-color: #3c3c3c;
                color: #cccccc;
                border-top: 1px solid #555555;
            }
            QSplitter::handle {
                background-color: #555555;
            }
            QTextEdit {
                selection-background-color: #007acc;
                selection-color: white;
            }
            QListWidget::item:selected {
                background-color: #007acc;
                color: white;
            }
            QSlider::groove:horizontal {
                border: 1px solid #444;
                background: #333;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #aaaaaa;
                border: 1px solid #777;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #aaaaaa;
                border-radius: 4px;
            }
        """

    def apply_stylesheet(self, theme_name):
        self.setStyleSheet(self.get_light_stylesheet() if theme_name == "light" else self.get_dark_stylesheet())
        
        # Adjust the selection highlight color for the current section
        if theme_name == "light":
            self.full_html_text_format.setBackground(QColor("#aaffaa"))
        else:
            self.full_html_text_format.setBackground(QColor("#555500"))

        # Update highlighter colors and rehighlight
        self.html_syntax_highlighter.set_theme_colors(theme_name)

        # Re-apply any active selection highlight after theme change
        if hasattr(self, 'section_listbox') and self.section_listbox.selectedItems():
            self.display_selected_section()

    def toggle_theme(self):
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"
        self.apply_stylesheet(self.current_theme)
        self.update_status(f"Theme switched to {self.current_theme} mode.")

    def apply_all_code_fonts(self):
        """Applies the current font family and size to the three code-related widgets."""
        font = QFont(self.current_font_family, self.font_size)
        self.full_html_text.setFont(font)
        self.code_block_text.setFont(font)
        self.section_listbox.setFont(font)
        self.update_status(f"Font set to '{self.current_font_family}', Size: {self.font_size}")


    def change_font_size_slider(self, value):
        self.font_size = value
        self.font_size_textbox.setText(str(value)) # Keep textbox in sync
        self.apply_all_code_fonts()

    def change_font_size_text(self):
        try:
            size = int(self.font_size_textbox.text())
            if 6 <= size <= 72:
                self.font_size = size
                self.font_size_slider.setValue(size) # Keep slider in sync
                self.apply_all_code_fonts()
            else:
                self.update_status("Error: Font size must be between 6 and 72.")
                self.font_size_textbox.setText(str(self.font_size)) # Revert to current valid size
        except ValueError:
            self.update_status("Error: Invalid font size. Please enter a number.")
            self.font_size_textbox.setText(str(self.font_size)) # Revert to current valid size

    def change_font_family(self, index):
        self.current_font_family = self.available_fonts[index]
        self.apply_all_code_fonts()

    def update_font_size_from_wheel(self, new_size: int):
        """Slot to receive font size changes from ZoomableTextEdit's wheelEvent."""
        self.font_size = new_size
        self.font_size_slider.setValue(new_size)
        self.font_size_textbox.setText(str(new_size))
        self.apply_all_code_fonts()


    def toggle_auto_refresh(self, state):
        self.auto_refresh_enabled = (state == Qt.CheckState.Checked.value)
        self.update_status(f"Auto refresh set to: {self.auto_refresh_enabled}")

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML files (*.html);;All files (*.*)")
        if file_path:
            self.path_entry.setText(file_path)
            self.current_html_path = file_path
            self.load_html_file()
            self.update_status(f"Selected file: '{os.path.basename(file_path)}'")


    def load_html_file(self):
        file_path = self.current_html_path
        if not file_path or not os.path.exists(file_path):
            self.update_status("Error: Please select a valid HTML file.")
            self.update_block_button.setEnabled(False)
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.current_html_content = f.read()

            self.full_html_text.setPlainText(self.current_html_content)
            self.parse_sections()
            self.update_block_button.setEnabled(True)
            self.update_status(f"'{os.path.basename(file_path)}' loaded successfully.")

            self.refresh_browser()

        except Exception as e:
            self.update_status(f"Error loading file: {e}")
            self.current_html_content = ""
            self.full_html_text.setPlainText("")
            self.sections.clear()
            self.section_listbox.clear()
            self.update_block_button.setEnabled(False)

    def parse_sections(self):
        self.sections.clear()
        self.section_listbox.clear()

        lines = self.full_html_text.toPlainText().splitlines()
        current_section_name = None
        section_start_line = -1
        section_content_lines = []

        start_pattern = re.compile(r'// START (.+)')
        end_pattern = re.compile(r'// END (.+)')

        for i, line in enumerate(lines):
            start_match = start_pattern.search(line)
            end_match = end_pattern.search(line)

            if start_match:
                if current_section_name:
                    self.update_status(f"Warning: Nested or unclosed section detected before '{start_match.group(1)}' at line {i+1}. This section will be ignored for now.")
                    current_section_name = None
                    section_start_line = -1
                    section_content_lines = []
                
                current_section_name = start_match.group(1).strip()
                section_start_line = i + 1
                section_content_lines = []
                
            elif end_match:
                end_section_name = end_match.group(1).strip()
                if current_section_name and current_section_name == end_section_name:
                    self.sections[current_section_name] = {
                        'start_line': section_start_line,
                        'end_line': i + 1,
                        'content': "\n".join(section_content_lines)
                    }
                    self.section_listbox.addItem(current_section_name)
                    current_section_name = None
                    section_start_line = -1
                    section_content_lines = []
                else:
                    self.update_status(f"Warning: Mismatched or unstarted END marker for '{end_section_name}' at line {i+1}. Ignoring.")
            elif current_section_name:
                section_content_lines.append(line)
        
        if current_section_name:
            self.update_status(f"Warning: Section '{current_section_name}' started at line {section_start_line} but no END marker found. This section is incomplete and will not be listed.")

    def display_selected_section(self):
        current_extra_selections = list(self.full_html_text.extraSelections())
        new_extra_selections = []

        for s in current_extra_selections:
            if s.format.background().color() != self.full_html_text_format.background().color():
                new_extra_selections.append(s)
        self.full_html_text.setExtraSelections(new_extra_selections)


        selected_items = self.section_listbox.selectedItems()
        if not selected_items:
            self.code_block_text.clear()
            return

        section_name = selected_items[0].text()

        if section_name in self.sections:
            section_data = self.sections[section_name]
            self.code_block_text.setPlainText(section_data['content'])

            cursor = self.full_html_text.textCursor()
            
            start_block = self.full_html_text.document().findBlockByNumber(section_data['start_line'] - 1)
            cursor.setPosition(start_block.position())
            
            end_block = self.full_html_text.document().findBlockByNumber(section_data['end_line'] - 1)
            end_pos = end_block.position() + end_block.length() -1 
            
            cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = self.full_html_text_format

            new_extra_selections.append(selection)
            self.full_html_text.setExtraSelections(new_extra_selections)

            self.full_html_text.setTextCursor(selection.cursor)
            self.full_html_text.ensureCursorVisible()
            
        else:
            self.code_block_text.clear()
            self.update_status(f"Error: Section '{section_name}' not found in parsed data.")

    def copy_selected_block(self):
        selected_text = self.code_block_text.toPlainText().strip()
        if selected_text:
            QApplication.clipboard().setText(selected_text)
            self.update_status("Selected code block copied to clipboard!")
        else:
            self.update_status("Warning: No code block selected or content is empty to copy.")

    def update_selected_block(self):
        selected_items = self.section_listbox.selectedItems()
        if not selected_items:
            self.update_status("Warning: Please select a section to update.")
            return

        section_name = selected_items[0].text()

        if section_name not in self.sections:
            self.update_status(f"Error: Section '{section_name}' not found for update.")
            return

        new_block_content = self.code_block_text.toPlainText()
        old_section_data = self.sections[section_name]

        lines = self.full_html_text.toPlainText().splitlines()
        
        new_full_content_lines = []
        new_full_content_lines.extend(lines[:old_section_data['start_line'] - 1])
        new_full_content_lines.append(lines[old_section_data['start_line'] - 1])
        new_full_content_lines.extend(new_block_content.splitlines())
        new_full_content_lines.append(lines[old_section_data['end_line'] - 1])
        new_full_content_lines.extend(lines[old_section_data['end_line']:])

        updated_html_content = "\n".join(new_full_content_lines)

        base_path, ext = os.path.splitext(self.current_html_path)
        
        match = re.search(r'(-\d+)$', base_path)
        if match:
            num = int(match.group(1)[1:])
            new_num = num + 1
            new_base_name = base_path[:match.start()]
        else:
            new_num = 1
            new_base_name = base_path

        new_file_name = f"{new_base_name}-{new_num}{ext}"

        try:
            with open(new_file_name, 'w', encoding='utf-8') as f:
                f.write(updated_html_content)

            self.full_html_text.setPlainText(updated_html_content)
            
            self.current_html_content = updated_html_content
            self.current_html_path = new_file_name
            self.path_entry.setText(new_file_name)

            self.parse_sections() 

            if self.auto_refresh_enabled:
                self.refresh_browser()

            self.update_status(f"File updated and saved as '{os.path.basename(new_file_name)}'")

        except Exception as e:
            self.update_status(f"Error saving updated file: {e}")

    def refresh_browser(self):
        current_content_for_browser = self.full_html_text.toPlainText()

        if current_content_for_browser:
            base_url = QUrl.fromLocalFile(os.path.dirname(self.current_html_path) + os.sep)
            self.browser_view.setHtml(current_content_for_browser, base_url)
            self.update_status("Browser refreshed.")
        else:
            self.browser_view.setHtml("<h1>No HTML Loaded</h1><p>Load an HTML file to preview it here.</p>")
            self.update_status("Browser content cleared (no file loaded).")

# --- Main Application Execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HTMLHelperApp()
    window.show()
    sys.exit(app.exec())
