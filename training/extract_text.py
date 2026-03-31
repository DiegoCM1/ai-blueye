import fitz          # PyMuPDF — reads PDF structure and extracts embedded text
import pytesseract   # Python wrapper for Tesseract OCR — reads text from images
from PIL import Image  # Pillow — converts raw pixel data into an image Tesseract can read
import io            # handles in-memory byte streams (no temp files needed)
from pathlib import Path

dataset_path = "/Users/luisdiegocolinmendiola/Desktop/Dev/ai-blueye/training/raw_data"
output_path = "/Users/luisdiegocolinmendiola/Desktop/Dev/ai-blueye/training/extracted/ocr-no-cleaning"


for filename in Path(dataset_path).glob("*.[Pp][Dd][Ff]"):
        doc = fitz.open(filename)
        output = ""

        for i, page in enumerate(doc):
            # Primary extraction: reads actual character data embedded in the PDF — exact, fast
            text = page.get_text("text")

            if len(text.strip()) < 50:
                # Page came back empty — it's a scanned image, not selectable text
                # Render the page as a 300 DPI pixel map (higher DPI = better OCR accuracy)
                pixmap = page.get_pixmap(dpi=300)
                # Convert raw pixel bytes to a PNG in memory, then open it as a Pillow image
                img = Image.open(io.BytesIO(pixmap.tobytes("png")))
                # Run OCR with the Spanish language pack to handle tildes, ñ, accents
                text = pytesseract.image_to_string(img, lang="spa")

            output += f"\n--- Page {i+1} ---\n"
            output += text


        # Write all pages for this PDF into a single TXT file named after the PDF
        final_output_path = Path(output_path) / f"{filename.stem}.txt"
        final_output_path.write_text(output)
        


        
