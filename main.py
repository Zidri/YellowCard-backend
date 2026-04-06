# main.py
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader, PdfMerger
from docx import Document
from PIL import Image
import fitz  # PyMuPDF
import os
import uuid
import base64

app = Flask(__name__)
CORS(app)

# --------------------
# Folders
# --------------------
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# --------------------
# Convert PDF to Word
# --------------------
@app.route("/convert", methods=["POST"])
def convert_pdf_to_word():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Invalid file type"}), 400

    # Save with unique name
    pdf_path = os.path.join("uploads", f"{uuid.uuid4().hex}_{file.filename}")
    file.save(pdf_path)

    doc = Document()
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        text = page.extract_text() or "[No text found on this page]"
        doc.add_paragraph(text)

    output_filename = file.filename.replace(".pdf", ".docx")
    output_path = os.path.join("outputs", f"{uuid.uuid4().hex}_{output_filename}")
    doc.save(output_path)

    # Clean up upload
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    return send_file(output_path, as_attachment=True)

# --------------------
# Merge PDFs
# --------------------
@app.route("/merge", methods=["POST"])
def merge_pdfs():
    if "files" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = request.files.getlist("files")
    pdf_files = [f for f in files if f.filename.lower().endswith(".pdf")]
    if not pdf_files:
        return jsonify({"error": "No PDF files found"}), 400

    saved_paths = []
    for f in pdf_files:
        path = os.path.join("uploads", f"{uuid.uuid4().hex}_{f.filename}")
        f.save(path)
        saved_paths.append(path)

    merger = PdfMerger()
    for path in saved_paths:
        merger.append(path)

    output_filename = f"merged_{uuid.uuid4().hex}.pdf"
    output_path = os.path.join("outputs", output_filename)
    merger.write(output_path)
    merger.close()

    # Clean up uploads
    for path in saved_paths:
        if os.path.exists(path):
            os.remove(path)

    return send_file(output_path, as_attachment=True)

# --------------------
# Resize Image
# --------------------
@app.route("/resize", methods=["POST"])
def resize_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not (file.filename.lower().endswith(".jpg") or file.filename.lower().endswith(".png")):
        return jsonify({"error": "Only JPG and PNG allowed"}), 400

    # Save with unique name
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    input_path = os.path.join("uploads", filename)
    file.save(input_path)

    # Get scale safely
    try:
        scale = float(request.form.get("scale", 100)) / 100
    except ValueError:
        scale = 1.0

    try:
        img = Image.open(input_path)
        new_width = max(1, int(img.width * scale))
        new_height = max(1, int(img.height * scale))
        resized_img = img.resize((new_width, new_height)).convert("RGB")

        output_filename = f"resized_{uuid.uuid4().hex}.png"
        output_path = os.path.join("outputs", output_filename)
        resized_img.save(output_path)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

    return send_file(output_path, as_attachment=True)

# --------------------
# Preview PDF
# --------------------
@app.route("/preview_pdf", methods=["POST"])
def preview_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    pdf_file = request.files["file"]

    try:
        pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        pages_base64 = []

        for page_number in range(len(pdf_doc)):
            page = pdf_doc[page_number]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            b64_str = base64.b64encode(img_bytes).decode("utf-8")
            pages_base64.append(f"data:image/png;base64,{b64_str}")

        pdf_doc.close()
        return jsonify({"pages": pages_base64})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------
# Edit PDF placeholder
# --------------------
@app.route("/edit_pdf", methods=["POST"])
def edit_pdf():
    return jsonify({"message": "PDF editing endpoint"})

# --------------------
# Run app
# --------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)