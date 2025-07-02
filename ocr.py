import os
import pathlib
import psycopg2

import pdf2image
import pytesseract
from flask import Flask, jsonify, render_template, request
from langcodes import Language
from PIL import Image
from werkzeug.utils import secure_filename

__author__ = "Santhosh Thottingal <santhosh.thottingal@gmail.com>"
__source__ = "https://github.com/santhoshtr/tesseract-web"

app = Flask(__name__)
UPLOAD_FOLDER = "./static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SUPPORTED_FORMATS"] = ["png", "jpeg", "jpg", "bmp", "pnm", "gif", "tiff", "webp", "pdf"]


def pdf_to_img(pdf_file):
    return pdf2image.convert_from_path(pdf_file)


def ocr_core(image: Image, language="en"):
    text = pytesseract.image_to_string(image, lang=Language.get(language).to_alpha3())
    return text


def pdf_to_text(pdf_file_path: str, language="en") -> str:
    texts = []
    images = pdf_to_img(pdf_file_path)
    for _pg, img in enumerate(images):
        texts.append(ocr_core(img, language))

    return "\n".join(texts)


def get_languages() -> dict:
    languages = {}
    alpha3codes = pytesseract.get_languages()
    for code in alpha3codes:
        language = Language.get(code)

        languages[language.language] = language.autonym()
    return languages


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html", languages=get_languages())

@app.route("/review", methods=["GET"])
def review():
    return render_template("review.html")


@app.route("/api/languages", methods=["GET"])
def listSupportedLanguages():
    return jsonify(languages=get_languages())


@app.route("/api/ocr", methods=["POST"])
def ocr():
    f = request.files["file"]
    language = request.form.get("language", default="en")
    # create a secure filename
    filename = secure_filename(f.filename)
    file_extension = pathlib.Path(filename).suffix.lower().lstrip('.') # Get extension and remove leading dot

    if not file_extension or file_extension not in app.config["SUPPORTED_FORMATS"]:
        return jsonify(error="File format not supported or missing extension"), 400

    # save file to /static/uploads
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(filepath)

    if file_extension == "pdf":
        # perform OCR on PDF
        text = pdf_to_text(filepath, language)
    else:
        # perform OCR on the processed image
        text = ocr_core(Image.open(filepath), language)

    # remove the processed image
    os.remove(filepath)

    return jsonify(text=text, filename=filename)



@app.route("/api/get_corrections", methods=["GET"])
def get_corrections():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, original_text, corrected_text, language, file_name, created_at FROM ocr_corrections ORDER BY created_at DESC")
        corrections = cur.fetchall()
        cur.close()
        conn.close()

        # Convert to a list of dictionaries for JSON serialization
        corrections_list = []
        for corr in corrections:
            corrections_list.append({
                "id": corr[0],
                "original_text": corr[1],
                "corrected_text": corr[2],
                "language": corr[3],
                "file_name": corr[4],
                "created_at": corr[5].isoformat() # Convert datetime to ISO format string
            })
        return jsonify(corrections=corrections_list), 200
    except Exception as e:
        print(f"Error fetching corrections: {e}")
        return jsonify(success=False, error=str(e)), 500


def get_db_connection():
    conn = psycopg2.connect(
        host="timescale",
        database="RAG",
        user="rag",
        password="wecandoit"
    )
    return conn

@app.route("/api/save_correction", methods=["POST"])
def save_correction():
    data = request.get_json()
    original_text = data.get("original_text")
    corrected_text = data.get("corrected_text")
    language = data.get("language")
    file_name = data.get("file_name")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ocr_corrections (original_text, corrected_text, language, file_name) VALUES (%s, %s, %s, %s)",
            (original_text, corrected_text, language, file_name)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(success=True), 200
    except Exception as e:
        print(f"Error saving correction: {e}")
        return jsonify(success=False, error=str(e)), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

