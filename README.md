# SOLGulf Contract Generator

An automated procurement contract generation system built for SOLGulf to streamline the creation of Master Services Agreements (MSAs).

## Project Overview
This tool takes dynamic inputs (vendor names, effective dates, scopes of work, and pricing) and automatically injects them into a standardized Word template (`.docx`), generating a finalized, download-ready contract in seconds.

## Tech Stack
* **Python**
* **Streamlit** (User Interface)
* **python-docx** (Document Processing)

## Project Structure
```text
SOLGulf-Contract-Generator/
│
├── app.py
├── requirements.txt
├── templates/
│   └── master_services_agreement.docx
└── assets/
    └── solgulf_logo.png
