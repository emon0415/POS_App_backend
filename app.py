from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from db_control.connect import AzureDBConnection # connect.pyのインポート
import logging

# エラーハンドリング用ログの設定
logging.basicConfig(
    level=logging.INFO,  # INFO以上のログを表示
    format="%(asctime)s - %(levelname)s - %(message)s",  # ログのフォーマット
    handlers=[
        logging.StreamHandler()  # 標準出力に出力
    ]
)

# 環境変数をロード
load_dotenv()

# FastAPIアプリケーションの初期化
app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    logging.info(f"Request received for product code: {code}")
    try:
        query = text("SELECT name, price FROM m_product_horie WHERE code = :code")
        logging.info(f"Executing query: {query}")
        logging.info(f"Query parameters: {{'code': code}}")
        result = db.execute(query, {"code":code}).fetchone()
        logging.info(f"Query result: {result}")
        if not result:
            logging.warning(f"Product not found: {code}")
            raise HTTPException(status_code=404, detail="Product not found")
        logging.info(f"Product found: {result}")
        return {"name": result[0], "price": result[1]}
    except HTTPException as e:
        logging.error(f"HTTP Exception: {e.detail}")
        raise e
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# アプリケーション終了時のイベント
@app.on_event("shutdown")
def shutdown_event():
    db_connection.close()

# DBに接続しているかを確認するだけのエンドポイント
@app.get("/db/status")
async def check_db_status():
    try:
        db_connection.connect()  # 接続確認用
        return {"status": "Database connection is healthy."}
    except Exception as e:
        logging.error(f"Database connection error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection failed.")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
