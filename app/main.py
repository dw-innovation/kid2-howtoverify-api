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

origins = origins = ["*.howtoverify.info"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class Request(BaseModel):
    click_history: List

    @validator('click_history', each_item=True, always=True)
    def check_items_in_click_history(cls, v):
        if not v.startswith('http://dw.com/'):
            raise ValueError('Not valid input')
        return v


class Response(BaseModel):
    nodes: List
    links: List


@app.post("/graph", response_model=Response)
def subgraph(click_history: Request):
    return construct_subgraph(click_history)
    # return create_subgraph(click_history.click_history)


@CACHE.memoize()
def construct_subgraph(click_history):
    subgraph = KIDGraph(click_history=click_history.click_history)
    return subgraph.construct()
