# 1. Minimal Python runtime
FROM python:3.11-slim

# 2. Copy pre-built uv binary from official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. Set working directory
WORKDIR /app

# 4. Install dependencies using uv into system Python (added greenlet)
RUN uv pip install --system fastapi uvicorn pydantic google-genai python-dotenv sqlalchemy aiosqlite greenlet

# 5. Copy project source code
COPY . .

# 6. Expose default FastAPI port
EXPOSE 8000

# 7. Start Uvicorn server bound to 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]