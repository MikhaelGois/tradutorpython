import os
import json
import threading
import time
from pathlib import Path
import subprocess
import sys

import flet as ft
import pyperclip
from PIL import Image, ImageDraw

from translator_clipboard import translate_text

SETTINGS_PATH = Path("launcher_settings.json")


def load_settings():
    default = {
        "theme": "dark",
        "target_lang": "pt",
        "auto_clipboard": True,
        "font_size": 14,
        "paused": False,
        "default_ui": "flet",
    }
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                s = json.load(f)
            default.update(s)
        except Exception:
            pass
    return default


def save_settings(s):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class ClipboardMonitor(threading.Thread):
    def __init__(self, page, settings, on_new_text):
        super().__init__(daemon=True)
        self.page = page
        self.settings = settings
        self.on_new_text = on_new_text
        self._last = ""
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            if not self.settings.get("paused") and self.settings.get("auto_clipboard"):
                try:
                    current = pyperclip.paste()
                except Exception:
                    current = ""
                if current and current != self._last:
                    self._last = current
                    # Call UI thread safely
                    try:
                        self.page.add_thread_safe_callback(lambda: self.on_new_text(current))
                    except Exception:
                        # older flet versions may not have add_thread_safe_callback
                        try:
                            self.page.call_from_thread(lambda: self.on_new_text(current))
                        except Exception:
                            pass
            time.sleep(0.45)

    def stop(self):
        self._stop.set()


def create_tray_icon(app):
    # Create a tiny monochrome icon in memory to avoid external assets
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((8, 8, 56, 56), fill=(30, 144, 255, 255))
    return img


def main(page: ft.Page):
    settings = load_settings()

    page.title = "Tradutor - Launcher"
    page.window_width = 700
    page.window_height = 520
    page.padding = 16

    dark = settings.get("theme", "dark") == "dark"
    page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT

    status = ft.Text("Pronto", size=12)

    lang_options = [
        ft.dropdown.Option("pt", text="Português (pt)"),
        ft.dropdown.Option("en", text="Inglês (en)"),
        ft.dropdown.Option("es", text="Espanhol (es)"),
        ft.dropdown.Option("auto", text="Detectar (auto)"),
    ]

    target_dropdown = ft.Dropdown(width=220, value=settings.get("target_lang", "pt"), options=lang_options)

    # Make text fields constrained and scrollable to avoid UI collapse on large paste
    input_field = ft.TextField(label="Texto de entrada", multiline=True, min_lines=3, max_lines=12, expand=True)
    output_field = ft.TextField(label="Tradução", multiline=True, read_only=True, min_lines=3, max_lines=12, expand=True)

    font_size_slider = ft.Slider(value=settings.get("font_size", 14), min=12, max=28, divisions=8, label="Tamanho da fonte")

    def apply_font_size(e=None):
        size = int(font_size_slider.value)
        input_field.style = ft.TextStyle(size=size)
        output_field.style = ft.TextStyle(size=size)
        status.style = ft.TextStyle(size=max(10, size-2))
        settings["font_size"] = size
        save_settings(settings)
        page.update()

    font_size_slider.on_change = lambda e: apply_font_size()

    auto_checkbox = ft.Checkbox(label="Auto-colar (monitorar clipboard)", value=settings.get("auto_clipboard", True))

    def on_translate_click(e=None):
        text = input_field.value or ""
        if not text.strip():
            page.snack_bar = ft.SnackBar(ft.Text("Nada para traduzir."))
            page.snack_bar.open = True
            page.update()
            return
        status.value = "Traduzindo..."
        page.update()
        try:
            translated, src = translate_text(text, target_dropdown.value if target_dropdown.value != "auto" else "pt")
            header = f"[Idioma origem: {src}]\n" if src else ""
            output_field.value = f"{header}{translated}"
            status.value = "Pronto"
        except Exception as err:
            status.value = "Erro"
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao traduzir: {err}"))
            page.snack_bar.open = True
        page.update()

    translate_button = ft.Button("Traduzir (Ctrl+Enter)", on_click=on_translate_click)

    def on_new_clipboard(text: str):
        # update input field and optionally auto-translate
        input_field.value = text
        if settings.get("auto_clipboard"):
            on_translate_click()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Texto copiado detectado."))
            page.snack_bar.open = True
        page.update()

    # Start clipboard monitor thread
    monitor = ClipboardMonitor(page, settings, on_new_clipboard)
    monitor.start()

    # --- UI switching helpers ---
    def launch_other_ui():
        # Launch the older Tkinter clipboard popup script in a detached process
        other = Path(__file__).parent / "translator_clipboard.py"
        if not other.exists():
            page.snack_bar = ft.SnackBar(ft.Text("Arquivo alternativo não encontrado."))
            page.snack_bar.open = True
            page.update()
            return
        try:
            creationflags = 0x00000008  # DETACHED_PROCESS
            subprocess.Popen([sys.executable, str(other)], creationflags=creationflags)
            page.snack_bar = ft.SnackBar(ft.Text("UI alternativo iniciado."))
            page.snack_bar.open = True
            page.update()
        except Exception as err:
            page.snack_bar = ft.SnackBar(ft.Text(f"Falha ao iniciar UI: {err}"))
            page.snack_bar.open = True
            page.update()

    def set_default_ui(value: str):
        settings["default_ui"] = value
        save_settings(settings)
        page.snack_bar = ft.SnackBar(ft.Text(f"Padrão salvo: {value}"))
        page.snack_bar.open = True
        page.update()

    def switch_now(e):
        other = settings.get("default_ui", "flet")
        # if default is flet, switch to tk, else to flet
        target = "translator_clipboard.py" if other == "flet" else Path(__file__).name
        try:
            subprocess.Popen([sys.executable, str(Path(__file__).parent / target)], creationflags=0x00000008)
        except Exception:
            pass
        # close current app
        try:
            monitor.stop()
        except Exception:
            pass
        try:
            page.window_close()
        except Exception:
            pass

    def toggle_theme(e):
        settings["theme"] = "dark" if page.theme_mode == ft.ThemeMode.LIGHT else "light"
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        save_settings(settings)
        page.update()

    # Theme toggle button (text-based for maximum compatibility)
    theme_toggle = ft.TextButton("Tema claro/escuro", on_click=toggle_theme)

    def on_auto_change(e):
        settings["auto_clipboard"] = auto_checkbox.value
        save_settings(settings)

    auto_checkbox.on_change = on_auto_change

    def on_pause_resume(e):
        settings["paused"] = not settings.get("paused", False)
        save_settings(settings)
        status.value = "Pausado" if settings["paused"] else "Pronto"
        page.update()

    pause_button = ft.Button("Pausar/Retomar (Tray)", on_click=on_pause_resume)

    # Tray (pystray) integration (runs isolated)
    try:
        import pystray

        def tray_thread():
            icon_image = create_tray_icon(None)

            def on_quit(icon, item):
                icon.stop()
                monitor.stop()
                try:
                    page.window_close()
                except Exception:
                    pass

            def on_toggle(icon, item):
                settings["paused"] = not settings.get("paused", False)
                save_settings(settings)
                # update UI from main thread
                try:
                    page.add_thread_safe_callback(lambda: setattr(status, "value", "Pausado" if settings["paused"] else "Pronto"))
                except Exception:
                    try:
                        page.call_from_thread(lambda: setattr(status, "value", "Pausado" if settings["paused"] else "Pronto"))
                    except Exception:
                        pass

            menu = pystray.Menu(
                pystray.MenuItem("Pausar/Retomar", on_toggle),
                pystray.MenuItem("Sair", on_quit),
            )
            icon = pystray.Icon("tradutor", icon_image, "Tradutor", menu)
            icon.run()

        t = threading.Thread(target=tray_thread, daemon=True)
        t.start()
    except Exception:
        # tray optional; ignore failures
        pass

    # Layout
    ui_choice = ft.Dropdown(width=180, value=settings.get("default_ui", "flet"), options=[
        ft.dropdown.Option("flet", text="Flet UI"),
        ft.dropdown.Option("tk", text="Tkinter Popup"),
    ])

    launch_alt_btn = ft.Button("Iniciar UI alternativo", on_click=lambda e: launch_other_ui())
    save_default_btn = ft.Button("Salvar como padrão", on_click=lambda e: set_default_ui(ui_choice.value))
    switch_btn = ft.Button("Trocar agora", on_click=switch_now)

    controls = ft.Row([
        target_dropdown,
        translate_button,
        pause_button,
        theme_toggle,
    ], alignment=ft.MainAxisAlignment.START)

    # Use a scrollable, expanding column so the UI adapts to large content
    page.add(
        ft.Column(
            [
                ft.Text("Tradutor — Clipboard", size=18, weight=ft.FontWeight.BOLD),
                controls,
                input_field,
                output_field,
                ft.Row([auto_checkbox, ft.Column([font_size_slider])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ui_choice, launch_alt_btn, save_default_btn, switch_btn], alignment=ft.MainAxisAlignment.START),
                ft.Divider(),
                ft.Row([status], alignment=ft.MainAxisAlignment.START),
            ],
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
    )

    # apply initial font size
    apply_font_size()


if __name__ == "__main__":
    ft.app(target=main)
