import fitz
import sys

doc = fitz.open("/Users/luisdiegocolinmendiola/Desktop/Dev/ai-blueye/training/dataset/Copia de 3-FASCCULOINUNDACIONES.PDF")

for page in doc: 
    blocks = page.get_text("dict")
    for block in blocks["blocks"]:
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    print(f"size={span['size']:.1f} | text={span['text'][:80]}")

print("Transcription completed")