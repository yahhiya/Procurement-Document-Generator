# SOLGulf Procurement Document Generator

An automated procurement document generation system developed for SOLGulf to streamline the creation of procurement documents by reducing manual drafting, improving consistency, and minimising human error.

---

## Project Overview

This application processes a requirements document (.DOCX or .TXT), extracts the required contractual information, and populates an approved Microsoft Word (.docx) template to generate a completed procurement document.

The first iteration focuses on generating a Master Services Agreement (MSA); however, the system has been designed with a flexible architecture that can support additional procurement document templates in future iterations.

The overall workflow is:

Requirements Document (.DOCX / .TXT)

↓

Information Extraction

↓

Document Generation

↓

Completed Microsoft Word Document (.DOCX)

---

## Features

- Upload requirements documents (.DOCX or .TXT)
- Extract key contractual information from uploaded documents
- Populate approved Microsoft Word templates using placeholder tags
- Preserve the original document formatting during generation
- Download the completed procurement document as a Microsoft Word (.docx) file
- Architecture designed to support additional document templates in future iterations

---

## Technology Stack

- **Language:** Python
- **Framework:** Streamlit
- **Libraries:**
  - python-docx (Microsoft Word document processing)

---

## Project Structure

```
SOLGulf-Procurement-Document-Generator/
│
├── app.py
├── requirements.txt
├── templates/
│   └── master_services_agreement.docx
├── assets/
│   └── solgulf_logo.png
└── README.md
```

---

## Current Status

This project is currently under active development as part of an enterprise procurement automation case study in collaboration with SOLGulf.

The current focus is on implementing the core ingestion, information extraction, document generation, and download workflow. Future iterations will extend support to additional procurement document templates while maintaining the same overall architecture.

---

## Author

**Yahhiya Khawaja**
