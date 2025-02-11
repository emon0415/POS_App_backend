from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

## ============== 商品マスタ ==============
class ProductBase(BaseModel):
    CODE: str
    NAME: str
    PRICE: int

class ProductCreate(ProductBase):
    PRD_ID: int  # 主キー指定

class Product(ProductCreate):
    class Config:
        orm_mode = True  # SQLAlchemyモデルを返すときに必要

## ============== 取引テーブル ==============
class TransactionBase(BaseModel):
    EMP_CD: str
    STORE_CD: str
    POS_NO: str
    TOTAL_AMT: int

# リクエスト専用クラス
class AddTransactionRequest(BaseModel):
    EMP_CD: str
    STORE_CD: str
    POS_NO: str
    TOTAL_AMT: int
class TransactionCreate(TransactionBase):
    pass

# レスポンス用: DBから返すときはTRD_IDが含まれる
class Transaction(TransactionBase):
    TRD_ID: int

    class Config:
        orm_mode = True

## ============== 取引明細テーブル ==============
class TransactionDetailBase(BaseModel):
    DTL_ID: int
    PRD_ID: int
    PRD_CODE: str
    PRD_NAME: str
    PRD_PRICE: int

class TransactionDetailCreate(TransactionDetailBase):
    TRD_ID: int

class TransactionDetail(TransactionDetailCreate):
    class Config:
        orm_mode = True

## ============== 取引と明細をまとめて表示 ==============
class TransactionWithDetails(Transaction):
    details: List[TransactionDetail] = []