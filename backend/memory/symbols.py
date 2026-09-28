"""
Domain-specific symbol and abbreviation recognition.
Includes medical, engineering, education, biology, business, local business, and code.
"""

SYMBOLS = {
    "medical": {
        "BP": "Blood Pressure",
        "HR": "Heart Rate",
        "Rx": "Prescription",
        "CBC": "Complete Blood Count",
        "MRI": "Magnetic Resonance Imaging",
        "CT": "Computed Tomography",
        "CPR": "Cardiopulmonary Resuscitation",
        "ECG": "Electrocardiogram",
        "EKG": "Electrocardiogram",
        "IV": "Intravenous",
        "OTC": "Over The Counter",
        "GERD": "Gastroesophageal Reflux Disease",
        "COPD": "Chronic Obstructive Pulmonary Disease"
    },
    "engineering": {
        "CAD": "Computer-Aided Design",
        "CAM": "Computer-Aided Manufacturing",
        "FEA": "Finite Element Analysis",
        "HVAC": "Heating, Ventilation, and Air Conditioning",
        "PCB": "Printed Circuit Board",
        "CPU": "Central Processing Unit",
        "GPU": "Graphics Processing Unit",
        "RAM": "Random Access Memory",
        "USB": "Universal Serial Bus",
        "AC": "Alternating Current",
        "DC": "Direct Current",
        "MPa": "Megapascal",
        "rpm": "Revolutions Per Minute"
    },
    "education": {
        "GPA": "Grade Point Average",
        "SAT": "Scholastic Assessment Test",
        "ACT": "American College Testing",
        "STEM": "Science, Technology, Engineering, and Mathematics",
        "K-12": "Kindergarten through 12th Grade",
        "PhD": "Doctor of Philosophy",
        "MBA": "Master of Business Administration",
        "GED": "General Educational Development",
        "IQ": "Intelligence Quotient",
        "LMS": "Learning Management System",
        "MOOC": "Massive Open Online Course"
    },
    "biology": {
        "DNA": "Deoxyribonucleic Acid",
        "RNA": "Ribonucleic Acid",
        "ATP": "Adenosine Triphosphate",
        "ADP": "Adenosine Diphosphate",
        "PCR": "Polymerase Chain Reaction",
        "MRI": "Magnetic Resonance Imaging",
        "CT": "Computed Tomography",
        "ECG": "Electrocardiogram",
        "CNS": "Central Nervous System",
        "PNS": "Peripheral Nervous System",
        "AIDS": "Acquired Immunodeficiency Syndrome",
        "HIV": "Human Immunodeficiency Virus"
    },
    "business": {
        "CEO": "Chief Executive Officer",
        "CFO": "Chief Financial Officer",
        "ROI": "Return On Investment",
        "KPI": "Key Performance Indicator",
        "B2B": "Business To Business",
        "B2C": "Business To Consumer",
        "ERP": "Enterprise Resource Planning",
        "CRM": "Customer Relationship Management",
        "IPO": "Initial Public Offering",
        "SME": "Small and Medium Enterprise",
        "VAT": "Value Added Tax",
        "FX": "Foreign Exchange"
    },
    "local_business": {
        "POS": "Point Of Sale",
        "QR": "Quick Response",
        "USSD": "Unstructured Supplementary Service Data",
        "NIN": "National Identification Number",
        "BVN": "Bank Verification Number",
        "KYC": "Know Your Customer",
        "TIN": "Taxpayer Identification Number",
        "CAC": "Corporate Affairs Commission",
        "NGO": "Non-Governmental Organization",
        "MSME": "Micro, Small, and Medium Enterprises"
    },
    "code": {
        # Common operators and symbols
        "=>": "Arrow function (JS)",
        "==": "Equality operator",
        "===": "Strict equality operator",
        "!=": "Inequality operator",
        "!==": "Strict inequality operator",
        "+=": "Addition assignment",
        "-=": "Subtraction assignment",
        "*=": "Multiplication assignment",
        "/=": "Division assignment",
        "%": "Modulo operator",
        "&&": "Logical AND",
        "||": "Logical OR",
        "!": "Logical NOT",
        "&": "Bitwise AND",
        "|": "Bitwise OR",
        "^": "Bitwise XOR",
        "~": "Bitwise NOT",
        "<<": "Left shift",
        ">>": "Right shift",
        ">>>": "Unsigned right shift",
        "?": "Ternary conditional",
        "??": "Nullish coalescing",
        "**": "Exponentiation",
        "...": "Spread/rest operator",
        "#": "Preprocessor directive / comment",
        "//": "Single-line comment",
        "/*": "Multi-line comment start",
        "*/": "Multi-line comment end",
        "<!--": "HTML comment start",
        "-->": "HTML comment end",
        "<=": "Less than or equal",
        ">=": "Greater than or equal",
        "->": "Arrow (C/C++)",
        "::": "Scope resolution (C++/PHP)",
        ".": "Dot / member access",
        "`": "Template literal (JS)",
        "$": "Variable prefix (PHP/Bash)",
        "@": "Decorator (Python)",
        ";": "Statement terminator",
        ",": "Comma separator",
        ":": "Colon (key-value, type declaration)",
        "()": "Parentheses (function call, grouping)",
        "[]": "Brackets (array indexing)",
        "{}": "Braces (block, object, set)",
        "<>": "Angle brackets (templates, generics)",
        "|>": "Pipe operator (Elixir, F#)"
    }
}

def recognize_symbols(text: str, domain: str = "general") -> list:
    found = []
    domain_symbols = SYMBOLS.get(domain, {})
    for sym, meaning in domain_symbols.items():
        if sym.lower() in text.lower():
            found.append((sym, meaning))
    return found

def enrich_query_with_symbols(query: str, domain: str) -> str:
    symbols_found = recognize_symbols(query, domain)
    if not symbols_found:
        return query
    enrich = "Recognized symbols:\n"
    for sym, meaning in symbols_found:
        enrich += f"- {sym}: {meaning}\n"
    return f"{query}\n\n{enrich}"