# ⚡ Structured AI Extraction Microservice

An asynchronous, production-grade microservice that transforms unstructured customer support text into validated, deterministic JSON objects using Gemini 2.5 Flash, FastAPI, and Pydantic v2. Extracted entities are persisted asynchronously to SQLite via SQLAlchemy ORM.

Fully containerized with Docker using `uv` for ultra-fast dependency resolution.

---

## 🎯 Key Features

- **Guaranteed Output Schema:** Leverages Gemini's structured output generation with Pydantic schemas to prevent JSON parsing failures and schema drift.
- **Async Database Persistence:** Uses `SQLAlchemy 2.0` with `aiosqlite` to store raw inputs and structured extractions without blocking the event loop.
- **FastAPI Core:** Automatic OpenAPI (`/docs`) generation, typed request validation, and asynchronous request handling.
- **High-Performance Packaging:** Built with Astral’s `uv` package manager for lightning-fast environment setup and container builds.
- **Containerized:** Orchestrated via `docker-compose` with mounted volumes for database persistence across restarts.

---

## 🛠️ Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **AI Model:** Google Gemini (`gemini-2.5-flash`) via `google-genai` SDK
- **Data Validation:** Pydantic v2
- **Database & ORM:** SQLite, SQLAlchemy (Async), `aiosqlite`
- **Package Manager:** `uv`
- **Containerization:** Docker & Docker Compose

---

## 🏗️ Architecture


```

[ Unstructured Text Payload ]
│
▼
[ POST /analyze-ticket Endpoint ]
│
▼
[ Gemini 2.5 Flash + Structured Schema Enforcement ]
│
▼
[ Pydantic Runtime Type Validation ]
│
├──► [ Async Persistence -> SQLite (tickets.db) ]
│
▼
[ Validated JSON Response ]

```

---

## ⚙️ Local Development Setup

### Prerequisites
- Python 3.10+
- `uv` installed (`pip install uv` or `uv venv`)
- Google Gemini API Key ([Get Key Here](https://aistudio.google.com/app/apikey))

### 1. Clone & Setup Environment
```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install fastapi uvicorn pydantic google-genai python-dotenv sqlalchemy aiosqlite greenlet

```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here

```

### 3. Run Locally

```bash
uvicorn main:app --reload

```

Navigate to `http://127.0.0.1:8000/docs` to test endpoints via Swagger UI.

---

## 🐳 Docker Deployment

To build and run the microservice inside a containerized environment:

```bash
# Build and start the container
docker compose up --build

```

Access the live API at `http://localhost:8000/docs`.

---

## 📡 API Endpoints

### `POST /analyze-ticket`

Extracts structured information from raw customer service text and persists the result to the database.

**Request Body:**

```json
{
  "raw_text": "Hi, my application crashes with Error 500 every time I click on 'Export Report'. This is blocking our team before tomorrow's meeting!"
}

```

**Response (HTTP 200 OK):**

```json
{
  "category": "Technical",
  "urgency_score": 5,
  "summary": "Application crashes with Error 500 when attempting to export reports, blocking team operations before a critical meeting.",
  "action_items": [
    "Investigate the root cause of the Error 500 on report export functionality.",
    "Identify and implement an urgent fix or provide a workaround for the user.",
    "Review application logs for more specific error details related to the crash."
  ]
}

```

### `GET /tickets`

Retrieves all historical ticket extractions from SQLite.

**Response (HTTP 200 OK):**

```json
[
  {
    "id": 1,
    "category": "Technical",
    "urgency_score": 5,
    "summary": "Application crashes with Error 500 when attempting to export reports...",
    "action_items": [ ... ],
    "raw_text": "Hi, my application crashes with Error 500 every time I click on 'Export Report'..."
  }
]

```

```

---

### Suggested Bullet Points for Your Resume

> **AI Backend Engineer / Python Developer Project**
> * Developed an asynchronous AI data extraction microservice using **FastAPI**, **Pydantic v2**, and **Gemini 2.5 Flash**, achieving deterministic JSON parsing via schema enforcement.
> * Engineered async database persistence using **SQLAlchemy** and **aiosqlite**, enabling non-blocking I/O operations for incoming requests.
> * Optimized Docker build speeds by replacing standard `pip` with Astral’s **`uv`** package manager and containerized the service using Docker Compose.

<ElicitationsGroup message="Would you like assistance with any of these final steps?">
  <Elicitation label="How to push this project to GitHub step-by-step" query="How do I initialize git and push this project to GitHub safely without uploading my .env file?"/>
  <Elicitation label="Add a Streamlit frontend UI for demoing" query="Show me how to build a simple interactive Streamlit dashboard that talks to this FastAPI microservice."/>
</ElicitationsGroup>

```