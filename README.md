# Tradutor em Tempo Real

Aplicação local de tradução por clipboard e launcher GUI.

Principais scripts:
- `translator_clipboard.py`: monitor de clipboard que traduz automaticamente o texto copiado (Tkinter popup).
- `translator_launcher.py`: launcher moderno em Flet com seleção de UI, tema, histórico e monitor de clipboard.

Como executar (desenvolvimento):
1. Crie e ative um venv (recomendado):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. Instale dependências:
```powershell
python -m pip install -r requirements.txt
```
3. Execute o launcher Flet:
```powershell
python translator_launcher.py
```

Gerar EXE (Windows):
- Usamos `PyInstaller` para empacotar. Exemplo:
```powershell
pyinstaller --noconfirm --onefile --windowed --name TradutorLauncher translator_launcher.py
pyinstaller --noconfirm --onefile --windowed --name TradutorReal translator_clipboard.py
```

Instalador (opcional):
- Há um script `installer.iss` (Inno Setup) para gerar um instalador Windows. Compile com o Inno Setup Compiler (ISCC).

Observações:
- O tradutor usa `deep-translator` (Google web scraping) por padrão; é possível configurar APIs (Google Cloud, Azure, LibreTranslate) via variáveis de ambiente.
- OCR está disponível em arquivos separados, mas desabilitado no launcher por padrão.

Licença e contribuições
- Pull requests são bem-vindos. Ajuste o README conforme necessário.
# Tradutor em tempo real (Clipboard + OCR)

Scripts incluídos:

- `translator_clipboard.py` — observa o clipboard e traduz automaticamente o texto copiado (mostra em pop-up).
- `translator_ocr_hotkey.py` — app GUI: digite texto para traduzir, ou pressione `Ctrl+Alt+O` para selecionar uma área da tela (OCR → tradução).

Pré-requisitos

1. Python 3.8+
2. Instalar dependências:

```bash
pip install -r requirements.txt
```

3. Para OCR: instalar Tesseract OCR no sistema. No Windows, adicione a instalação e (se necessário) ajuste o caminho em `translator_ocr_hotkey.py`:

```python
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Configurar serviço de tradução (uma das opções):

- Azure Translator (recomendado): exporte as variáveis de ambiente `AZURE_TRANSLATOR_KEY` e `AZURE_TRANSLATOR_REGION`.
- LibreTranslate: defina `LIBRE_TRANSLATE_URL`, ex.: `https://libretranslate.com`.
- Offline: use `argostranslate` e adapte `translate_text()` para usar Argos (veja documentação do Argos).
 - Google Cloud Translate: defina `GOOGLE_TRANSLATE_KEY` com sua API key (v2 REST endpoint). Quando presente, os scripts usarão o Google Translate.
 - Google web (padrão): os scripts agora usam `deep-translator` para acessar o Google Translate público sem chave, portanto não é necessário fornecer variáveis de ambiente nem digitar nada no terminal — basta executar o app/exe.
 - Google Cloud Translate (opcional): se preferir usar a API paga com chave, defina `GOOGLE_TRANSLATE_KEY` e o script usará a API quando disponível.

Execução

- Monitor de clipboard:

```bash
python "translator_clipboard.py"
```

- App OCR + GUI:

```bash
python "translator_ocr_hotkey.py"
```

Notas

- Para empacotar em .exe (Windows): `pip install pyinstaller` →
  `pyinstaller --noconsole --onefile translator_ocr_hotkey.py`.
- Evite traduzir conteúdo sensível em serviços online — prefira modo offline com Argos para privacidade.
