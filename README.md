# Document Logo Placer

A web application that allows you to place your own custom logo on documents (currently pdf only).

## Features

- Drag and drop interface for PDF documents and logo images
- Customizable logo positioning and sizing
- Support for processing single or multiple pages
- Maintains aspect ratio of logos
- Various logo placement options (bottom-right, top-left, center, etc.)

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python logo_placer.py
```

The web interface will open in your default browser. You can then:
1. Upload your PDF document
2. Upload your logo image (PNG with transparent background recommended)
3. Configure logo placement and size
4. Process the document and download the result

## Requirements

- Python 3.8 or higher
- See requirements.txt for Python package dependencies 