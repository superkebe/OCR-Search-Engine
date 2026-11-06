import os
import tempfile

# app.main builds a module-level app on import; keep its database out of the project folder.
os.environ["OCR_DB"] = os.path.join(tempfile.mkdtemp(prefix="ocr_search_tests_"), "import.sqlite3")
