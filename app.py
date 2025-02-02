from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text, Column, String, Integer
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os
from typing import List

# 環境変数をロード
load_dotenv()

# FastAPIアプリケーションの初期化
app = FastAPI()

# CORS設定
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース設定
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variable")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# データベース接続依存関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Product(Base):
    __tablename__ = "m_product_horie"
    id = Column(Integer, primary_key=True)
    code = Column(String(13), unique=True, index = True, nullable=False)
    name = Column(String(50), nullable=False)
    price = Column(Integer, nullable=False)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/products/{code}")
async def get_product_by_code(code:str, db:SessionLocal = Depends(get_db)):
    query = text("SELECT name, price FROM m_product_horie WHERE code = :code")
    result = db.execute(query, {"code":code}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"name": result[0], "price": result[1]}

