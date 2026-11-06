"""Generate fictional sample receipts and invoices for trying the OCR Search Engine.

All businesses, people, and numbers are made up. Every document is marked SAMPLE.
Run from the ocr_search folder:  .venv\\Scripts\\python.exe samples\\generate_samples.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent
FONTS = Path(r"C:\Windows\Fonts")

# ---------------------------------------------------------------- data

RECEIPT = {
    "store": "MAPLE STREET COFFEE",
    "address": ["418 Maple Street", "Columbus, OH 43215", "(614) 555-0142"],
    "date": "11/06/2026  08:42 AM",
    "number": "Receipt #: 20261106-0057",
    "cashier": "Cashier: Dana",
    "items": [("Latte (16 oz)", 2, 4.75), ("Blueberry Muffin", 1, 3.25), ("Bagel w/ Cream Cheese", 1, 3.95)],
    "tax_rate": 0.0725,
    "payment": "VISA **** 4242",
    "footer": ["Thank you for visiting!", "Questions? hello@maplecoffee.example.com"],
}

INVOICE = {
    "company": "Northwind Web Studio",
    "company_lines": ["220 High Street, Suite 4", "Columbus, OH 43215", "billing@northwind.example.com"],
    "number": "INV-2026-118",
    "date": "November 6, 2026",
    "due": "December 6, 2026",
    "bill_to": ["Isiaka's Demo Company", "75 Broad Street", "Columbus, OH 43215"],
    "items": [("Website design (5 pages)", 1, 1200.00), ("Web hosting - 12 months", 12, 15.00),
              ("Logo revisions (hours)", 3, 45.00)],
    "tax_rate": 0.05,
    "terms": "Payment terms: Net 30. Please include the invoice number with your payment.",
}

OFFICE_INVOICE = {
    "company": "Buckeye Office Supplies",
    "company_lines": ["1290 Industrial Parkway", "Dayton, OH 45402", "orders@buckeyeoffice.example.com"],
    "number": "INV-2026-121",
    "date": "November 3, 2026",
    "due": "November 17, 2026",
    "bill_to": ["Isiaka's Demo Company", "75 Broad Street", "Columbus, OH 43215"],
    "items": [("Copy paper (ream)", 10, 6.50), ("Toner cartridge", 2, 89.99), ("LED desk lamp", 1, 34.50)],
    "tax_rate": 0.0725,
    "terms": "Payment terms: Net 14.",
}

GROCERY = {
    "store": "GREEN VALLEY MARKET",
    "items": [("Bananas (2.1 lb)", 1, 1.26), ("Whole milk 1 gal", 1, 3.89), ("Brown eggs dozen", 1, 4.29),
              ("Sourdough bread", 1, 5.49), ("Apples Gala 3 lb", 1, 4.99)],
    "tax_rate": 0.0,
}


# 987-65-4320 is in the range the Social Security Administration reserved for advertising/examples.
EMPLOYEE_FORM = [
    ("title", "EMPLOYEE INFORMATION FORM"),
    ("note", "SAMPLE - fictional person and data"),
    ("head", "Employer"),
    ("row", "Company: Buckeye Office Supplies"),
    ("row", "1290 Industrial Parkway, Dayton, OH 45402"),
    ("head", "Employee"),
    ("row", "Full name: Maria Lopez"),
    ("row", "Employee ID: EMP-20481"),
    ("row", "Social Security Number: 987-65-4320"),
    ("row", "Date of birth: 04/12/1990"),
    ("row", "Home address: 1458 Oak Avenue, Apt 3B"),
    ("row", "Columbus, OH 43206"),
    ("row", "Phone: (614) 555-0199"),
    ("row", "Email: maria.lopez@example.com"),
    ("head", "Employment"),
    ("row", "Start date: March 2, 2026"),
    ("row", "Position: Inventory Coordinator"),
    ("row", "Annual salary: $48,500.00"),
    ("row", "Manager: Angela Brooks"),
    ("head", "Emergency contact"),
    ("row", "Contact: James Lopez (brother)"),
    ("row", "Phone: 614-555-0123"),
]


def draw_form(rows):
    width, height = 1700, 2000
    image = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(image)
    fonts = {"title": font("arialbd.ttf", 60), "note": font("arialbd.ttf", 32), "head": font("arialbd.ttf", 40),
             "row": font("arial.ttf", 36)}
    y = 110
    for kind, text in rows:
        if kind == "head":
            y += 40
            d.rectangle((110, y - 10, width - 110, y + 58), fill=(225, 225, 225))
        d.text((130, y), text, fill=(90, 90, 90) if kind == "note" else "black", font=fonts[kind])
        y += {"title": 95, "note": 70, "head": 85, "row": 58}[kind]
    return image.crop((0, 0, width, y + 100))


def money(value):
    return f"${value:,.2f}"


def totals(doc):
    subtotal = round(sum(qty * price for _, qty, price in doc["items"]), 2)
    tax = round(subtotal * doc["tax_rate"] + 1e-9, 2)
    return subtotal, tax, round(subtotal + tax, 2)


def font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default(size=size)


# ---------------------------------------------------------------- images

def draw_receipt(doc):
    width, line = 760, 46
    image = Image.new("RGB", (width, 1500), "white")
    d = ImageDraw.Draw(image)
    mono, bold = font("consola.ttf", 30), font("consolab.ttf", 40)
    y = 50

    def center(text, f=mono):
        nonlocal y
        d.text(((width - d.textlength(text, font=f)) / 2, y), text, fill="black", font=f)
        y += line + (10 if f is bold else 0)

    def row(left, right=""):
        nonlocal y
        d.text((50, y), left, fill="black", font=mono)
        if right:
            d.text((width - 50 - d.textlength(right, font=mono), y), right, fill="black", font=mono)
        y += line

    def rule():
        nonlocal y
        d.line((50, y + 18, width - 50, y + 18), fill="black", width=2)
        y += line

    center("*** SAMPLE RECEIPT ***")
    center(doc["store"], bold)
    for text in doc["address"]:
        center(text)
    rule()
    row(doc["date"])
    row(doc["number"])
    row(doc["cashier"])
    rule()
    for name, qty, price in doc["items"]:
        row(f"{qty} x {name}", money(qty * price))
    rule()
    subtotal, tax, total = totals(doc)
    row("Subtotal", money(subtotal))
    row(f"Sales tax ({doc['tax_rate'] * 100:.2f}%)", money(tax))
    row("TOTAL", money(total))
    row(f"Paid: {doc['payment']}", money(total))
    rule()
    for text in doc["footer"]:
        center(text)
    return image.crop((0, 0, width, y + 40))


def draw_invoice(doc):
    width, height = 1700, 2200  # US Letter at 200 DPI
    image = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(image)
    regular, bold = font("arial.ttf", 34), font("arialbd.ttf", 34)
    big, title = font("arialbd.ttf", 56), font("arialbd.ttf", 84)
    left, right = 130, width - 130

    def rtext(x, y, text, f=regular):
        d.text((x - d.textlength(text, font=f), y), text, fill="black", font=f)

    d.text((left, 120), doc["company"], fill="black", font=big)
    for i, text in enumerate(doc["company_lines"]):
        d.text((left, 205 + i * 46), text, fill="black", font=regular)
    rtext(right, 110, "INVOICE", title)
    rtext(right, 215, "SAMPLE - fictional data", bold)

    y = 420
    d.text((left, y), "Bill to:", fill="black", font=bold)
    for i, text in enumerate(doc["bill_to"]):
        d.text((left, y + 50 + i * 46), text, fill="black", font=regular)
    for i, (label, value) in enumerate([("Invoice number:", doc["number"]), ("Invoice date:", doc["date"]),
                                        ("Payment due:", doc["due"])]):
        d.text((1000, y + i * 50), label, fill="black", font=bold)
        rtext(right, y + i * 50, value)

    y = 720
    columns = [(left, "Description"), (1050, "Qty"), (1300, "Unit price"), (right, "Amount")]
    d.rectangle((left - 20, y - 15, right + 20, y + 55), fill=(225, 225, 225))
    d.text((left, y), "Description", fill="black", font=bold)
    for x, label in columns[1:]:
        rtext(x, y, label, bold)
    y += 90
    for name, qty, price in doc["items"]:
        d.text((left, y), name, fill="black", font=regular)
        rtext(1050, y, str(qty))
        rtext(1300, y, money(price))
        rtext(right, y, money(qty * price))
        y += 62
    d.line((left - 20, y, right + 20, y), fill="black", width=3)

    subtotal, tax, total = totals(doc)
    y += 30
    for label, value, f in [("Subtotal:", money(subtotal), regular),
                            (f"Tax ({doc['tax_rate'] * 100:g}%):", money(tax), regular),
                            ("Total due:", money(total), bold)]:
        rtext(1300, y, label, f)
        rtext(right, y, value, f)
        y += 58
    d.text((left, y + 80), doc["terms"], fill="black", font=regular)
    d.text((left, height - 160), "This is a fictional sample document for testing. Not a real invoice.",
           fill=(90, 90, 90), font=regular)
    return image


def as_scan(image):
    # Mild rotation, gray paper, and blur so it resembles a scanned page.
    page = image.convert("L").point(lambda v: 40 + v * 0.8)
    page = page.rotate(0.7, resample=Image.BICUBIC, expand=True, fillcolor=244)
    return page.filter(ImageFilter.GaussianBlur(0.8))


# ---------------------------------------------------------------- text-layer PDF

def pdf_escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_pdf(path, items):
    """items: (x, y, size, bold, text, align) in PDF points; y measured from the top of a Letter page."""
    ops = []
    for x, y, size, bold, text, align in items:
        if align == "right":  # Approximate Helvetica width so right-aligned columns line up.
            x -= len(text) * size * 0.5
        ops.append(f"BT /{'F2' if bold else 'F1'} {size} Tf {x:.1f} {792 - y:.1f} Td ({pdf_escape(text)}) Tj ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
               b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>",
               b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


def invoice_pdf(path, doc):
    items = [(50, 60, 20, True, doc["company"], "left"), (562, 60, 28, True, "INVOICE", "right"),
             (562, 88, 11, True, "SAMPLE - fictional data", "right")]
    items += [(50, 82 + i * 15, 11, False, t, "left") for i, t in enumerate(doc["company_lines"])]
    items.append((50, 160, 11, True, "Bill to:", "left"))
    items += [(50, 176 + i * 15, 11, False, t, "left") for i, t in enumerate(doc["bill_to"])]
    for i, (label, value) in enumerate([("Invoice number:", doc["number"]), ("Invoice date:", doc["date"]),
                                        ("Payment due:", doc["due"])]):
        items += [(340, 160 + i * 16, 11, True, label, "left"), (562, 160 + i * 16, 11, False, value, "right")]
    y = 260
    items += [(50, y, 11, True, "Description", "left"), (370, y, 11, True, "Qty", "right"),
              (460, y, 11, True, "Unit price", "right"), (562, y, 11, True, "Amount", "right")]
    for name, qty, price in doc["items"]:
        y += 20
        items += [(50, y, 11, False, name, "left"), (370, y, 11, False, str(qty), "right"),
                  (460, y, 11, False, money(price), "right"), (562, y, 11, False, money(qty * price), "right")]
    subtotal, tax, total = totals(doc)
    for label, value, bold in [("Subtotal:", money(subtotal), False),
                               (f"Tax ({doc['tax_rate'] * 100:g}%):", money(tax), False),
                               ("Total due:", money(total), True)]:
        y += 20 if label != "Subtotal:" else 32
        items += [(460, y, 11, bold, label, "right"), (562, y, 11, bold, value, "right")]
    items.append((50, y + 40, 10, False, doc["terms"], "left"))
    items.append((50, 740, 9, False, "This is a fictional sample document for testing. Not a real invoice.", "left"))
    text_pdf(path, items)


# ---------------------------------------------------------------- Word and text

def invoice_docx(path, doc):
    import docx
    from docx.shared import Pt

    document = docx.Document()
    document.add_heading(f"{doc['company']} - INVOICE (SAMPLE)", level=1)
    for text in doc["company_lines"]:
        document.add_paragraph(text)
    document.add_paragraph(f"Invoice number: {doc['number']}")
    document.add_paragraph(f"Invoice date: {doc['date']}")
    document.add_paragraph(f"Payment due: {doc['due']}")
    document.add_paragraph("Bill to: " + ", ".join(doc["bill_to"]))
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for cell, label in zip(table.rows[0].cells, ["Description", "Qty", "Unit price", "Amount"]):
        cell.text = label
    for name, qty, price in doc["items"]:
        for cell, value in zip(table.add_row().cells, [name, str(qty), money(price), money(qty * price)]):
            cell.text = value
    subtotal, tax, total = totals(doc)
    document.add_paragraph(f"Subtotal: {money(subtotal)}")
    document.add_paragraph(f"Tax ({doc['tax_rate'] * 100:g}%): {money(tax)}")
    document.add_paragraph().add_run(f"Total due: {money(total)}").bold = True
    document.add_paragraph(doc["terms"])
    note = document.add_paragraph().add_run("This is a fictional sample document for testing. Not a real invoice.")
    note.font.size = Pt(9)
    document.save(path)


def grocery_txt(path, doc):
    subtotal, tax, total = totals(doc)
    lines = ["*** SAMPLE RECEIPT - fictional data ***", doc["store"], "560 Valley Road, Westerville, OH 43081",
             "Date: 11/05/2026 6:15 PM   Register 3", "-" * 40]
    lines += [f"{name:<30}{money(qty * price):>10}" for name, qty, price in doc["items"]]
    lines += ["-" * 40, f"{'Subtotal':<30}{money(subtotal):>10}", f"{'Tax (food exempt)':<30}{money(tax):>10}",
              f"{'TOTAL':<30}{money(total):>10}", f"{'Paid: Cash':<30}{money(20):>10}",
              f"{'Change':<30}{money(20 - total):>10}", "-" * 40, "Items sold: 5",
              "Rewards questions: rewards@greenvalley.example.com"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    draw_receipt(RECEIPT).save(OUT / "receipt.png")
    invoice = draw_invoice(INVOICE)
    invoice.save(OUT / "invoice.png")
    as_scan(invoice).save(OUT / "invoice_scanned.pdf", resolution=200)
    invoice_pdf(OUT / "invoice.pdf", INVOICE)
    invoice_docx(OUT / "invoice_office_supplies.docx", OFFICE_INVOICE)
    grocery_txt(OUT / "receipt_grocery.txt", GROCERY)
    draw_form(EMPLOYEE_FORM).save(OUT / "employee_form.png")
    for name, doc in [("receipt.png", RECEIPT), ("invoice.*", INVOICE), ("office docx", OFFICE_INVOICE),
                      ("grocery txt", GROCERY)]:
        print(f"{name:<12} subtotal/tax/total:", *map(money, totals(doc)))
