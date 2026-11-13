"""Pick-and-choose detail extraction from document text.

Patterns (regular expressions) handle structured details such as emails, phone numbers, SSNs and
dates. People and organization names use spaCy's statistical named-entity model when it is
installed, plus label-based rules ("Name:", "Cashier:" ...). Everything runs locally; nothing
is sent to an external service. Results are candidates to review, not guaranteed-complete.
"""
import re
from functools import lru_cache

MONTHS = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|"
          r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?")
STREET_TYPES = (r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl|"
                r"Parkway|Pkwy|Highway|Hwy|Circle|Cir|Terrace|Ter|Trail|Trl|Square|Sq)\.?")
STATES = ("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM "
          "NY NC ND OH OK OR PA PR RI SC SD TN TX UT VT VA WA WV WI WY").split()

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<![\w-])(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?![\w-])")
AMOUNT = re.compile(r"(?:[$€£]\s?\d[\d,]*(?:\.\d{1,2})?|\b\d[\d,]*\.\d{2}\s?(?:USD|EUR|GBP)\b)")
# International amounts: "10 760 000", "18 877,18", "1.800,50", followed or preceded by a currency.
SPACE = "[   ]"  # Normal, no-break and narrow no-break spaces (French thousands separators).
CURRENCY = (r"USD|EUR|GBP|XOF|XAF|F\s?CFA|francs?\s+CFA|CFA|GNF|NGN|GHS|CAD|CHF|MAD|"
            r"dollars?(?:\s+US)?|euros?")
CURRENCY_WORD = re.compile(rf"(?<![A-Za-z])(?:{CURRENCY})(?![A-Za-z])", re.I)
MONEY_NUMBER = rf"\d{{1,3}}(?:(?:{SPACE}|[.,'])\d{{3}})+(?:[.,]\d{{1,2}})?|\d+(?:[.,]\d{{1,2}})?"
# Never start inside a longer number: in "28 800 5 760 000" a match may not begin at "5 760 000".
NUMBER_START = rf"(?<![\d.,])(?<![\d.,]{SPACE})"
TAGGED_AMOUNT = re.compile(
    rf"{NUMBER_START}(?P<num>{MONEY_NUMBER})(?!\d)\)?{SPACE}*(?P<cur>{CURRENCY})(?![A-Za-z])"
    rf"|(?<![A-Za-z])(?P<cur2>{CURRENCY}){SPACE}*(?P<num2>{MONEY_NUMBER})(?!\d)", re.I)
NUMERIC_CELL = re.compile(rf"\(?(?:{MONEY_NUMBER})\)?")
UNTAGGED_NUMBER = re.compile(rf"{NUMBER_START}(?:{MONEY_NUMBER})(?!\d)")
TOTAL_LABEL = re.compile(r"\b(?:grand[ -]total|sous[ -]total|sub[ -]?total|total|montant|amount|balance|solde|"
                         r"net [àa] payer|tva|vat|tax)\b", re.I)
NUMBER = re.compile(r"(?<![\w.,-])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\w,])|(?<![\w.,-])-?\d+(?:\.\d+)?%?(?![\w,])")
SSN = re.compile(r"(?<![\d-])(?!000|666)\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?![\d-])")
SSN_LABELED = re.compile(r"(?:SSN|Social Security(?: Number| No\.?)?)\s*[:#]?\s*(\d{3}[ -]?\d{2}[ -]?\d{4})(?!\d)", re.I)
REFERENCE = re.compile(
    r"\b(?:invoice|receipt|order|account|acct|po|purchase order|reference|ref|transaction|customer|member|policy|"
    r"case|ticket|tracking|confirmation)\s*(?:number|no\.?|num|#|id)?\s*[:#]\s*([A-Z0-9][A-Z0-9-]{2,})", re.I)
CODE_ID = re.compile(r"\b[A-Z]{2,5}-\d{2,}(?:-\d+)*\b")
DATE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})|\d{4}-\d{2}-\d{2}|"
    rf"{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}|\d{{1,2}}\s+{MONTHS},?\s+\d{{4}})\b", re.I)
STREET_LINE = re.compile(
    rf"\b(?:\d{{1,6}}[A-Z]?\s+(?:[NSEW]\.?\s+)?(?:[A-Z0-9][\w'.-]*\s+){{0,4}}{STREET_TYPES}"
    r"(?:\s*,?\s*(?:Suite|Ste\.?|Apt\.?|Unit|#)\s*[\w-]+)?|P\.?\s?O\.?\s+Box\s+\d+)\b", re.I)
STREET_NAME = re.compile(rf"\b{STREET_TYPES}$", re.I)  # "Oak Avenue" is a street, not an organization.
CITY_LINE = re.compile(rf"\b[A-Z][A-Za-z .'-]+,\s*(?:{'|'.join(STATES)})\.?\s+\d{{5}}(?:-\d{{4}})?\b")
# Labels match in any case; the name itself must be capitalized.
NAME_LABEL = re.compile(
    r"\b(?i:name|full name|customer name|employee|patient|cashier|server|attn|attention|contact|"
    r"signed by|prepared by|approved by|account holder|insured|applicant)\s*[:\-]\s*"
    r"([A-Z][a-z'’.-]+(?:[ \t]+[A-Z][a-z'’.-]*){0,3})")
ORG_SUFFIX = re.compile(
    r"\b((?:[A-Z][\w&'’.-]*[ \t]+){0,4}(?:Inc|LLC|L\.L\.C|Ltd|Corp|Corporation|Company|Co|Group|Studio|Studios|"
    r"Market|Supplies|Services|Bank|University|Hospital|Clinic|Coffee|Associates|Partners)\b\.?)")
# Words that spaCy sometimes tags as people on forms and receipts.
NOT_NAMES = {"bill", "total", "subtotal", "tax", "invoice", "receipt", "payment", "due", "amount", "qty",
             "description", "date", "thank", "paid", "visa", "cash", "change", "street", "suite", "attn",
             "cashier", "customer", "sample", "questions", "logo", "web", "unit"}
# Form labels and table headers that spaCy sometimes tags as organizations.
NOT_ORGS = {"description", "qty", "quantity", "unit", "price", "invoice", "total", "subtotal", "amount", "number",
            "social", "security", "date", "employee", "employer", "bill", "receipt", "sample", "tax", "id"}
CONNECTORS = {"&", "and", "of", "the", "for", "de"}


def _unique(values):
    seen, out = set(), []
    for value in values:
        value = re.sub(r"\s+", " ", value).strip(" ,;:")
        if value and value.lower() not in seen:
            seen.add(value.lower())
            out.append(value)
    return out


@lru_cache(maxsize=1)
def _nlp():
    try:
        import spacy
        return spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        return None


def _entities(text, labels, skip_priced_lines=False):
    nlp = _nlp()
    if nlp is None:
        return []
    # Line by line so an entity never joins words from separate lines of a form or receipt.
    lines = [line for line in text.splitlines() if line.strip()]
    if skip_priced_lines:
        # Item lines ("1 x Blueberry Muffin $3.25") are products, not people.
        lines = [line for line in lines if not AMOUNT.search(line)]
    found = []
    for doc in nlp.pipe(lines):
        found += [ent.text for ent in doc.ents if ent.label_ in labels]
    return found


def _next_text_line(lines, i, reach=2):
    for line in lines[i + 1:i + 1 + reach]:
        if line.strip():
            return line
    return ""


def emails(text):
    return _unique(EMAIL.findall(text))


def phones(text):
    return _unique(PHONE.findall(text))


def _currency_code(raw):
    word = " ".join(raw.upper().split())
    if "CFA" in word:
        return "FCFA"
    if word.startswith("DOLLAR"):
        return "USD"
    if word.startswith("EURO"):
        return "EUR"
    return word


def _money(number, currency=None):
    number = re.sub(SPACE, " ", number.strip("()"))
    return f"{number} {_currency_code(currency)}" if currency else number


def _money_shaped(number):
    # Without a currency, only grouped or two-decimal numbers count: "10 760 000", "18 877,18", not "300".
    return bool(re.search(rf"\d(?:{SPACE}|[.,'])\d{{3}}|[.,]\d{{2}}\)?$", number))


def _tagged_amounts(text):
    return [_money(m.group("num") or m.group("num2"), m.group("cur") or m.group("cur2"))
            for m in TAGGED_AMOUNT.finditer(text)]


def _table_amounts(text):
    """Amounts in table rows whose cells are separated by " | " (PDF and Word tables).

    A header cell naming a currency, such as "Montant (FCFA)", marks its column as money. Columns are
    matched from the right, because amount columns are the rightmost ones and are always filled in,
    while the description column on the left may sit on a separate line.
    """
    found, columns = [], {}  # columns: position counted from the right -> currency code
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 2:
            continue
        numeric = [bool(NUMERIC_CELL.fullmatch(cell)) for cell in cells]
        if not any(numeric):
            currencies = {len(cells) - i: _currency_code(m.group(0))
                          for i, cell in enumerate(cells) if (m := CURRENCY_WORD.search(cell))}
            if currencies:
                columns = currencies
            continue
        labels = [i for i, cell in enumerate(cells) if not numeric[i] and TOTAL_LABEL.search(cell)]
        # In "Total | 300 | TOTAL | 10 760 000 | 18 877,18" only the cells after the last label are amounts.
        for i in range(labels[-1] + 1 if labels else 0, len(cells)):
            if not numeric[i]:
                continue
            currency = columns.get(len(cells) - i)
            if currency:
                found.append(_money(cells[i], currency))
            elif labels and _money_shaped(cells[i]):
                found.append(_money(cells[i]))
        if labels:
            columns = {}  # A total row ends the table.
    return found


def _labeled_amounts(text):
    """Plain lines such as "TOTAL 10 760 000" (for example from OCR): the first amount after the label."""
    found = []
    for line in text.splitlines():
        labels = list(TOTAL_LABEL.finditer(line))
        if "|" in line or not labels or AMOUNT.search(line) or TAGGED_AMOUNT.search(line):
            continue
        number = UNTAGGED_NUMBER.search(line, labels[-1].end())
        if number and _money_shaped(number.group(0)):
            found.append(_money(number.group(0)))
    return found


def amounts(text):
    return _unique(AMOUNT.findall(text) + _tagged_amounts(text) + _table_amounts(text) + _labeled_amounts(text))


def numbers(text):
    return _unique(NUMBER.findall(text))


def references(text):
    return _unique(REFERENCE.findall(text) + CODE_ID.findall(text))


def dates(text):
    return _unique(DATE.findall(text))


def ssns(text):
    found = SSN.findall(text)
    for raw in SSN_LABELED.findall(text):
        digits = re.sub(r"\D", "", raw)
        if digits[:3] not in {"000", "666"} and digits[3:5] != "00" and digits[5:] != "0000":
            found.append(f"{digits[:3]}-{digits[3:5]}-{digits[5:]}")
    return _unique(found)


def addresses(text):
    lines = text.splitlines()
    found = []
    for i, line in enumerate(lines):
        street = STREET_LINE.search(line)
        if not street:
            continue
        # Keep "street, City, ST 12345" on one line, or join the next line when it is "City, ST 12345".
        city = CITY_LINE.search(line[street.end():]) or CITY_LINE.search(_next_text_line(lines, i))
        if city:
            found.append(f"{street.group(0)}, {city.group(0)}")
        else:
            found.append(street.group(0))
    return _unique(found)


def _looks_like_person(value, labeled):
    words = value.replace("'s", "").split()
    # A single word counts only when a label such as "Cashier:" vouches for it.
    return (1 <= len(words) <= 4 and not any(ch.isdigit() for ch in value)
            and all(w[0].isupper() for w in words) and not any(w.lower().strip(".:") in NOT_NAMES for w in words)
            and (len(words) >= 2 or value in labeled))


def names(text):
    labeled = {m.strip() for m in NAME_LABEL.findall(text)}
    candidates = sorted(labeled) + [v.strip() for v in _entities(text, {"PERSON"}, skip_priced_lines=True)]
    return _unique(v for v in candidates if _looks_like_person(v, labeled))


def _looks_like_org(value, from_suffix):
    words = value.split()
    if any(ch.isdigit() for ch in value) or "@" in value or " - " in value or len(value) <= 2:
        return False
    if any(w.lower().strip(".:,") in NOT_ORGS for w in words) or STREET_NAME.search(value):
        return False
    if len(words) < 2:  # A lone "Company" or "Inc" is a label, not a name.
        return False
    # spaCy's guesses must look like a proper name: several capitalized words, e.g. "Northwind Web Studio".
    return from_suffix or (len(words) >= 2 and all(w[0].isupper() or w.lower() in CONNECTORS for w in words))


def organizations(text):
    by_suffix = [m.strip() for m in ORG_SUFFIX.findall(text)]
    guessed = [v.strip() for v in _entities(text, {"ORG", "FAC"}, skip_priced_lines=True)]
    return _unique([v for v in by_suffix if _looks_like_org(v, True)] +
                   [v for v in guessed if _looks_like_org(v, False)])


FIELDS = {
    "emails": ("Email addresses", emails),
    "phones": ("Phone numbers", phones),
    "amounts": ("Money amounts", amounts),
    "dates": ("Dates", dates),
    "references": ("Invoice / order / account numbers", references),
    "numbers": ("All numbers", numbers),
    "names": ("People's names", names),
    "organizations": ("Business / organization names", organizations),
    "addresses": ("Street addresses", addresses),
    "ssns": ("Social Security numbers", ssns),
}


def extract(text, keys):
    return {key: FIELDS[key][1](text) for key in keys}


def ner_available():
    return _nlp() is not None
