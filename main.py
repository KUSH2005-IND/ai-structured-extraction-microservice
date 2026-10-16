import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

load_dotenv()  # load_dotenv(): Reads your hidden .env file and loads GEMINI_API_KEY into your system's environment variables. This prevents hardcoding sensitive credentials in source control.

# ==========================================
# ASYNC DATABASE SETUP (SQLAlchemy + SQLite)
# ==========================================

# 1. Connection string using 'sqlite+aiosqlite' for non-blocking database I/O
DATABASE_URL = "sqlite+aiosqlite:///./tickets.db"  # Creates a local database file named 'tickets.db' in project root.

# 2. Async Engine creation (echo=True logs raw SQL queries to console for debugging)
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. Session Factory configured for async operations
AsyncSessionLocal = async_sessionmaker(engine,
                                       expire_on_commit=False)  # expire_on_commit=False keeps model attributes accessible post-commit.

# 4. Declarative Base class from which all ORM models inherit
Base = declarative_base()


# ==========================================
# DATABASE TABLE ORM MODEL
# ==========================================
class TicketDB(Base):  # Maps this Python class directly to a database table named 'tickets'
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)  # Unique auto-incrementing primary key ID for each record.
    raw_text = Column(Text, nullable=False)  # Stores the original customer text payload sent in request.
    category = Column(String, nullable=False)  # Stores extracted category ("Billing", "Technical", etc.).
    urgency_score = Column(Integer, nullable=False)  # Stores urgency score integer (1-5).
    summary = Column(Text, nullable=False)  # Stores extracted one-sentence summary.
    action_items = Column(Text, nullable=False)  # Stores action items list serialized as a JSON string.


# ==========================================
# LIFESPAN HOOK (App Startup & Shutdown)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on application startup: automatically creates 'tickets.db' and tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # Application runs while suspended here
    # Clean up operations go here after yield (if needed on shutdown)


# FastAPI instance initialized with lifespan manager hook
app = FastAPI(title="Structured AI Extraction Microservice",
              lifespan=lifespan)  # app = FastAPI(...): Creates the core Web API application instance. FastAPI automatically generates OpenAPI specs and the interactive /docs UI from this instance.
client = genai.Client(api_key=os.getenv(
    "GEMINI_API_KEY"))  # client = genai.Client(...): Initializes the Google GenAI client object, passing the secret key securely from environment variables.


# ==========================================
# DEPENDENCY INJECTION FOR DB SESSIONS
# ==========================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Creates an isolated async session per HTTP request and ensures it closes automatically when done
    async with AsyncSessionLocal() as session:
        yield session


# 1. output schema(what the AI must return?)
class SupportTicketAnalysis(
    BaseModel):  # BaseModel: The base class for defining typed structures in FastAPI and Pydantic.
    category: str = Field(
        description="Category: Billing, Technical or General"
    )
    urgency_score: int = Field(
        ge=1, le=5, description="Priority rating from 1 (low) to 5 (critical)"
        # Validation Rules (ge=1, le=5): Stands for "Greater than or equal to 1, Less than or equal to 5". If the AI tries to return an urgency score of 10, Pydantic catches it and raises a validation error before bad data enters your backend.
    )
    summary: str = Field(
        description="Concise one-sentence summary of the issue"
    )
    action_items: list[str] = Field(
        description="Concrete next steps for the support team"
    )


'''
Field(description=...): Serves a dual purpose here:
1. It provides documentation in FastAPI’s Swagger UI.

2. It is sent to Gemini as instructions so the model knows what data to extract for each field.
'''


# 2. input schema(what the client must send?)
class TicketRequest(BaseModel):  # Inherits from BaseModel to validate that request body contains 'raw_text' string.
    raw_text: str  # The raw string passed by client (e.g., {"raw_text": "I was charged twice..."}).


# setting up the route and endpoint
'''
app.post("/analyze-ticket"): Defines an HTTP POST endpoint at /analyze-ticket.
response_model=SupportTicketAnalysis: Tells FastAPI that the final JSON response sent back to the user must match the SupportTicketAnalysis schema.
'''


@app.post("/analyze-ticket", response_model=SupportTicketAnalysis)
async def analyze_ticket(request: TicketRequest, db: AsyncSession = Depends(
    get_db)):  # sync def: Declares an asynchronous function. FastAPI handles thousands of concurrent requests efficiently because I/O tasks(like waiting for an LLM response) do not block the main process thread. (like waiting for an LLM response) do not block the main process thread.
    # runtime validation & error handling
    try:  # Wraps network call, extraction, and database persistence in a try-block
        # constraining the llm(structured generation) : deterministic o/p from non-deterministic model
        response = await client.aio.models.generate_content(  # Uses await client.aio for non-blocking async network I/O
            model="gemini-2.5-flash",
            contents=request.raw_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                # response_mime_type="application/json": Forces Gemini to output strictly valid JSON instead of markdown text or conversational fluff ("Here is your JSON:...").
                response_schema=SupportTicketAnalysis,
                # response_schema=SupportTicketAnalysis: Translates the Python Pydantic class directly into a JSON Schema spec and feeds it to Gemini. Gemini uses Grammar-Guided Decoding at the token generation level to ensure every returned character follows your exact class fields.
                system_instruction="Extract structured customer service data accurately",
            ),
        )

        # Parse and validate returned JSON string into our Pydantic model
        extracted_data = SupportTicketAnalysis.model_validate_json(
            response.text)  # model_validate_json(response.text): Deserializes the raw JSON string returned by Gemini into a validated SupportTicketAnalysis Python object.

        # ==========================================
        # DATABASE WRITE STEP
        # ==========================================
        # Instantiate the database ORM model using extracted data
        db_ticket = TicketDB(
            raw_text=request.raw_text,
            category=extracted_data.category,
            urgency_score=extracted_data.urgency_score,
            summary=extracted_data.summary,
            action_items=json.dumps(extracted_data.action_items)  # Converts list to JSON string for SQLite storage
        )

        db.add(db_ticket)  # Stages the new record in the database session
        await db.commit()  # Commits the transaction to disk asynchronously
        await db.refresh(db_ticket)  # Refreshes the instance to populate auto-generated DB attributes (e.g., id)

        return extracted_data  # Returns typed Pydantic response back to client

    except Exception as e:
        await db.rollback()  # Rollback any active database transaction if processing fails
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


# ==========================================
# READ ENDPOINT TO FETCH STORED TICKETS
# ==========================================
@app.get("/tickets")  # GET endpoint allowing clients to view all historical tickets saved in the database
async def list_tickets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TicketDB))  # Executes async 'SELECT * FROM tickets' query
    tickets = result.scalars().all()  # Extracts ORM instances from query result

    # Return formatted list of stored tickets with action_items parsed back into lists
    return [
        {
            "id": t.id,
            "category": t.category,
            "urgency_score": t.urgency_score,
            "summary": t.summary,
            "action_items": json.loads(t.action_items),  # Deserializes JSON string back to list
            "raw_text": t.raw_text
        }
        for t in tickets
    ]