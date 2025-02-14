from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from dotenv import load_dotenv
from db_control.connect import AzureDBConnection # connect.pyのインポート
import logging
import uvicorn
import os
from pydantic import BaseModel
from db_control.schemas import Product, ProductCreate, Transaction, TransactionCreate, TransactionDetail, TransactionDetailCreate, TransactionWithDetails, AddTransactionRequest
from datetime import datetime
from db_control import mymodels, schemas, crud, connect
import json
import pytz
from typing import List, Union


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

origins = [
    "https://tech0-gen8-step4-pos-app-43.azurewebsites.net",  # フロントエンドのURL
    "http://localhost:3000",  # 開発用
]

# CORS設定
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


# 商品コード(code)で商品マスタ(m_product_horie)を検索し、該当商品を返す。見つからなければ404エラー
@app.get("/products/{code}", response_model=schemas.Product)
async def get_product_by_code(code:str, db = Depends(get_db)):

    product = db.query(mymodels.Product).filter(mymodels.Product.CODE == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# 取引テーブルへの登録
@app.post("/add_transaction", response_model=schemas.AddTransactionRequest)
async def add_transaction(data: schemas.AddTransactionRequest, db=Depends(get_db)):

    try:
        # 現在の日時を取得（バックエンド側で処理）
        transaction_datetime = datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")

        with db.begin():
            # 新規取引を挿入
            transaction_query = text("""
                INSERT INTO transaction_horie (DATETIME, EMP_CD, STORE_CD, POS_NO, TOTAL_AMT)
                VALUES (:DATETIME, :EMP_CD, :STORE_CD, :POS_NO, :TOTAL_AMT)
            """)
            db.execute(transaction_query, {
                "DATETIME": transaction_datetime,
                "EMP_CD": data.EMP_CD,
                "STORE_CD": data.STORE_CD,
                "POS_NO": data.POS_NO,
                "TOTAL_AMT": data.TOTAL_AMT,
            })

            # 挿入された取引IDを取得。フロントエンドに返すため。
            last_id_query = text("SELECT LAST_INSERT_ID()")
            last_id = db.execute(last_id_query).fetchone()[0]

        # 成功レスポンスデータを作成
        return {
            "message": "Transaction added successfully",
            "TRD_ID": last_id,
            "DATETIME":transaction_datetime,
            "EMP_CD":data.EMP_CD,
            "STORE_CD":data.STORE_CD,
            "POS_NO":data.POS_NO,
            "TOTAL_AMT":data.TOTAL_AMT,
        }
    except IntegrityError as e:
        db.rollback()
        logging.error(f"IntegrityError (外部キー・ユニーク制約違反): {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"データ整合性エラー: {str(e)}")

    except OperationalError as e:
        db.rollback()
        logging.error(f"OperationalError (データベース接続エラー): {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="データベース接続エラーが発生しました。管理者に連絡してください。")

    except DataError as e:
        db.rollback()
        logging.error(f"DataError (データ型エラー): {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"無効なデータが入力されました: {str(e)}")

    except ValueError as e:
        db.rollback()
        logging.error(f"ValueError (バリデーションエラー): {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"入力データの形式が正しくありません: {str(e)}")

    except TypeError as e:
        db.rollback()
        logging.error(f"TypeError (型エラー): {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"データ型が正しくありません: {str(e)}")

    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="予期しないエラーが発生しました。管理者に連絡してください。")



# データ検証用モデル
class TransactionDetailData(BaseModel):
    TRD_ID: int # トランザクションID
    PRD_CODE: str # 商品コード
    PRD_NAME: str # 商品名
    PRD_PRICE: int # 商品単価

@app.post("/add_transaction-detail", response_model=List[schemas.TransactionDetail])
async def add_transaction_detail(
    data: Union[schemas.TransactionDetailData, List[schemas.TransactionDetailData]],  # 複数の明細データを受け取る
    db: Session = Depends(get_db)
):
    print("Received request data:", data)  # 受け取ったデータをログに出力
    if not isinstance(data, list):  # 単数データの場合、リストに変換
        data = [data]

    try:
        inserted_details = [] # 登録した取引明細を保存するリスト

        for item in data:
            print(f"Processing item: TRD_ID={item.TRD_ID}, PRD_CODE={item.PRD_CODE}")  # デバッグ情報

            # 取引が存在するか確認
            transaction = db.query(mymodels.Transaction).filter_by(TRD_ID=item.TRD_ID).first()
            if not transaction:
                logging.error(f"Transaction ID {item.TRD_ID} not found in transaction_horie table.")
                raise HTTPException(status_code=404, detail=f"Transaction ID {item.TRD_ID} not found.")

            # m_product_horieにPRD_CODEがあるか確認
            product = db.query(mymodels.Product).filter_by(CODE=item.PRD_CODE).first()
            if not product:
                logging.warning(f"Product with code {item.PRD_CODE} not found in m_product_horie table.")
                raise HTTPException(status_code=404, detail=f"Product with code {item.PRD_CODE} not found.")

            # 取引明細にデータを挿入（DTL_IDは auto_increment のため指定しない）
            new_detail = mymodels.TransactionDetail(
                TRD_ID=item.TRD_ID,
                PRD_ID=product.PRD_ID,
                PRD_CODE=product.CODE,
                PRD_NAME=item.PRD_NAME,
                PRD_PRICE=item.PRD_PRICE,
            )
            db.add(new_detail)

            # 合計金額を更新（単純加算）
            transaction.TOTAL_AMT += item.PRD_PRICE

            inserted_details.append(new_detail)

        # データベースにコミット
        db.commit()

        # 最新データを取得
        for detail in inserted_details:
            db.refresh(detail) # 挿入されたデータを最新の状態に更新

        return inserted_details

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Data integrity error occurred.")

    except OperationalError:
        db.rollback()
        print(f"OperationalError: {str(e)}")  # デバッグ用にログ出力
        raise HTTPException(status_code=500, detail="Database operation error occurred.")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # 環境変数からPORTを取得（デフォルト8000）
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)

