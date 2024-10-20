from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, create_engine, Session, select
from starlette.templating import Jinja2Templates

# Initialize FastAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database models and setup
class NoteBase(SQLModel):
    content: str

class NoteCreate(NoteBase):
    pass

class Note(NoteBase, table=True):
    id: int = Field(default=None, primary_key=True)

# SQLite database engine
engine = create_engine("sqlite:///notes.db", echo=True)
SQLModel.metadata.create_all(engine)

# Route to display notes
@app.get("/", response_class=HTMLResponse)
async def read_notes(request: Request):
    with Session(engine) as session:
        notes = session.exec(select(Note)).all()
    return templates.TemplateResponse("index.html", {"request": request, "notes": notes})

# Route to add a new note
@app.post("/add", response_class=HTMLResponse)
async def add_note(request: Request, content: str = Form(...)):
    with Session(engine) as session:
        db_note = Note(content=content)
        session.add(db_note)
        session.commit()
        session.refresh(db_note)
    return templates.TemplateResponse("_note_item.html", {"request": request, "note": db_note}, status_code=200)

# Route to delete a note
@app.get("/delete/{note_id}", response_class=HTMLResponse)
async def delete_note(request: Request, note_id: int):
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if note:
            session.delete(note)
            session.commit()
    # Return the updated notes list
    with Session(engine) as session:
        notes = session.exec(select(Note)).all()
    return templates.TemplateResponse("_note_list.html", {"request": request, "notes": notes})

# Route to display expanded note
@app.get("/note/{note_id}", response_class=HTMLResponse)
async def get_note(request: Request, note_id: int):
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            return HTMLResponse("Note not found", status_code=404)
    return templates.TemplateResponse("_note_expanded.html", {"request": request, "note": note})

# Route to collapse the expanded note
@app.get("/note/collapse/{note_id}", response_class=HTMLResponse)
async def collapse_note(request: Request, note_id: int):
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            return HTMLResponse("Note not found", status_code=404)
    return templates.TemplateResponse("_note_item.html", {"request": request, "note": note})

# Route to update a note
@app.put("/note/update/{note_id}", response_class=HTMLResponse)
async def update_note(request: Request, note_id: int, content: str = Form(...)):
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            return HTMLResponse("Note not found", status_code=404)
        note.content = content
        session.add(note)
        session.commit()
        session.refresh(note)
    return templates.TemplateResponse("_note_item.html", {"request": request, "note": note})
