import os
import time
import threading
import json
import pyperclip
import tkinter as tk
from tkinter import ttk
import requests

TARGET_LANG = "pt"  # idioma de destino (ex.: 'pt', 'en', 'es')
SHOW_SOURCE_LANG = True  # se quiser mostrar o idioma detectado

AZURE_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_REGION = os.getenv("AZURE_TRANSLATOR_REGION")
LIBRE_URL = os.getenv("LIBRE_TRANSLATE_URL")  # ex.: https://libretranslate.com
GOOGLE_KEY = os.getenv("GOOGLE_TRANSLATE_KEY")  # Google Cloud Translate API key (optional)
# Usar Google Translate via web (deep-translator) por padrão para não exigir chave nem terminal
USE_GOOGLE_WEB = True


def translate_text(text, target_lang=TARGET_LANG):
    text = text.strip()
    if not text:
        return None
    if USE_GOOGLE_WEB:
        # Google Translate via web (deep-translator). Não exige chave, mas depende de scraping.
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            return translated, ""
        except Exception:
            # fallback para outras opções
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
        # Microsoft Translator (Azure)
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
        # LibreTranslate (sem API key por padrão; alguns servidores exigem)
        endpoint = f"{LIBRE_URL}/translate"
        payload = {"q": text, "source": "auto", "target": target_lang, "format": "text"}
        r = requests.post(endpoint, data=payload, timeout=10)
        r.raise_for_status()
        translated = r.json().get("translatedText")
        return translated, ""
    else:
        raise RuntimeError("Nenhum serviço de tradução configurado. Defina AZURE_* ou LIBRE_TRANSLATE_URL.")


class Popup:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tradução")
        self.root.attributes("-topmost", True)
        self.root.geometry("500x250+50+50")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.txt = tk.Text(self.root, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=8, pady=8)
        self.btn = ttk.Button(self.root, text="Fechar", command=self.on_close)
        self.btn.pack(pady=(0,8))
        self.root.withdraw()

    def show(self, content):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", content)
        self.root.deiconify()
        self.root.update()

    def on_close(self):
        self.root.withdraw()

    def loop(self):
        self.root.mainloop()


def monitor_clipboard(popup: Popup):
    last = ""
    while True:
        try:
            current = pyperclip.paste()
        except Exception:
            current = ""
        if current and current != last:
            try:
                result = translate_text(current)
                if result:
                    translated, src = result
                    header = f"[Idioma origem: {src}] " if (SHOW_SOURCE_LANG and src) else ""
                    popup.show(f"{header}{translated}")
            except Exception as e:
                popup.show(f"Erro ao traduzir: {e}")
            last = current
        time.sleep(0.4)


if __name__ == "__main__":
    popup = Popup()
    t = threading.Thread(target=monitor_clipboard, args=(popup,), daemon=True)
    t.start()
    popup.loop()
