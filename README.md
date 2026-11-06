# OCR Search Engine
Build by Isiaka Kebe.

## Run locally
Python 3.11 or newer (tested on 3.14). Install Tesseract OCR first (see below). From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python app/main.py
```
On Windows activate with `.venv\Scripts\activate` and copy `.env.example` to `.env` using File Explorer or `copy .env.example .env`.
Open https://127.0.0.1:8000/. Interactive API documentation: https://127.0.0.1:8000/docs. On first start the app creates a self-signed certificate in `certs/` (not committed); the browser warns once, so choose Advanced and continue. Delete `certs/` to generate a new one.

Click **Try sample invoice** to explore without credentials. Ask about the total or due date, or summarize. This mode uses fixed fictional text and fixed answers. It does not perform OCR or call an LLM.

The `samples/` folder holds fictional receipts, invoices, and an employee form in every supported format (PNG, text PDF, scanned PDF, DOCX, TXT) for trying OCR and detail extraction. Regenerate them with `python samples/generate_samples.py`. All data is made up; the SSN 987-65-4320 is from the range reserved for examples.

## Enable real OCR and AI
1. OCR runs locally with Tesseract by default (`OCR_ENGINE=tesseract`). On Windows install it with `winget install UB-Mannheim.TesseractOCR`; the app finds it on PATH or in `C:\Program Files\Tesseract-OCR`, or set TESSERACT_CMD. No account or key is needed for OCR.
2. Optional, for Google Cloud Vision instead: set `OCR_ENGINE=vision`, create/select a Google Cloud project, enable billing and Cloud Vision API, then set up Application Default Credentials using `gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON path outside this project.
3. Create a Gemini API key in Google AI Studio. Put it in GEMINI_API_KEY in .env. Never put keys in the frontend or commit them.
4. GEMINI_MODEL defaults to gemini-2.5-flash. Change it to a model available to your account if needed.
5. Restart the server and upload an image or document. Images and scanned PDF pages are OCRed by the configured engine; Gemini receives extracted source text and your question. Provider charges may apply for Gemini and Vision.

Original files are not saved. Extracted text, including any personal details such as SSNs, is stored unencrypted in local documents.sqlite3. To clear data, stop the server and delete that file. Intended for one person on localhost: no authentication, tenant isolation, rate limits, malware scanning, or production deployment configuration is included.

## What is implemented
- HTTPS on localhost with an automatically generated self-signed certificate.
- Validated PNG/JPEG/WebP uploads, 10 MB limit, 16-million-pixel limit.
- PDF uploads (up to 30 pages): pages with a text layer are read locally with pypdfium2; scanned pages are rendered and OCRed. Word (.docx) and UTF-8 text (.txt/.md/.csv) files are read locally.
- Image orientation correction, grayscale conversion and Gaussian smoothing with OpenCV.
- Local Tesseract OCR (default) or Google Cloud Vision document OCR, whitespace cleaning, rule-based email and currency extraction.
- "Extract details" panel (`POST /api/extract`, field list at `GET /api/fields`): choose any of emails, phone numbers, money amounts, dates, invoice/order/account numbers, all numbers, people's names, organizations, street addresses, and Social Security numbers. Runs locally: regular expressions for structured details, spaCy `en_core_web_sm` plus label rules ("Name:", "Cashier:") for names. SSNs are masked on screen until "Show full SSNs" is ticked; results can be copied or downloaded as CSV. Names and organizations are best-effort guesses and should be checked.
- SQLite persistence and document selection.
- Overlapping text chunks and simple keyword-ranked retrieval for questions.
- Gemini structured answers with source quotations and chunk IDs. Quotations must occur verbatim in their cited chunk. This checks quote existence, not whether every claim is supported; inspect the source.
- Full-document summary with a 70,000-character limit; longer documents are rejected rather than silently summarized partially.
- Actual OCR and answer elapsed times. No sub-second performance claim is made.
- Explicit sample mode, error handling, REST endpoints and a browser interface.

This version handles individual images and documents, not bulk datasets, vector search, or multiple independently deployed microservices. It provides a foundation for those extensions. Detail extraction combines regular expressions with spaCy's small pretrained English model; it is not trained on this project's documents, so names and organizations need review. Addresses and phone numbers follow US formats.

## API examples
```bash
curl -k -F 'file=@invoice.png' https://127.0.0.1:8000/api/documents
curl -k -H 'Content-Type: application/json' -d '{"document_id":"ID_FROM_UPLOAD","question":"What is the total?"}' https://127.0.0.1:8000/api/ask
curl -k -H 'Content-Type: application/json' -d '{"document_id":"ID_FROM_UPLOAD"}' https://127.0.0.1:8000/api/summarize
curl -k -H 'Content-Type: application/json' -d '{"document_id":"ID_FROM_UPLOAD","fields":["emails","names","ssns"]}' https://127.0.0.1:8000/api/extract
```
Other routes: GET /api/health, GET /api/fields, GET /api/documents, GET /api/documents/{id}, POST /api/demo.

## Tests
```bash
python -m pytest -q
```
Tests use provider doubles and never consume Google API quota. They cover upload validation, the image-to-text-to-answer workflow, PDF (text and scanned), Word and text uploads, detail extraction including SSN rules, persistence, sample behavior, retrieval and request errors. One test runs the real Tesseract and is skipped if it is not installed. A live cloud smoke test requires your own credentials and an image with known text; compare extracted text and answers against that image.

## Explain it in an interview
“I built a Python application that turns images, PDFs, and Word documents into searchable text. Images and scanned PDF pages go through OCR, with Tesseract running locally by default and Google Cloud Vision as an option; PDFs that already contain text are read directly, which avoids OCR cost. I use OpenCV to prepare images before OCR. Users choose which details to pull out, such as emails, phone numbers, dates, amounts, addresses, names, or Social Security numbers, using regular expressions plus a spaCy language model; SSNs are masked on screen by default. Users can also ask questions or request summaries through Gemini, and the interface shows source quotations so they can check each answer. I exposed the workflow through a FastAPI REST API served over HTTPS, stored the extracted text in SQLite, and covered it with pytest tests.”

Python coordinates the steps; OpenCV processes images; Tesseract or Vision reads words; pypdfium2 and python-docx read PDFs and Word files; spaCy and regular expressions find details; Gemini interprets the extracted text; FastAPI exposes endpoints; SQLite stores text. The sample button bypasses the Google services and must not be presented as a live AI demonstration.

## Official references
- https://github.com/tesseract-ocr/tesseract
- https://spacy.io/models/en
- https://docs.cloud.google.com/vision/docs/ocr
- https://docs.cloud.google.com/docs/authentication/provide-credentials-adc
- https://googleapis.github.io/python-genai/
- https://ai.google.dev/gemini-api/docs/api-key
