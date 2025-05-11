import io
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import numpy as np
import streamlit as st
import tempfile
import os

def get_background_color(pdf_path, page_number=0, x=None, y=None, width=None, height=None):
    """
    Sample the background color from a region of the PDF
    
    Parameters:
    - pdf_path: Path to the PDF file
    - page_number: Page number to sample from (0-indexed)
    - x, y, width, height: Region to sample (if None, will use default values)
    
    Returns:
    - (R, G, B) tuple with values from 0 to 1
    """
    # Open the PDF
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    
    # Get page dimensions if not provided
    if x is None or y is None or width is None or height is None:
        # Get page dimensions
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        # Set default sampling area
        x = page_width - 200
        y = 15
        width = 10
        height = 10
    
    # Get a pixmap of the region
    clip_rect = fitz.Rect(x, y, x + width, y + height)
    pix = page.get_pixmap(clip=clip_rect)
    
    # Convert to numpy array to calculate average color
    samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    
    # Calculate average color (excluding alpha channel if present)
    channels = 3 if pix.n == 3 else 3  # Handle both RGB and RGBA
    avg_color = np.mean(samples[:, :, 0:channels], axis=(0, 1)) / 255.0
    
    # Close the document
    doc.close()
    
    # Return RGB values (0-1 scale for reportlab)
    return tuple(avg_color)

def replace_logo_background_on_page(page, page_width, page_height, logo_path, bg_color, logo_config):
    """
    Create PDF content to place logo with background on a single page
    
    Parameters:
    - page: PyPDF2 page object
    - page_width, page_height: Dimensions of the page
    - logo_path: Path to the logo image
    - bg_color: Background color tuple (R, G, B)
    - logo_config: Dict with logo and background configuration
    """
    # Create a rectangle for the logo background
    bg_rect_packet = io.BytesIO()
    bg_rect_canvas = canvas.Canvas(bg_rect_packet, pagesize=(page_width, page_height))
    
    # Load the logo image to get dimensions
    logo = Image.open(logo_path)
    logo_orig_width, logo_orig_height = logo.size
    
    # Get logo dimensions from config
    logo_width = logo_config.get('width', None)
    logo_height = logo_config.get('height', None)
    
    # Calculate logo dimensions maintaining aspect ratio
    if logo_width is None and logo_height is None:
        max_width = logo_config.get('max_width', 150)
        if logo_orig_width > max_width:
            scale_factor = max_width / logo_orig_width
            logo_width = max_width
            logo_height = logo_orig_height * scale_factor
        else:
            logo_width = logo_orig_width
            logo_height = logo_orig_height
    elif logo_height is None and logo_width is not None:
        scale_factor = logo_width / logo_orig_width
        logo_height = logo_orig_height * scale_factor
    elif logo_width is None and logo_height is not None:
        scale_factor = logo_height / logo_orig_height
        logo_width = logo_orig_width * scale_factor
    
    # Get background dimensions and padding
    bg_width = logo_config.get('bg_width', logo_width + 40)  # Default padding of 20 on each side
    bg_height = logo_config.get('bg_height', logo_height + 40)
    padding = logo_config.get('padding', 20)
    
    # Calculate logo position
    position_mode = logo_config.get('position', 'bottom-right')
    
    if position_mode == 'bottom-right':
        x_position = page_width - logo_width - padding
        y_position = padding
    elif position_mode == 'bottom-left':
        x_position = padding
        y_position = padding
    elif position_mode == 'top-right':
        x_position = page_width - logo_width - padding
        y_position = page_height - logo_height - padding
    elif position_mode == 'top-left':
        x_position = padding
        y_position = page_height - logo_height - padding
    elif position_mode == 'center':
        x_position = (page_width - logo_width) / 2
        y_position = (page_height - logo_height) / 2
    elif position_mode == 'custom':
        x_position = logo_config.get('x', page_width - logo_width - padding)
        y_position = logo_config.get('y', padding)
    
    # Calculate background position (centered around logo)
    bg_x = x_position - (bg_width - logo_width) / 2
    bg_y = y_position - (bg_height - logo_height) / 2
    
    # Draw background rectangle
    bg_rect_canvas.setFillColorRGB(bg_color[0], bg_color[1], bg_color[2])
    bg_rect_canvas.rect(bg_x, bg_y, bg_width, bg_height, fill=1, stroke=0)
    bg_rect_canvas.save()
    
    # Create logo PDF
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # Draw the logo
    can.drawImage(logo_path, x_position, y_position, width=logo_width, height=logo_height, mask='auto')
    can.save()
    
    # Merge everything
    bg_rect_packet.seek(0)
    bg_rect_pdf = PdfReader(bg_rect_packet)
    bg_rect_page = bg_rect_pdf.pages[0]
    
    packet.seek(0)
    logo_pdf = PdfReader(packet)
    logo_page = logo_pdf.pages[0]
    
    page.merge_page(bg_rect_page)
    page.merge_page(logo_page)
    
    return page

def process_pdf_with_logo(
    input_pdf_path, 
    output_pdf_path, 
    logo_path, 
    pages='all',
    logo_config=None
):
    """
    Process a PDF file to add a logo with custom background.
    
    Parameters:
    - input_pdf_path: Path to the original PDF file
    - output_pdf_path: Path where to save the modified PDF
    - logo_path: Path to your logo image (PNG with transparent background)
    - pages: 'all' to process all pages, or a list of page numbers (0-indexed)
    - logo_config: Dict with logo and background configuration:
        - width: logo width
        - height: logo height
        - max_width: maximum width if neither width nor height is specified
        - position: one of 'bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'custom'
        - padding: padding from edge of page
        - x: custom x-coordinate (used when position='custom')
        - y: custom y-coordinate (used when position='custom')
        - bg_width: width of the background rectangle
        - bg_height: height of the background rectangle
    """
    if logo_config is None:
        logo_config = {}
    
    # Open the existing PDF
    pdf_reader = PdfReader(input_pdf_path)
    pdf_writer = PdfWriter()
    
    # Sample background color from the first page
    bg_color = get_background_color(input_pdf_path, 0)
    
    # Determine which pages to process
    if pages == 'all':
        pages_to_process = range(len(pdf_reader.pages))
    else:
        pages_to_process = pages
    
    # Process each page
    for i in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[i]
        
        # Get page dimensions
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        
        # If this page should be processed, add the logo
        if i in pages_to_process:
            # For pages other than the first, sample the background color
            if i > 0 and pages == 'all':
                bg_color = get_background_color(input_pdf_path, i)
            
            # Add logo with background
            page = replace_logo_background_on_page(
                page, page_width, page_height, logo_path, bg_color, logo_config
            )
        
        # Add the page to the output PDF
        pdf_writer.add_page(page)
    
    # Write the modified PDF to a file
    with open(output_pdf_path, "wb") as output_file:
        pdf_writer.write(output_file)
    
    print(f"Modified PDF saved to {output_pdf_path}")
    print(f"Processed {len(pages_to_process)} pages")

def main():
    st.set_page_config(
        page_title="Document Logo Placer",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("Document Logo Placer")
    st.write("Add your logo with custom background to PDF documents.")

    st.markdown("---")
    # File upload section
    upload_col1, upload_col2 = st.columns(2)
    with upload_col1:
        st.subheader("Upload PDF Document")
        pdf_file = st.file_uploader("Drag and drop your PDF here", type=['pdf'], key="pdf")
    with upload_col2:
        st.subheader("Upload Logo")
        logo_file = st.file_uploader("Drag and drop your logo here", type=['png', 'jpg', 'jpeg'], key="logo")

    # --- Smart defaults based on logo image ---
    if 'logo_width' not in st.session_state:
        st.session_state.logo_width = 100
    if 'logo_height' not in st.session_state:
        st.session_state.logo_height = 100
    if 'bg_width' not in st.session_state:
        st.session_state.bg_width = 140
    if 'bg_height' not in st.session_state:
        st.session_state.bg_height = 140
    if 'logo_aspect' not in st.session_state:
        st.session_state.logo_aspect = 1.0
    if 'logo_overridden' not in st.session_state:
        st.session_state.logo_overridden = False
    if 'bg_overridden' not in st.session_state:
        st.session_state.bg_overridden = False
    if 'padding' not in st.session_state:
        st.session_state.padding = 20

    # When a logo is uploaded, set smart defaults
    if logo_file is not None:
        logo_img = Image.open(logo_file)
        orig_w, orig_h = logo_img.size
        aspect = orig_w / orig_h if orig_h != 0 else 1.0
        st.session_state.logo_aspect = aspect
        # Only set defaults if not overridden
        if not st.session_state.logo_overridden:
            st.session_state.logo_width = 100
            st.session_state.logo_height = int(100 / aspect)
        if not st.session_state.bg_overridden:
            st.session_state.bg_width = st.session_state.logo_width + 2 * st.session_state.padding
            st.session_state.bg_height = st.session_state.logo_height + 2 * st.session_state.padding

    st.markdown("---")
    st.markdown("### Logo & Background Configuration")
    config_col1, config_col2 = st.columns(2)

    with config_col1:
        st.markdown("#### Logo Settings")
        position = st.selectbox(
            "Logo Position",
            ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'custom']
        )
        if position == 'custom':
            custom_x = st.number_input("Custom X Position", min_value=0, value=400)
            custom_y = st.number_input("Custom Y Position", min_value=0, value=20)
        st.write("")
        def on_logo_width_change():
            st.session_state.logo_overridden = True
            st.session_state.logo_height = int(st.session_state.logo_width / st.session_state.logo_aspect)
            if not st.session_state.bg_overridden:
                st.session_state.bg_width = st.session_state.logo_width + 2 * st.session_state.padding
                st.session_state.bg_height = st.session_state.logo_height + 2 * st.session_state.padding
        def on_logo_height_change():
            st.session_state.logo_overridden = True
            st.session_state.logo_width = int(st.session_state.logo_height * st.session_state.logo_aspect)
            if not st.session_state.bg_overridden:
                st.session_state.bg_width = st.session_state.logo_width + 2 * st.session_state.padding
                st.session_state.bg_height = st.session_state.logo_height + 2 * st.session_state.padding
        logo_width = st.number_input(
            "Logo Width (px)", min_value=10, value=st.session_state.logo_width, key="logo_width", on_change=on_logo_width_change
        )
        logo_height = st.number_input(
            "Logo Height (px)", min_value=10, value=st.session_state.logo_height, key="logo_height", on_change=on_logo_height_change
        )
        def on_padding_change():
            st.session_state.padding = st.session_state['padding']
            if not st.session_state.bg_overridden:
                st.session_state.bg_width = st.session_state.logo_width + 2 * st.session_state.padding
                st.session_state.bg_height = st.session_state.logo_height + 2 * st.session_state.padding
        padding = st.number_input("Padding from edges (px)", min_value=0, value=st.session_state.padding, key="padding", on_change=on_padding_change)

    with config_col2:
        st.markdown("#### Background Settings")
        def on_bg_width_change():
            st.session_state.bg_overridden = True
        def on_bg_height_change():
            st.session_state.bg_overridden = True
        bg_width = st.number_input(
            "Background Width (px)", min_value=10, value=st.session_state.bg_width, key="bg_width", on_change=on_bg_width_change
        )
        bg_height = st.number_input(
            "Background Height (px)", min_value=10, value=st.session_state.bg_height, key="bg_height", on_change=on_bg_height_change
        )
        st.write("")
        st.markdown("#### Preview & Advanced")
        with st.expander("Advanced Options", expanded=False):
            opacity = st.slider("Background Opacity", 0.0, 1.0, 1.0, 0.01)
            rotation = st.slider("Logo Rotation (degrees)", -180, 180, 0, 1)
        if 'opacity' not in locals():
            opacity = 1.0
        if 'rotation' not in locals():
            rotation = 0

    st.markdown("---")
    button_col = st.columns([1,2,1])[1]
    with button_col:
        process = st.button("Process Document", use_container_width=True)

    if process:
        if pdf_file is None or logo_file is None:
            st.error("Please upload both a PDF document and a logo image.")
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
            tmp_pdf.write(pdf_file.getvalue())
            pdf_path = tmp_pdf.name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_logo:
            tmp_logo.write(logo_file.getvalue())
            logo_path = tmp_logo.name
        try:
            logo_config = {
                'width': st.session_state.logo_width,
                'height': st.session_state.logo_height,
                'position': position,
                'padding': st.session_state.padding,
                'bg_width': st.session_state.bg_width,
                'bg_height': st.session_state.bg_height,
                'opacity': opacity,
                'rotation': rotation
            }
            if position == 'custom':
                logo_config.update({
                    'x': custom_x,
                    'y': custom_y
                })
            output_filename = f"modified_{pdf_file.name}"
            output_path = os.path.join(tempfile.gettempdir(), output_filename)
            with st.spinner("Processing document..."):
                process_pdf_with_logo(
                    input_pdf_path=pdf_path,
                    output_pdf_path=output_path,
                    logo_path=logo_path,
                    pages='all',
                    logo_config=logo_config
                )
            with open(output_path, "rb") as f:
                st.download_button(
                    label="Download Processed PDF",
                    data=f,
                    file_name=output_filename,
                    mime="application/pdf"
                )
            st.success("Document processed successfully!")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        finally:
            os.unlink(pdf_path)
            os.unlink(logo_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

if __name__ == "__main__":
    main()