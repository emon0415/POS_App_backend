from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os
from db_control.connect import AzureDBConnection # connect.pyのインポート

# 環境変数をロード
load_dotenv()

# FastAPIアプリケーションの初期化
app = FastAPI()

# CORS設定
origins = [
    "http://localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# connect.py を使用してデータベース接続を確立
db_connection = AzureDBConnection()
engine = db_connection.connect()  # DBエンジンの取得

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# データベース接続依存関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/products/{code}")
async def get_product_by_code(code:str, db = Depends(get_db)):
    query = text("SELECT name, price FROM m_product_horie WHERE code = :code")
    result = db.execute(query, {"code":code}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"name": result[0], "price": result[1]}

# アプリケーション終了時のイベント
@app.on_event("shutdown")
def shutdown_event():
    db_connection.close()