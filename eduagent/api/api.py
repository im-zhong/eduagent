# app.py
from fastapi import FastAPI

api = FastAPI()


@api.get(path="/hello")
async def hello() -> str:
    return "hello"
