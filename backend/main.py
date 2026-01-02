from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models, schemas

app = FastAPI()
#models.Base.metadata.create_all(bind=engine)

#리액트랑 연결
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get('/api/hello')
def check_handler():
    return {'name':'jisu'}
















