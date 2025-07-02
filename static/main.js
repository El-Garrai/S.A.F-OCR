const dropZone = document.querySelector(".drop_zone");
const input = document.querySelector("#uploadimage");

let state = {
    isDragging: false,
    file: null,
    originalText: "",
    fileName: "",
    resultTextarea: document.querySelector("#resulttext")
};

input.addEventListener("change", () => {
    const files = input.files;
    onDrop(files[0]);
});

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("is-dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("is-dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("is-dragover");
    const files = e.dataTransfer.files;
    onDrop(files[0]);
});

document.onpaste = (event) => {
    event.preventDefault();
    const items = event.clipboardData?.items;
    for (let index in items) {
        const item = items[index];
        if (item.kind === 'file') {
            const blob = item.getAsFile();
            onDrop(blob);
        }
    }
};

const displayImage = () => {
    document.querySelector("#ocr-img").src = URL.createObjectURL(state.file);
    document.querySelector("#ocr-img").classList.remove('d-none');
    document.querySelector("#ocr-pdf").classList.add('d-none');
}

const displayPdf = () => {
    document.querySelector("#ocr-img").classList.add('d-none');
    document.querySelector("#ocr-pdf").src = URL.createObjectURL(state.file);
    document.querySelector("#ocr-pdf").classList.remove('d-none');
}

const onDrop = (file) => {
    if (!file) return;
    state.file = file;
    if (file.type.startsWith("image/")) {
        displayImage();
    } else if (file.type === "application/pdf") {
        displayPdf();
    }
}

function doOCR() {
    if (!state.file) {
        state.resultTextarea.value = "الرجاء تحديد ملف أولاً.";
        return;
    }

    const data = new FormData();
    const language = document.getElementById('source_lang').value;
    data.append('file', state.file);
    data.append('language', language);
    state.resultTextarea.value = "جارٍ المسح...";

    fetch('/api/ocr', {
        method: 'POST',
        body: data
    })
    .then(response => response.json())
    .then(result => {
        state.resultTextarea.value = result.error || result.text;
        if (result.text) {
            state.originalText = result.text;
            state.fileName = result.filename;
        }
    })
    .catch(() => {
        state.resultTextarea.value = "حدث خطأ ما.";
    });
}

function saveCorrection() {
    const correctedText = state.resultTextarea.value;
    const language = document.getElementById('source_lang').value;

    if (!state.originalText || !state.fileName) {
        alert("لا يوجد نص أصلي أو اسم ملف لحفظ التصحيح.");
        return;
    }

    if (correctedText === state.originalText) {
        alert("لم يتم إجراء أي تصحيحات.");
        return;
    }

    fetch('/api/save_correction', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            original_text: state.originalText,
            corrected_text: correctedText,
            language: language,
            file_name: state.fileName
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            alert("تم حفظ التصحيح بنجاح!");
            state.originalText = ""; // Clear after saving
            state.fileName = ""; // Clear after saving
        } else {
            alert("فشل حفظ التصحيح: " + result.error);
        }
    })
    .catch(error => {
        alert("حدث خطأ أثناء حفظ التصحيح: " + error);
    });
}

function copyResult() {
    const copyButton = document.getElementById('copyButton');
    if (state.resultTextarea && copyButton) {
        state.resultTextarea.select();
        state.resultTextarea.setSelectionRange(0, 99999); // For mobile devices
        navigator.clipboard.writeText(state.resultTextarea.value)
            .then(() => {
                const originalText = copyButton.textContent;
                copyButton.textContent = "تم النسخ!";
                setTimeout(() => {
                    copyButton.textContent = originalText;
                }, 2000); // Change back after 2 seconds
            })
            .catch(err => {
                console.error('فشل نسخ النص:', err);
                alert("فشل نسخ النص.");
            });
    }
}