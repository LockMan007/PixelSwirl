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
    QToolBar, QMenu
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl, QRegularExpression
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument, QFont, QSyntaxHighlighter

# --- QSyntaxHighlighter Class for HTML ---
class HtmlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)

        self.formats = {
            "tag": self.create_format(QColor("#000080"), QFont.Weight.Bold),
            "attribute": self.create_format(QColor("#800080")),
            "string": self.create_format(QColor("#008000")),
            "comment": self.create_format(QColor("#808080"), font_italic=True),
            "doctype": self.create_format(QColor("#008080"), QFont.Weight.Bold),
            "entity": self.create_format(QColor("#8B0000")),
            "script_tag": self.create_format(QColor("#0000FF"), QFont.Weight.Bold),
            "style_tag": self.create_format(QColor("#FF00FF"), QFont.Weight.Bold),
        }

        self.rules = []
        self.rules.append((r'', "comment"))
        self.rules.append((r'<!DOCTYPE.*?>', "doctype"))
        self.rules.append((r'<\s*[/]?\s*[\w:]+\b', "tag"))
        self.rules.append((r'\b[\w:]+\s*/>', "tag"))
        self.rules.append((r'>', "tag"))
        self.rules.append((r'\b([a-zA-Z_][\w\-\:]*)\s*=', "attribute", 1))
        self.rules.append((r'"[^"]*"', "string"))
        self.rules.append((r"'[^']*'", "string"))
        self.rules.append((r'&[a-zA-Z0-9#]+;', "entity"))
        self.rules.append((r'<script\b[^>]*>[\s\S]*?</script>', "script_tag"))
        self.rules.append((r'<style\b[^>]*>[\s\S]*?</style>', "style_tag"))

    def create_format(self, color: QColor, font_weight: QFont.Weight = QFont.Weight.Normal, font_italic: bool = False):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        fmt.setFontWeight(font_weight)
        fmt.setFontItalic(font_italic)
        return fmt

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
        
        # --- Crucial Order Change Starts Here ---
        # 1. Initialize QTextEdit elements and their related formats/highlighters FIRST
        # This ensures they exist before methods like apply_stylesheet or display_selected_section
        # try to access them.

        # Initialize full_html_text and its highlight format
        self.full_html_text = QTextEdit()
        self.full_html_text_format = QTextCharFormat() # Used for the current selection highlight

        # Instantiate the highlighter and associate it with the QTextEdit's document
        self.html_syntax_highlighter = HtmlHighlighter(self.full_html_text.document())

        # Initialize other QTextEdit elements
        self.code_block_text = QTextEdit()
        # --- Crucial Order Change Ends Here ---


        # Theme Management (can now be called safely)
        self.current_theme = "dark" # Default theme
        self.light_stylesheet = self.get_light_stylesheet()
        self.dark_stylesheet = self.get_dark_stylesheet()
        self.apply_stylesheet(self.current_theme) # This will now find self.full_html_text_format


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

        # Add theme toggle to top bar for easy access
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
        self.section_listbox = QListWidget()
        self.section_listbox.itemSelectionChanged.connect(self.display_selected_section)
        left_layout.addWidget(self.section_listbox)
        main_splitter.addWidget(left_frame)

        # --- Middle Pane: HTML Display & Code Block Editor ---
        middle_frame = QWidget()
        middle_layout = QVBoxLayout(middle_frame)
        middle_layout.setContentsMargins(5, 5, 5, 5)

        middle_content_splitter = QSplitter(Qt.Orientation.Vertical)
        middle_layout.addWidget(middle_content_splitter, 1)

        full_html_section = QWidget()
        full_html_layout = QVBoxLayout(full_html_section)
        full_html_layout.setContentsMargins(0, 0, 0, 0)
        full_html_layout.addWidget(QLabel("Full HTML Code:"))
        
        # Add the pre-initialized full_html_text to the layout
        full_html_layout.addWidget(self.full_html_text, 1)
        middle_content_splitter.addWidget(full_html_section)

        selected_code_section = QWidget()
        selected_code_layout = QVBoxLayout(selected_code_section)
        selected_code_layout.setContentsMargins(0, 0, 0, 0)
        selected_code_layout.addWidget(QLabel("Selected Code Block:"))
        # Add the pre-initialized code_block_text to the layout
        selected_code_layout.addWidget(self.code_block_text, 1)
        middle_content_splitter.addWidget(selected_code_section)

        middle_content_splitter.setSizes([700, 200])

        # Code Block Buttons
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

        # Refresh controls frame
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
            QLineEdit, QTextEdit, QListWidget {
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
            /* Specific styles for highlighter visibility */
            QTextEdit {
                 selection-background-color: #add8e6; /* Light blue for selected text in light mode */
                 selection-color: black;
            }
            QListWidget::item:selected {
                background-color: #a0c0e0; /* A slightly darker blue for list selection */
                color: black;
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
            QLineEdit, QTextEdit, QListWidget {
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
            /* Specific styles for highlighter visibility */
            QTextEdit {
                selection-background-color: #007acc; /* A common dark mode selection blue */
                selection-color: white;
            }
            QListWidget::item:selected {
                background-color: #007acc;
                color: white;
            }
        """

    def apply_stylesheet(self, theme_name):
        if theme_name == "light":
            self.setStyleSheet(self.light_stylesheet)
            # Adjust the highlight color for light mode (used for current selected section)
            self.full_html_text_format.setBackground(QColor("#aaffaa")) # A softer green/yellow for light mode
        else: # dark
            self.setStyleSheet(self.dark_stylesheet)
            # Adjust the highlight color for dark mode (used for current selected section)
            self.full_html_text_format.setBackground(QColor("#555500")) # A darker yellow/gold for dark mode

        # Re-apply any active selection highlight after theme change to ensure it uses the new format color
        # This can only be called if section_listbox is initialized, so we add a check.
        # During initial __init__, section_listbox isn't ready yet, so we'll skip this on first call.
        if hasattr(self, 'section_listbox') and self.section_listbox.selectedItems():
            self.display_selected_section()

    def toggle_theme(self):
        if self.current_theme == "light":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"
        self.apply_stylesheet(self.current_theme)
        self.update_status(f"Theme switched to {self.current_theme} mode.")

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
        # Clear previous highlights first
        current_extra_selections = list(self.full_html_text.extraSelections())
        new_extra_selections = []

        # Remove only our specific highlight, keep others if they exist
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

            # Highlight the section
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

        # Use the current content of the full_html_text for the update base
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