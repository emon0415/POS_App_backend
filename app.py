from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from db_control.connect import AzureDBConnection # connect.pyのインポート
import logging
import uvicorn
import os
from pydantic import BaseModel
from db_control.schemas import Product, ProductCreate, Transaction, TransactionCreate, TransactionDetail, TransactionDetailCreate, TransactionWithDetails
from datetime import datetime

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
        raise HTTPException(status_code=500, detail="Database connection failed.")


# コードをキーにDBにあるm_product_horieからnameとpriceを引っ張ってくるエンドポイント
@app.get("/products/{code}", response_model=Product)
async def get_product_by_code(code:str, db = Depends(get_db)):
    try:
        query = text("SELECT name, price FROM m_product_horie WHERE code = :code")
        result = db.execute(query, {"code":code}).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Product not found")
        return Product(PRD_ID=result[0], CODE=result[1], NAME=result[2], PRICE=result[3])
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# 新規取引登録用のリクエストモデル
class AddTransactionRequest(BaseModel):
    emp_cd: str
    store_cd: str
    pos_no: str
    total_amt: int

# 取引テーブルへの登録
@app.post("/add_transaction", response_model=Transaction)
async def add_transaction(data: AddTransactionRequest, db=Depends(get_db)):
    logging.info(f"Received request to add transaction: {data}")
    emp_cd= data.emp_cd
    store_cd= data.store_cd 
    pos_no= data.pos_no
    total_amt= data.total_amt

    try:
        # 現在の日時を取得
        transaction_datetime = datetime.now()

        with db.begin():
            # 新規取引を挿入
            transaction_query = text("""
                INSERT INTO transaction_horie (DATETIME, EMP_CD, STORE_CD, POS_NO, TOTAL_AMT)
                VALUES (:DATETIME, :EMP_CD, :STORE_CD, :POS_NO, :TOTAL_AMT)
            """)
            db.execute(transaction_query, {
                "DATETIME": transaction_datetime,
                "EMP_CD": emp_cd,
                "STORE_CD": store_cd,
                "POS_NO": pos_no,
                "TOTAL_AMT": total_amt,
            })

            # 挿入された取引キーを取得
            last_id_query = text("SELECT LAST_INSERT_ID() AS TRD_ID")
            last_id = db.execute(last_id_query).fetchone()["TRD_ID"]

        # 成功レスポンスデータを作成
        return Transaction(
            TRD_ID=last_id,
            DATETIME=transaction_datetime,
            EMP_CD=emp_cd,
            STORE_CD=store_cd,
            POS_NO=pos_no,
            TOTAL_AMT=total_amt,
        )
    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error occurred: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred: {str(e)}"
        )



# データ検証用モデル
class TransactionDetailData(BaseModel):
    TRD_ID: int # トランザクションID
    PRD_CODE: str # 商品コード
    PRD_NAME: str # 商品名
    PRD_PRICE: int # 商品単価

@app.post("/add_transaction-detail", response_model=TransactionDetail)
async def add_transaction_detail(data: TransactionDetailData, db=Depends(get_db)):
    try:
        # 商品コードから商品マスタテーブルにアクセスし、PRD_IDを取得
        product_query = text("SELECT PRD_ID FROM m_product_horie WHERE code = :code")
        product_result = db.execute(product_query, {"code": data.PRD_CODE}).fetchone()

        if not product_result:
            raise HTTPException(
                status_code=404, detail=f"Product with code {data.PRD_CODE} not found."
            )
        
        prd_id = product_result[0] # 商品IDを取得

        with db.begin():
            try:
                # 取引明細にデータを挿入
                detail_query = text("""
                    INSERT INTO transaction_detail_horie (TRD_ID, PRD_ID, PRD_CODE, PRD_NAME, PRD_PRICE)
                    VALUES (:TRD_ID, :PRD_ID, :PRD_CODE, :PRD_NAME, :PRD_PRICE)
                """)
                db.execute(detail_query, {
                    "TRD_ID": data.TRD_ID,
                    "PRD_ID": prd_id,
                    "PRD_CODE": data.PRD_CODE,
                    "PRD_NAME": data.PRD_NAME,
                    "PRD_PRICE": data.PRD_PRICE,
                })

                # 挿入された明細キーを取得
                last_id_query = text("SELECT LAST_INSERT_ID() AS last_id")
                last_id = db.execute(last_id_query).fetchone()["last_id"]
            
            except Exception as inner_e:
                db.rollback()  # トランザクションをロールバック
                logging.error(f"Error during transaction:  {str(inner_e)}", exc_info=True)  # 詳細なログ
                raise HTTPException(
                    status_code=500, 
                    detail=f"An unexpected error occurred: {str(inner_e)}"
                )  # 500 Internal Server Error を返す

        # 成功レスポンスデータを作成
        return TransactionDetail(
            DTL_ID=last_id,
            TRD_ID=data.TRD_ID,
            PRD_ID=prd_id,
            PRD_CODE=data.PRD_CODE,
            PRD_NAME=data.PRD_NAME,
            PRD_PRICE=data.PRD_PRICE,
        )
    except HTTPException as e:
        logging.error(f"HTTPException: {e.detail}")# 明確にHTTPExceptionが発生した場合の処理
        raise e
    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error occurred: {str(e)}", exc_info=True)  # 詳細なログ
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # 環境変数からPORTを取得（デフォルト8000）
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)

