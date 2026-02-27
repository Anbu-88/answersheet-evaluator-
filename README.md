# 📝 ExamAI — AI-Powered Handwritten Exam Grader

**ExamAI** uses **Google Gemini's native vision AI** to automatically grade handwritten exam sheets against an answer key — no OCR needed. Upload two PDFs, and get a detailed grading report in seconds.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_AI-2.5_Flash-4285F4?logo=google&logoColor=white)

---

## ✨ Features

- 🔍 **Native Vision AI** — Gemini reads handwriting directly from images, no OCR pipeline
- 📋 **Answer Key Analysis** — Automatically extracts questions, expected answers, and marks
- ✍️ **Handwriting Grading** — Compares student answers against the answer key with reasoning
- 📊 **PDF Report Generation** — Produces a professional grading report with per-question breakdown
- 🔄 **Retry Logic** — Automatic retries with exponential backoff for robust API calls
- 🎨 **Modern UI** — Drag & drop file upload with animated progress indicators

---

## 🏗️ Architecture

```
examai/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Environment & app configuration
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # API keys (not committed)
│   ├── .env.example             # Template for .env
│   ├── routes/
│   │   └── grading.py           # /api/grade & /api/analyze-answer-key endpoints
│   └── services/
│       ├── gemini_service.py    # Gemini AI integration (vision + JSON parsing)
│       └── pdf_service.py       # PDF → images & report PDF generation
├── frontend/
│   ├── index.html               # Main UI page
│   ├── style.css                # Styling
│   └── app.js                   # Frontend logic (upload, progress, results)
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** installed ([download](https://www.python.org/downloads/))
- **Google Gemini API Key** — get one free at [Google AI Studio](https://aistudio.google.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/Anbu-08/examai.git
cd examai
```

### 2. Set Up the Backend

```bash
# Navigate to the backend
cd backend

# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env
```

Edit `backend/.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 4. Start the Backend Server

```bash
# From the backend/ directory
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be running at **http://localhost:8000**. You can access the docs at **http://localhost:8000/docs**.

### 5. Start the Frontend

Open a **new terminal** and run:

```bash
# From the frontend/ directory
cd frontend
python -m http.server 5500
```

Open your browser and go to **http://localhost:5500**.

---

## 📖 Usage

1. **Open** the app at `http://localhost:5500`
2. **Upload** an Answer Key PDF (the correct answers with marks)
3. **Upload** a Handwritten Exam Sheet PDF (the student's submission)
4. **Click** "🚀 Grade Exam" and wait ~30–60 seconds
5. **Download** the generated PDF grading report

---

## 🔌 API Endpoints

| Method | Endpoint                  | Description                                |
|--------|---------------------------|--------------------------------------------|
| `POST` | `/api/grade`              | Grade an exam sheet against an answer key   |
| `POST` | `/api/analyze-answer-key` | Analyze & extract answer key structure only |
| `GET`  | `/health`                 | Health check                               |
| `GET`  | `/docs`                   | Interactive API documentation (Swagger)    |

### Example: Grade an Exam (cURL)

```bash
curl -X POST http://localhost:8000/api/grade \
  -F "answer_key=@answer_key.pdf" \
  -F "exam_sheet=@student_exam.pdf" \
  --output grading_report.pdf
```

---

## 🛠️ Tech Stack

| Component      | Technology                          |
|----------------|-------------------------------------|
| **AI Model**   | Google Gemini 2.5 Flash (Vision)    |
| **Backend**    | FastAPI + Uvicorn                   |
| **PDF → Image**| PyMuPDF (fitz)                      |
| **Report Gen** | ReportLab                           |
| **Frontend**   | Vanilla HTML/CSS/JS                 |
| **API Client** | google-genai SDK                    |

---

## ⚙️ Configuration

All settings are in `backend/config.py`:

| Setting              | Default              | Description                        |
|----------------------|----------------------|------------------------------------|
| `GEMINI_MODEL`       | `gemini-2.5-flash`   | Gemini model to use                |
| `MAX_UPLOAD_SIZE_MB` | `50`                 | Max upload size per file           |
| `DPI`                | `200`                | Resolution for PDF → image render  |

---

---

## 🐳 Running with Docker

You can run the entire stack using Docker and Docker Compose. This is the easiest way to get started without installing Python locally.

### 1. Requirements
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### 2. Setup
1. Edit `backend/.env` and add your `GEMINI_API_KEY`.
2. Run the following command in the root directory:

```bash
docker-compose up --build
```

### 3. Access
- **Frontend:** [http://localhost:5500](http://localhost:5500)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📄 License


This project is open source and available under the [MIT License](LICENSE).
