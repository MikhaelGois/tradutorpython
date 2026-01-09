import os
import io
import json
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import mss
import pytesseract
import requests
from pynput import keyboard

# Ajuste o caminho do Tesseract no Windows se necessário
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DEFAULT_TARGET_LANG = "pt"
AZURE_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_REGION = os.getenv("AZURE_TRANSLATOR_REGION")
LIBRE_URL = os.getenv("LIBRE_TRANSLATE_URL")
GOOGLE_KEY = os.getenv("GOOGLE_TRANSLATE_KEY")  # Google Cloud Translate API key (optional)
# Usar Google web (deep-translator) por padrão
USE_GOOGLE_WEB = True


def translate_text(text, target_lang=DEFAULT_TARGET_LANG):
    text = text.strip()
    if not text:
        return None
    if USE_GOOGLE_WEB:
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            return translated, ""
        except Exception:
            pass
    if GOOGLE_KEY:
        # Google Cloud Translate (v2) using API key
        endpoint = f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_KEY}"
        payload = {"q": text, "target": target_lang, "format": "text", "source": ""}
        r = requests.post(endpoint, data=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        translations = data.get("data", {}).get("translations", [])
        if translations:
            translated = translations[0].get("translatedText", "")
            source_lang = translations[0].get("detectedSourceLanguage", "")
            return translated, source_lang
        return None
    if AZURE_KEY and AZURE_REGION:
        endpoint = "https://api.cognitive.microsofttranslator.com/translate"
        params = {"api-version": "3.0", "to": [target_lang]}
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Ocp-Apim-Subscription-Region": AZURE_REGION,
            "Content-type": "application/json"
        }
        body = [{"text": text}]
        r = requests.post(endpoint, params=params, headers=headers, data=json.dumps(body), timeout=10)
        r.raise_for_status()
        data = r.json()
        translated = data[0]["translations"][0]["text"]
        source_lang = data[0].get("detectedLanguage", {}).get("language", "")
        return translated, source_lang
    elif LIBRE_URL:
        endpoint = f"{LIBRE_URL}/translate"
        payload = {"q": text, "source": "auto", "target": target_lang, "format": "text"}
        r = requests.post(endpoint, data=payload, timeout=10)
        r.raise_for_status()
        translated = r.json().get("translatedText")
        return translated, ""
    else:
        raise RuntimeError("Nenhum serviço de tradução configurado. Defina AZURE_* ou LIBRE_TRANSLATE_URL.")


class TranslatorApp(tk.Tk):
    def __init__(self, fullscreen_ocr_default=False):
        super().__init__()
        self.fullscreen_ocr_default = fullscreen_ocr_default
        self.title("Tradutor com OCR")
        self.geometry("620x420+100+100")
        self.attributes("-topmost", True)
        # UI
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Label(frm, text="Idioma de destino (ex.: pt, en, es):").grid(row=0, column=0, sticky="w")
        self.target_var = tk.StringVar(value=DEFAULT_TARGET_LANG)
        ttk.Entry(frm, textvariable=self.target_var, width=8).grid(row=0, column=1, sticky="w")
        ttk.Label(frm, text="Mensagem para traduzir:").grid(row=1, column=0, columnspan=2, sticky="w", pady=(8,2))
        self.input_txt = tk.Text(frm, height=6, wrap="word")
        self.input_txt.grid(row=2, column=0, columnspan=2, sticky="nsew")
        frm.rowconfigure(2, weight=1)
        frm.columnconfigure(1, weight=1)
        self.output_txt = tk.Text(frm, height=8, wrap="word", state="normal")
        self.output_txt.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(8,0))
        frm.rowconfigure(3, weight=1)
        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)
        self.btn_translate = ttk.Button(btn_frm, text="Traduzir (Ctrl+Enter)", command=self.translate_message)
        self.btn_translate.pack(side="left")
        self.btn_ocr = ttk.Button(btn_frm, text="OCR da Tela (Ctrl+Alt+O)", command=self.start_ocr_selection)
        self.btn_ocr.pack(side="left", padx=8)
        self.bind_all("<Control-Return>", lambda e: self.translate_message())
        self.geometry_selector = None
        # Hotkey global (Ctrl+Alt+O) para abrir seleção de área
        threading.Thread(target=self.hotkey_listener, daemon=True).start()
        # If requested, start OCR in fullscreen automatically once UI is ready
        if self.fullscreen_ocr_default:
            self.after(500, self.start_ocr_selection)

    def hotkey_listener(self):
        COMBO = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode.from_char('o')}
        current = set()
        def on_press(key):
            try:
                current.add(key)
            except Exception:
                pass
            if all(k in current for k in COMBO):
                self.after(0, self.start_ocr_selection)
        def on_release(key):
            try:
                current.discard(key)
            except Exception:
                pass
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    def translate_message(self):
        text = self.input_txt.get("1.0", "end").strip()
        target = self.target_var.get().strip() or DEFAULT_TARGET_LANG
        self.output_txt.delete("1.0", "end")
        try:
            result = translate_text(text, target)
            if result:
                translated, src = result
                header = f"[origem: {src}] " if src else ""
                self.output_txt.insert("1.0", f"{header}{translated}")
        except Exception as e:
            self.output_txt.insert("1.0", f"Erro: {e}")

    def start_ocr_selection(self):
        if self.geometry_selector and tk.Toplevel.winfo_exists(self.geometry_selector):
            return
        self.geometry_selector = SelectionOverlay(self, self.on_region_selected)

    def on_region_selected(self, bbox):
        # bbox: (x1, y1, x2, y2)
        try:
            with mss.mss() as sct:
                x1, y1, x2, y2 = bbox
                left, top, width, height = x1, y1, x2 - x1, y2 - y1
                img = sct.grab({"left": left, "top": top, "width": width, "height": height})
                # Convert to PIL
                pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        except Exception as e:
            self.output_txt.delete("1.0", "end")
            self.output_txt.insert("1.0", f"Falha ao capturar tela: {e}")
            return
        try:
            ocr_text = pytesseract.image_to_string(pil_img)
            target = self.target_var.get().strip() or DEFAULT_TARGET_LANG
            result = translate_text(ocr_text, target)
            self.output_txt.delete("1.0", "end")
            if result:
                translated, src = result
                header = f"[origem: {src}] " if src else ""
                self.output_txt.insert("1.0", f"{header}{translated}")
        except Exception as e:
            self.output_txt.delete("1.0", "end")
            self.output_txt.insert("1.0", f"Erro no OCR/Tradução: {e}")


class SelectionOverlay(tk.Toplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback = callback
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-alpha", 0.2)
        self.attributes("-topmost", True)
        self.config(bg="gray")
        # Tela cheia
        self.update_idletasks()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+0+0")
        self.deiconify()
        self.start = None
        self.rect = None
        self.canvas = tk.Canvas(self, bg=self['bg'], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def on_click(self, event):
        self.start = (event.x, event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                 outline="red", width=2)

    def on_drag(self, event):
        if not self.start:
            return
        x1, y1 = self.start
        x2, y2 = event.x, event.y
        self.canvas.coords(self.rect, x1, y1, x2, y2)

    def on_release(self, event):
        if not self.start:
            return
        x1, y1 = self.start
        x2, y2 = event.x, event.y
        # Converter coords relativas da Toplevel em coords da tela
        abs_x = self.winfo_rootx()
        abs_y = self.winfo_rooty()
        bbox = (x1 + abs_x, y1 + abs_y, x2 + abs_x, y2 + abs_y)
        self.destroy()
        self.callback(bbox)


class OverlayWindow(tk.Toplevel):
    def __init__(self, img_size, lines, translations_map, timeout=8):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        # Slight transparency so user can still see underlying text
        try:
            self.attributes("-alpha", 0.85)
        except Exception:
            pass
        w, h = img_size
        # Place fullscreen
        self.geometry(f"{w}x{h}+0+0")
        self.canvas = tk.Canvas(self, width=w, height=h, highlightthickness=0, bg='')
        self.canvas.pack(fill="both", expand=True)
        # Draw translations
        for key in sorted(lines.keys()):
            info = lines[key]
            left = info.get('left', 0)
            top = info.get('top', 0)
            text = translations_map.get(key, '')
            if not text:
                continue
            # Draw a semi-opaque background box if possible (approximate using a filled rectangle)
            try:
                rect = self.canvas.create_rectangle(left, top, info.get('right', left)+4, info.get('bottom', top)+4, fill='yellow', outline='')
            except Exception:
                rect = None
            # Place text on top
            self.canvas.create_text(left+2, top+2, anchor='nw', text=text, fill='black', font=(None, 12))
        # Close on click or Escape
        self.bind('<Button-1>', lambda e: self.destroy())
        self.bind('<Escape>', lambda e: self.destroy())
        # Auto destroy after timeout seconds
        self.after(int(timeout*1000), self.destroy)


if __name__ == "__main__":
    app = TranslatorApp()
    app.mainloop()
