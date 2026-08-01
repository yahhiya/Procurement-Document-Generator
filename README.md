# SOLGulf Procurement Document Generator
An automated procurement document generation system developed for **SOLGulf** to streamline the creation of procurement documents by extracting information from requirements documents and populating approved Microsoft Word templates.

---

## Project Overview
This application processes a requirements document (`.DOCX` or `.TXT`), extracts the required procurement information, and automatically generates a completed Microsoft Word (`.DOCX`) document using an approved document template.

The first iteration focuses on generating a **Master Services Agreement (MSA)**. However, the architecture has been designed so that additional procurement document templates can be supported in future iterations.

### Workflow
```mermaid
flowchart LR
    A["Requirements Document<br/>(.DOCX / .TXT)"]
    --> B["Information Extraction (LLM)"]
    --> C["Human Review & Validation"]
    --> D["Document Generation"]
    --> E["Generated Procurement Document<br/>(.DOCX)"]
```

---

## Features
- Upload procurement requirements documents (`.DOCX` or `.TXT`)
- Extract key procurement information from structured or unstructured text using an LLM
- Human review step to confirm or correct extracted information before generation
- Map validated information to document placeholders
- Automatically generate Microsoft Word procurement documents
- Download completed documents in `.DOCX` format

---

## Technology Stack
| Component | Technology |
|-----------|------------|
| Programming Language | Python |
| User Interface | Streamlit |
| Document Reading | python-docx |
| Document Generation | docxtpl |
| Information Extraction (LLM) | Google Gemini API |
| Data Validation | pydantic |
| Version Control | Git & GitHub |

---

## Project Structure
```text
SOLGulf-Procurement-Generator/
│
├── app.py
├── requirements.txt
├── .env                  (not committed — holds API key)
├── .gitignore
│
├── templates/
│   └── master_services_agreement.docx
│
├── docs/
│   └── SOLGulf_Procurement_Document_Generation_System.pdf
│
├── generated/
│   └── (output documents)
│
├── assets/
│   └── solgulf_logo.png
│
└── README.md
```

---

## Current Status
This project is currently under active development.

**Completed so far:**
- Development environment set up (Python, Streamlit, Gemini API)
- Architecture design finalised and reviewed with stakeholder

**In progress:**
- Requirements document upload
- LLM-based information extraction
- Human review interface
- Document generation via template

Future iterations will introduce support for additional procurement document templates and further enhancements to the information extraction process.

---

## Planned Improvements
- Support multiple procurement document templates
- Improve information extraction accuracy
- Additional document validation
- Enhanced user interface
- Expanded document generation capabilities

---

## Author
**Yahhiya Khawaja**

Developed as part of an enterprise case study project in collaboration with **SOLGulf**.
