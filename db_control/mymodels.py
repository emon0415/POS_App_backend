from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "m_product_horie"
    id = Column(Integer, primary_key=True)
    code = Column(String(13), unique=True, index = True, nullable=False)
    name = Column(String(50), nullable=False)
    price = Column(Integer, nullable=False)


class Transaction(Base):
    __tablename__ = "transaction_horie"
    TRD_id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary Key")
    TRANSACTION_DATETIME = Column(TIMESTAMP, server_default=func.current_timestamp(), comment="TRANSACTION_DATETIME")
    EMP_CD = Column(String(10), nullable=False, comment="レジ担当")
    STORE_CD = Column(String(5), nullable=False, comment="store code")
    POS_NO = Column(String(3), nullable=False, comment="POS機ID")
    TOTAL_AMT = Column(Integer, comment="total price")


class TransactionDetail(Base):
    __tablename__ = "transaction_detail_horie"
    TRD_ID = Column(Integer, nullable=False, comment="取引キー")
    DTL_ID = Column(Integer, primary_key=True, autoincrement=True, comment="取引明細キー")
    PRD_ID = Column(Integer, nullable=False, comment="商品キー")
    PRD_CODE = Column(String(13), nullable=False, comment="商品コード")
    PRD_NAME = Column(String(50), nullable=False, comment="商品名")
    PRD_PRICE = Column(Integer, nullable=False, comment="商品単価")

