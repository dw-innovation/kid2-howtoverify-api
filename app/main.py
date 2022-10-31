from pydantic import BaseModel
from app.kg_ops import KIDGraph
from typing import Dict, Any, AnyStr, List
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
load_dotenv()

origins = origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class Request(BaseModel):
    click_history: List


class Response(BaseModel):
    nodes: List
    links: List


@app.post("/graph", response_model=Response)
def find_similar(click_history: Request):

    subgraph = KIDGraph(click_history=click_history.click_history)
    return subgraph.construct()
    # return create_subgraph(click_history.click_history)
