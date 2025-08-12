# event_handler.py

import tkinter as tk

class EventHandler:
    def __init__(self, app_context):
        self.app_context = app_context

    def on_send_button_click(self, message=None):
        # 🆕 Check if the argument is a Tkinter Event object, which happens on a keypress.
        # If it is, get the message from the entry box.
        if isinstance(message, tk.Event):
            message = self.app_context.message_entry.get()

        if message and self.app_context._is_connected:
            self.app_context.send_text_message(message)

    def on_connect_button_click(self, host, port):
        self.app_context.connect_to_server(host, port)
    
    def on_disconnect_button_click(self):
        self.app_context.cleanup_connection()