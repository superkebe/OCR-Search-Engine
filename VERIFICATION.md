# Verification

- Seventeen automated tests passed using Python 3.14 on Windows 11, including one that runs the real Tesseract 5.4 OCR engine on a rendered image.
- A real local Uvicorn server served the interface over HTTPS with the generated self-signed certificate (verified against that certificate for both 127.0.0.1 and localhost); plain HTTP on the same port is refused.
- Every file in `samples/` was run through the real extraction pipeline (Tesseract for images and the scanned PDF, the PDF text layer, python-docx, plain text). Totals, invoice numbers, and due dates were all recovered correctly.
- Over HTTPS, the employee form sample was uploaded and `/api/extract` returned the expected names, both addresses, both phone numbers, the email, and the SSN.
- Google Cloud Vision and Gemini calls were tested with provider doubles. No live provider request was made because user credentials were not supplied.
- Source quote verification rejects fabricated quotation references in the tests. It does not establish the factual correctness of every generated sentence.
- Name and organization extraction was checked only against the fictional samples; expect misses and false positives on other documents.
- requirements-lock.txt records the dependency versions installed during verification. Use `python -m pip install -r requirements-lock.txt` to reproduce them.
