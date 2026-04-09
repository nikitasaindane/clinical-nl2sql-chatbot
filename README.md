# NL2SQL Clinic Chatbot

An AI-powered Natural Language to SQL system built with **Vanna 2.0** and **FastAPI**.

Users ask questions in plain English about a clinic database and receive SQL results, data tables, and optional Plotly charts — no SQL knowledge required.

---

## LLM Provider

**Option A — Google Gemini** (`gemini-2.5-flash`)

- Free via [Google AI Studio](https://aistudio.google.com/apikey)
- Sign in with your Google account, click **Create API Key**
- No credit card required

---

## Architecture

```
User (plain English)
        |
        v
  FastAPI  /chat
        |
        v
  Rate Limiter + Cache
        |
        v
  Vanna 2.0 Agent
    - GeminiLlmService      (natural language -> SQL)
    - SqliteRunner           (executes SQL against clinic.db)
    - RunSqlTool             (agent tool wrapper for SqliteRunner)
    - VisualizeDataTool      (generates Plotly charts)
    - SaveQuestionToolArgsTool        (saves Q->SQL to memory)
    - SearchSavedCorrectToolUsesTool  (retrieves similar past Q->SQL)
    - DemoAgentMemory        (in-memory similarity store)
    - DefaultUserResolver    (maps all requests to a single user)
        |
        v
  SQL Validation (SELECT-only, blocklist)
        |
        v
  SQLite clinic.db
        |
        v
  JSON Response (message + sql + rows + chart)
```

---

## Project Structure

```
nl2sql_project/
├── setup_database.py   # Creates clinic.db with schema + 200 patients/500 appts
├── vanna_setup.py      # Vanna 2.0 Agent initialisation
├── seed_memory.py      # Pre-seeds DemoAgentMemory with 15 Q&A pairs
├── main.py             # FastAPI application (POST /chat, GET /health)
├── requirements.txt    # All dependencies
├── .env.example        # Environment variable template
├── README.md           # This file
└── RESULTS.md          # 20-question test results
```

---

## Setup (Step by Step)

### 1. Clone the repository

```bash
git clone https://github.com/nikitasaindane/clinical-nl2sql-chatbot.git
cd nl2sql-clinic
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=your-actual-key
```

### 5. Create the database

```bash
python setup_database.py
```

Expected output:
```
Created 200 patients, 15 doctors, 500 appointments, 301 treatments, 300 invoices
Database saved to clinic.db
```

### 6. Seed agent memory

```bash
python seed_memory.py
```

Expected output:
```
Seeding agent memory with 15 Q&A pairs ...
  ✓ How many patients do we have?
  ...
Total memories stored: 15
Memory seeding complete.
```

### 7. Start the API server

```bash
uvicorn main:app --port 8000
```

Or use the one-liner from the assignment:

```bash
pip install -r requirements.txt && python setup_database.py \
  && python seed_memory.py && uvicorn main:app --port 8000
```

The API is now available at `http://localhost:8000`

---

## API Reference

### POST /chat

Ask a natural-language question about the clinic data.

**Request**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many patients do we have?"}'
```

**Response**
```json
{
  "message": "There are 200 patients in the database.",
  "sql_query": "SELECT COUNT(*) AS total_patients FROM patients",
  "columns": ["total_patients"],
  "rows": [[200]],
  "row_count": 1,
  "chart": null,
  "chart_type": null,
  "error": null,
  "cached": false
}
```

**Request body**

| Field      | Type   | Required | Description                        |
|------------|--------|----------|------------------------------------|
| `question` | string | Yes      | Plain-English question (1–500 chars) |

**Response body**

| Field        | Type           | Description                               |
|--------------|----------------|-------------------------------------------|
| `message`    | string         | LLM-generated summary / explanation       |
| `sql_query`  | string or null | The SQL that was generated and run        |
| `columns`    | array or null  | Column names of the result set            |
| `rows`       | array or null  | Result rows (array of arrays)             |
| `row_count`  | int or null    | Number of rows returned                   |
| `chart`      | object or null | Plotly chart with `data` and `layout`     |
| `chart_type` | string or null | Chart type: `bar`, `line`, `pie`, etc.   |
| `error`      | string or null | Error message (null on success)           |
| `cached`     | bool           | Whether the response was served from cache |

---

### GET /health

Check service status and memory item count.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 15
}
```

---

## Example Questions

```bash
# Count
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"How many patients do we have?"}' | python -m json.tool

# Revenue
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the total revenue?"}' | python -m json.tool

# Top patients
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Top 5 patients by spending"}' | python -m json.tool

# Chart
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Show revenue by doctor as a chart"}' | python -m json.tool
```

---

## Security Features

- **SELECT-only**: any non-SELECT SQL is rejected before execution
- **Blocklist**: `DROP`, `DELETE`, `INSERT`, `UPDATE`, `EXEC`, `GRANT`, `REVOKE`, `SHUTDOWN`, `xp_*`, `sp_*`, `sqlite_master` are all blocked
- **Input validation**: questions must be 1–500 characters (enforced by Pydantic)
- **Rate limiting**: 20 requests per 60 seconds per IP address

## Performance Features

- **Query caching**: identical questions return cached responses for 5 minutes
- **Agent memory**: 15 pre-seeded Q→SQL pairs give the agent a head start on common questions

---

## Bonus Features Implemented

| Feature            | Implementation                                      |
|--------------------|-----------------------------------------------------|
| Chart generation   | Plotly via `VisualizeDataTool`                      |
| Input validation   | Pydantic min/max length on `question`               |
| Query caching      | In-memory TTL cache (5 min)                         |
| Rate limiting      | Sliding window (20 req / 60 s per IP)               |
| Structured logging | Python `logging` with timestamp + level + module    |

---

## Troubleshooting

**`GOOGLE_API_KEY` not set**
```
ValueError: Google API key is required.
```
Make sure `.env` exists with `GOOGLE_API_KEY=...` and that `python-dotenv` is installed.

**`clinic.db` not found**
```
sqlite3.OperationalError: unable to open database file
```
Run `python setup_database.py` first.

**Port already in use**
```
uvicorn main:app --port 8001
```
