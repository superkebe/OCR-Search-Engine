import io
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from app.main import MAX_PIXELS, create_app, clean_text, generate, select_context


def client(tmp_path, **kwargs):
    return TestClient(create_app(str(tmp_path / "test.sqlite3"), **kwargs))


def png(size=(60, 40), mode="RGB"):
    image = io.BytesIO()
    Image.new(mode, size, "white").save(image, format="PNG")
    return image.getvalue()


def test_demo_answers_and_unknown(tmp_path):
    c = client(tmp_path)
    doc = c.post("/api/demo").json()
    result = c.post("/api/ask", json={"document_id": doc["id"], "question": "What is the total?"}).json()
    assert "$365.50" in result["answer"]
    assert result["mode"] == "demo"
    assert [e["quote"] for e in result["evidence"]] == ["Total due: $365.50"]
    for evidence in result["evidence"]:
        assert evidence["quote"] in doc["text"]
    result = c.post("/api/ask", json={"document_id": doc["id"], "question": "When is payment due?"}).json()
    assert [e["quote"] for e in result["evidence"]] == ["Payment due: November 20, 2026"]
    for question in ["Who signed it?", "What is the subtotal?", "Is it overdue?"]:
        result = c.post("/api/ask", json={"document_id": doc["id"], "question": question}).json()
        assert result["evidence"] == [], question
        assert "$365.50" not in result["answer"], question
    assert c.post("/api/summarize", json={"document_id": doc["id"]}).status_code == 200


def test_invalid_image_never_calls_provider(tmp_path):
    def fail(data):
        raise AssertionError("Provider should not be called")
    c = client(tmp_path, ocr_fn=fail)
    assert c.post("/api/documents", files={"file": ("bad.png", b"bad", "image/png")}).status_code == 415
    # A valid PNG header proves the size limit, not the format check, rejects it.
    oversized = png() + b"\x00" * (10 * 1024 * 1024)
    assert c.post("/api/documents", files={"file": ("big.png", oversized)}).status_code == 413
    huge = png((MAX_PIXELS // 4000 + 1, 4000), mode="1")
    assert c.post("/api/documents", files={"file": ("huge.png", huge)}).status_code == 413


def test_blank_ocr_result_is_rejected(tmp_path):
    c = client(tmp_path, ocr_fn=lambda data: "  \n\t ")
    assert c.post("/api/documents", files={"file": ("blank.png", png())}).status_code == 422
    assert c.get("/api/documents").json() == []


def test_cloud_pipeline_with_provider_doubles_and_persistence(tmp_path):
    def ocr(data):
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        return "Invoice 123\n Total:   $20.00 "
    def answer(text, question, summary):
        assert text == "Invoice 123\nTotal: $20.00"
        return {"answer": "$20.00", "evidence": [{"chunk_id": 0, "quote": "Total: $20.00"}]}
    c = client(tmp_path, ocr_fn=ocr, answer_fn=answer)
    r = c.post("/api/documents", files={"file": ("invoice.png", png())})
    assert r.status_code == 200
    doc = r.json()
    assert doc["mode"] == "cloud"
    assert "$20.00" in doc["entities"]["amounts"]
    assert c.post("/api/ask", json={"document_id": doc["id"], "question": "total?"}).json()["answer"] == "$20.00"
    second = client(tmp_path)
    assert second.get("/api/documents/" + doc["id"]).json()["text"] == doc["text"]
    assert [d["id"] for d in second.get("/api/documents").json()] == [doc["id"]]


def text_pdf(line):
    # Minimal one-page PDF with a real text layer (Helvetica is a built-in PDF font).
    stream = f"BT /F1 12 Tf 72 720 Td ({line}) Tj ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def test_pdf_with_text_layer_skips_ocr(tmp_path):
    def fail(data):
        raise AssertionError("A PDF with a text layer should not be OCRed")
    c = client(tmp_path, ocr_fn=fail)
    r = c.post("/api/documents", files={"file": ("invoice.pdf", text_pdf("Invoice 7 Total due: $42.00"))})
    assert r.status_code == 200, r.text
    assert "Total due: $42.00" in r.json()["text"]
    assert "$42.00" in r.json()["entities"]["amounts"]


def test_scanned_pdf_pages_are_ocred(tmp_path):
    calls = []
    def ocr(data):
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        calls.append(data)
        return f"Scanned page {len(calls)}"
    scan = io.BytesIO()
    pages = [Image.new("RGB", (300, 400), "white") for _ in range(2)]
    pages[0].save(scan, format="PDF", save_all=True, append_images=pages[1:])
    c = client(tmp_path, ocr_fn=ocr)
    r = c.post("/api/documents", files={"file": ("scan.pdf", scan.getvalue())})
    assert r.status_code == 200, r.text
    assert len(calls) == 2
    assert r.json()["text"] == "Scanned page 1\n\nScanned page 2"


def test_bad_pdf_is_rejected(tmp_path):
    c = client(tmp_path)
    assert c.post("/api/documents", files={"file": ("bad.pdf", b"%PDF-1.4 garbage")}).status_code == 415


def test_docx_and_text_files_are_read_locally(tmp_path):
    docx = pytest.importorskip("docx")
    def fail(data):
        raise AssertionError("Word and text files should not be OCRed")
    c = client(tmp_path, ocr_fn=fail)
    document = docx.Document()
    document.add_paragraph("Contract for billing@example.com")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Fee", "$1,200.00"
    word = io.BytesIO()
    document.save(word)
    r = c.post("/api/documents", files={"file": ("contract.docx", word.getvalue())})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "Contract for billing@example.com\nFee | $1,200.00"
    r = c.post("/api/documents", files={"file": ("notes.txt", "﻿Meeting notes\nTotal: $5".encode())})
    assert r.json()["text"] == "Meeting notes\nTotal: $5"
    assert c.post("/api/documents", files={"file": ("latin.txt", b"caf\xe9")}).status_code == 415


def test_real_tesseract_reads_rendered_text(tmp_path, monkeypatch):
    from PIL import ImageDraw, ImageFont
    from app.main import tesseract_path
    if not tesseract_path():
        pytest.skip("Tesseract is not installed")
    monkeypatch.setenv("OCR_ENGINE", "tesseract")
    image = Image.new("RGB", (900, 160), "white")
    ImageDraw.Draw(image).text((30, 50), "Total due: $365.50", fill="black", font=ImageFont.load_default(size=48))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    r = client(tmp_path).post("/api/documents", files={"file": ("receipt.png", buffer.getvalue())})
    assert r.status_code == 200, r.text
    assert "365.50" in r.json()["text"]


def test_unknown_ocr_engine_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("OCR_ENGINE", "nope")
    assert client(tmp_path).post("/api/documents", files={"file": ("a.png", png())}).status_code == 500


FORM_TEXT = """EMPLOYEE INFORMATION FORM (SAMPLE)
Company: Buckeye Office Supplies
Full name: Maria Lopez
Employee ID: EMP-20481
Social Security Number: 987-65-4320
Date of birth: 04/12/1990
Home address: 1458 Oak Avenue, Apt 3B

Columbus, OH 43206
Phone: (614) 555-0199
Email: maria.lopez@example.com
Start date: March 2, 2026
Annual salary: $48,500.00
Cashier: Dana
1 x Blueberry Muffin $3.25
Invoice #: INV-2026-118
"""


def test_extract_selected_details(tmp_path):
    from app import extract
    c = client(tmp_path, ocr_fn=lambda data: FORM_TEXT)
    doc = c.post("/api/documents", files={"file": ("form.png", png())}).json()
    fields = [f["key"] for f in c.get("/api/fields").json()["fields"]]
    assert {"emails", "phones", "names", "addresses", "ssns", "numbers"} <= set(fields)
    r = c.post("/api/extract", json={"document_id": doc["id"], "fields": ["ssns", "emails"]})
    assert r.status_code == 200
    results = r.json()["results"]
    assert list(results) == ["ssns", "emails"]  # Only what was asked for, in that order.
    assert results["ssns"]["values"] == ["987-65-4320"]
    assert results["emails"]["values"] == ["maria.lopez@example.com"]
    found = extract.extract(FORM_TEXT, list(extract.FIELDS))
    assert found["phones"] == ["(614) 555-0199"]
    assert found["amounts"] == ["$48,500.00", "$3.25"]
    assert found["dates"] == ["04/12/1990", "March 2, 2026"]
    assert {"EMP-20481", "INV-2026-118"} <= set(found["references"])
    assert found["addresses"] == ["1458 Oak Avenue, Apt 3B, Columbus, OH 43206"]
    assert "48,500.00" in found["numbers"]
    assert {"Maria Lopez", "Dana"} <= set(found["names"])
    assert "Blueberry Muffin" not in found["names"]
    assert "Buckeye Office Supplies" in found["organizations"]


def test_ssn_rules():
    from app.extract import ssns
    assert ssns("SSN: 123-45-6789") == ["123-45-6789"]
    assert ssns("SSN: 123456789") == ["123-45-6789"]  # Unformatted, but labeled.
    assert ssns("Order 123456789") == []  # Unlabeled 9 digits could be anything.
    assert ssns("000-12-3456 666-12-3456 123-00-4567 123-45-0000") == []  # Never-issued patterns.
    assert ssns("Phone 614-555-0123") == []


def test_extract_rejects_bad_requests(tmp_path):
    c = client(tmp_path)
    doc = c.post("/api/demo").json()
    assert c.post("/api/extract", json={"document_id": doc["id"], "fields": []}).status_code == 422
    assert c.post("/api/extract", json={"document_id": doc["id"], "fields": ["passwords"]}).status_code == 422
    assert c.post("/api/extract", json={"document_id": "missing", "fields": ["emails"]}).status_code == 404


def test_missing_document_and_blank_question(tmp_path):
    c = client(tmp_path)
    assert c.get("/api/documents/missing").status_code == 404
    assert c.post("/api/ask", json={"document_id": "missing", "question": " "}).status_code == 422
    assert c.get("/").status_code == 200
    assert c.get("/api/health").json()["status"] == "ok"


def test_retrieval_and_cleaning():
    assert clean_text("  a   b\n c\x00 ") == "a b\nc"
    # Long enough for more than 8 chunks, so the needle is only found if ranking works.
    text = "ordinary " * 2000 + "UNIQUE_NEEDLE contract amount $900"
    assert len(select_context(text, "x", summary=True)) > 8
    assert any("UNIQUE_NEEDLE" in part for _, part in select_context(text, "Where is the UNIQUE_NEEDLE?"))
    with pytest.raises(HTTPException) as error:
        select_context("x" * 70001, "", summary=True)
    assert error.value.status_code == 422


def test_gemini_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        generate("Total: $20", "total?")
    assert error.value.status_code == 503


def test_gemini_evidence_validation(monkeypatch):
    genai = pytest.importorskip("google.genai")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    payload = {"answer": "Twenty dollars", "evidence": [{"chunk_id": 0, "quote": "Total: $20"}]}
    class FakeClient:
        def __init__(self, **kwargs):
            self.models = self
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=json.dumps(payload))
    monkeypatch.setattr(genai, "Client", FakeClient)
    assert generate("Total: $20", "total?")["answer"] == "Twenty dollars"
    unverified = {"answer": "I could not verify an answer in the extracted text.", "evidence": []}
    payload["evidence"][0]["quote"] = "Total: $999"
    assert generate("Total: $20", "total?") == unverified
    # One fabricated citation discredits the answer even when another citation is real.
    payload["evidence"] = [{"chunk_id": 0, "quote": "Total: $20"}, {"chunk_id": 999, "quote": "fake"}]
    assert generate("Total: $20", "total?") == unverified
