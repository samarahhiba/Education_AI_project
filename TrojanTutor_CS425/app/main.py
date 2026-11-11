"""FastAPI entrypoint; per-session history and state live in memory for Week 1."""
from pathlib import Path
from uuid import uuid4
from threading import RLock
import logging
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .retrieval import retrieve
from .pedagogical_retrieval import retrieve_evidence
from .interventions import intervene, reassess
from .tutor import answer,UNITS
from .algorithms import kruskal,dijkstra,DEMO_NODES,DEMO_MST,DEMO_PATH
ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title='TrojanTutor CS425',version='0.9.0')
logger=logging.getLogger('trojantutor')
@app.exception_handler(Exception)
async def handle_unexpected_error(request:Request,exc:Exception):
    # Do not leak stack traces, local file paths, or secrets into the browser.
    logger.exception('Unhandled error during %s %s',request.method,request.url.path)
    return JSONResponse(status_code=500,content={'detail':'Unexpected backend error. Check the server terminal for the traceback.'})
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
SESSIONS={};LOCK=RLock()
class Question(BaseModel):
    session_id:str
    question:str=Field(min_length=1,max_length=1200)
class Search(BaseModel):
    query:str=Field(min_length=1,max_length=500)
    unit:str|None=None
class EvidenceRequest(BaseModel):
    query:str=Field(min_length=1,max_length=1200)
    unit:str|None=None
    concept:str|None=None
    student_explanation:str|None=None
    mode:str="hybrid"
    limit:int=Field(default=5,ge=1,le=25)
    lecture:str|None=None

class InterventionRequest(BaseModel):
    concept_id:str
    student_explanation:str=Field(min_length=1,max_length=3000)
    mode:str='pedagogical'

class ReassessmentRequest(BaseModel):
    concept_id:str
    student_explanation:str=Field(min_length=1,max_length=3000)

class GraphRequest(BaseModel):
    algorithm:str
    nodes:list[str]=Field(default_factory=lambda:DEMO_NODES.copy())
    edges:list[list]=Field(default_factory=list)
    start:str='A'
@app.get('/')
def home():return FileResponse(ROOT/'static/index.html')
@app.get('/api/health')
def health():return {'status':'ok','unit_count':len(UNITS)}
@app.get('/api/units')
def units():return {'units':UNITS}
@app.post('/api/session')
def session(unit:str='Minimum Spanning Trees'):
    if unit not in UNITS:raise HTTPException(400,'Unknown unit')
    sid=uuid4().hex
    with LOCK:SESSIONS[sid]={'unit':unit,'history':[]}
    return {'session_id':sid,'unit':unit}
@app.post('/api/ask')
def ask(q:Question):
    with LOCK:
        state=SESSIONS.get(q.session_id)
        if not state:raise HTTPException(404,'Unknown session')
        try:result=answer(q.question,state['unit'],state['history'])
        except (RuntimeError, OSError, ImportError, ValueError) as e:
            logger.exception('Tutor inference failed')
            raise HTTPException(503,'Tutor data unavailable. Run python -m app.ingest to rebuild data/chunks.json and check data/concepts.json.') from e
        state['history']+= [{'role':'user','content':q.question},{'role':'assistant','content':result['answer'],'concept':result.get('concept_id'),'intent':result.get('intent')}]
        state['history']=state['history'][-16:]
    return result
@app.post('/api/search')
def search(q:Search):
    if q.unit is not None and q.unit not in UNITS:raise HTTPException(400,'Unknown unit')
    return {'sources':retrieve(q.query,q.unit)}
@app.post('/api/evidence')
def evidence(q:EvidenceRequest):
    if q.unit is not None and q.unit not in UNITS:raise HTTPException(400,'Unknown unit')
    try:return retrieve_evidence(q.query,q.unit,q.concept,q.student_explanation,q.mode,q.limit,q.lecture)
    except ValueError as e:raise HTTPException(400,str(e))

@app.post('/api/intervene')
def intervention(q:InterventionRequest):
    try:return intervene(q.concept_id,q.student_explanation,mode=q.mode)
    except ValueError as e:raise HTTPException(400,str(e))

@app.post('/api/reassess')
def intervention_reassessment(q:ReassessmentRequest):
    try:return reassess(q.concept_id,q.student_explanation)
    except ValueError as e:raise HTTPException(400,str(e))

@app.post('/api/algorithm')
def algorithm(q:GraphRequest):
    try:
        edges=q.edges or (DEMO_MST if q.algorithm=='kruskal' else DEMO_PATH)
        if q.algorithm=='kruskal':return kruskal(q.nodes,edges)
        if q.algorithm=='dijkstra':return dijkstra(q.nodes,edges,q.start)
        raise ValueError('Choose kruskal or dijkstra')
    except ValueError as e:raise HTTPException(400,str(e))
