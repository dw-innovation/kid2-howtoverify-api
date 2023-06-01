from pydantic import BaseModel,  validator
import app.kg_ops as kg_ops
from typing import Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from diskcache import Cache

app = FastAPI()
CACHE = Cache('tmp')

origins = ["https://preview.howtoverify.info", "https://www.howtoverify.info", "https://howtoverify.info", "https://kid-howtoverify-frontend-dev.vercel.app", "http://localhost:3000", "http://localhost:3001", "https://api.howtoverify.info"]
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
        if not kg_ops.validate_click_history(v):
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
    return kg_ops.get_index()


@CACHE.memoize()
def _search(search_request):
    return kg_ops.search(begin_node=search_request.query)


@CACHE.memoize()
def construct_subgraph(click_history):
    return kg_ops.construct(click_history=click_history.click_history)
