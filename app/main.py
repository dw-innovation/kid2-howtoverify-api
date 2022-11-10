from pydantic import BaseModel, ValidationError, validator
from app.kg_ops import KIDGraph
from typing import Dict, Any, AnyStr, List
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from diskcache import Cache

app = FastAPI()
load_dotenv()
CACHE = Cache('tmp')

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class ClickHistoryRequest(BaseModel):
    click_history: List

    @validator('click_history', each_item=True, always=True)
    def check_items_in_click_history(cls, v):
        if not v.startswith('http://dw.com/'):
            raise ValueError('Not valid input')
        return v


class SearchRequest(BaseModel):
    query = str
    category: str


class Response(BaseModel):
    nodes: List
    links: List

class SearchResponse(BaseModel):
    List


@app.post("/graph", response_model=Response)
def subgraph(click_history: ClickHistoryRequest):
    return construct_subgraph(click_history)


@app.post("/search", response_model=SearchResponse)
def search(query:SearchRequest):
    return KIDGraph.search(query)


@CACHE.memoize()
def construct_subgraph(click_history):
    subgraph = KIDGraph(click_history=click_history.click_history)
    return subgraph.construct()
