# Test Suite
This directory contains automated tests to ensure the API's reliability and data integrity.

### Contents
* **test_api.py**: Tests for the Flask REST endpoints (`/upload` and `/roads`). It validates:
    * Successful data ingestion.
    * Error handling for missing fields.
    * Correct JSON structure of the data output.

### Running Tests
Ensure you have `pytest` installed, then run the following command from the project root:
```bash
pytest tests/test_api.py
