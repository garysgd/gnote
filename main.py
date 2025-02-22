# main.py

from fastapi import FastAPI, Request, Form, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional, List
from starlette.templating import Jinja2Templates
from sqlalchemy import asc, desc

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database models and setup
class NoteBase(SQLModel):
    content: str

class NoteCreate(NoteBase):
    pass

class Note(NoteBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order: int = Field(default=0, index=True)

engine = create_engine("sqlite:///notes.db", echo=True)
SQLModel.metadata.create_all(engine)

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_notes(request: Request):
    with Session(engine) as session:
        notes = session.exec(select(Note).order_by(asc(Note.order))).all()
    return templates.TemplateResponse("index.html", {"request": request, "notes": notes})

@app.post("/add", response_class=HTMLResponse)
async def add_note(request: Request, content: str = Form(...)):
    with Session(engine) as session:
        highest_order_note = session.exec(select(Note).order_by(desc(Note.order))).first()
        new_order = highest_order_note.order + 1 if highest_order_note else 0

        db_note = Note(content=content, order=new_order)
        session.add(db_note)
        session.commit()
        session.refresh(db_note)
    return templates.TemplateResponse("_note_item.html", {"request": request, "note": db_note})

@app.post("/notes/reorder")
async def reorder_notes(order: List[int] = Body(...)):
    with Session(engine) as session:
        for idx, note_id in enumerate(order):
            note = session.get(Note, note_id)
            if note:
                note.order = idx
                session.add(note)
        session.commit()
    return {"status": "success"}

@app.post("/notes/delete", response_class=HTMLResponse)
async def delete_notes(request: Request, selected_notes: List[int] = Form(...)):
    with Session(engine) as session:
        for note_id in selected_notes:
            note = session.get(Note, note_id)
            if note:
                session.delete(note)
        session.commit()
        notes = session.exec(select(Note).order_by(asc(Note.order))).all()
    return templates.TemplateResponse("_note_list.html", {"request": request, "notes": notes})

@app.post("/notes/merge", response_class=HTMLResponse)
async def merge_notes(request: Request, selected_notes: List[int] = Form(...)):
    with Session(engine) as session:
        notes_to_merge = session.exec(select(Note).where(Note.id.in_(selected_notes)).order_by(asc(Note.order))).all()
        if not notes_to_merge:
            notes = session.exec(select(Note).order_by(asc(Note.order))).all()
            return templates.TemplateResponse("_note_list.html", {"request": request, "notes": notes})
        
        merged_content = " ".join(note.content for note in notes_to_merge)
        highest_order_note = session.exec(select(Note).order_by(desc(Note.order))).first()
        new_order = highest_order_note.order + 1 if highest_order_note else 0
        merged_note = Note(content=merged_content, order=new_order)
        session.add(merged_note)

        for note in notes_to_merge:
            session.delete(note)
        session.commit()

        notes = session.exec(select(Note).order_by(asc(Note.order))).all()
    return templates.TemplateResponse("_note_list.html", {"request": request, "notes": notes})

# Existing routes for note detail, update, collapse, etc.
@app.get("/note/{note_id}", response_class=HTMLResponse)
async def get_note_detail(request: Request, note_id: int):
    with Session(engine) as session:
        note = session.get(Note, note_id)
    return templates.TemplateResponse("_note_expanded.html", {"request": request, "note": note})

@app.put("/note/update/{note_id}", response_class=HTMLResponse)
async def update_note(request: Request, note_id: int, content: str = Form(...)):
    with Session(engine) as session:
        note = session.get(Note, note_id)
        note.content = content
        session.add(note)
        session.commit()
        session.refresh(note)
    return templates.TemplateResponse("_note_item.html", {"request": request, "note": note})

@app.get("/note/collapse/{note_id}", response_class=HTMLResponse)
async def collapse_note(request: Request, note_id: int):
    with Session(engine) as session:
        note = session.get(Note, note_id)
    return templates.TemplateResponse("_note_item.html", {"request": request, "note": note})
