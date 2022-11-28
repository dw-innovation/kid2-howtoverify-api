from pydantic import BaseModel, ValidationError, validator
from app.kg_ops import KIDGraph, validate_click_history
from typing import Dict, Any, AnyStr, List
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from diskcache import Cache

app = FastAPI()
load_dotenv()
CACHE = Cache('tmp')

origins = ["https://preview.howtoverify.info", "http://localhost:3000", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class ClickHistoryRequest(BaseModel):
    click_history: List

    @validator('click_history', always=True)
    def check_items_in_click_history(cls, v):
        if not validate_click_history(v):
            raise ValueError('Not valid input')
        return v


class SearchRequest(BaseModel):
    query: str


class Response(BaseModel):
    nodes: List
    links: List


class SearchResponse(BaseModel):
    category: Dict
    results: List


@app.post("/graph", response_model=Response)
def subgraph(click_history: ClickHistoryRequest):
    return construct_subgraph(click_history)


@app.post("/search", response_model=List[SearchResponse])
def search(search_request: SearchRequest):
    return _search(search_request)


@app.get("/getIndex", response_model=List)
def get_index():
    return _get_index()


@CACHE.memoize()
def _get_index():
    return KIDGraph.get_index()


@CACHE.memoize()
def _search(search_request):
    return KIDGraph.search(begin_node=search_request.query)


@CACHE.memoize()
def construct_subgraph(click_history):
    subgraph = KIDGraph(click_history=click_history.click_history)
    return subgraph.construct()
