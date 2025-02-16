from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, TIMESTAMP, DECIMAL
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

# 商品マスタ
class Product(Base):
    __tablename__ = "m_product_horie"
    PRD_ID = Column(Integer, primary_key=True)
    CODE = Column(String(13), unique=True, index = True, nullable=False)
    NAME = Column(String(50), nullable=False)
    PRICE = Column(Integer, nullable=False)

    # リレーションを定義する
    transaction_details = relationship("TransactionDetail", back_populates="product")

# 取引
class Transaction(Base):
    __tablename__ = "transaction_horie"
    TRD_ID = Column(Integer, primary_key=True, autoincrement=True, comment="Primary Key")
    DATETIME = Column(TIMESTAMP, server_default=func.current_timestamp(), comment="TRANSACTION_DATETIME")
    EMP_CD = Column(String(10), nullable=False, comment="レジ担当")
    STORE_CD = Column(String(5), nullable=False, comment="store code")
    POS_NO = Column(String(3), nullable=False, comment="POS機ID")
    TOTAL_AMT = Column(Integer, comment="total price")
    TTL_AMT_EX_TAX = Column(Integer, nullable=False, comment="合計金額（税抜き）")

    # リレーションを定義する
    transaction_details = relationship("TransactionDetail", back_populates="transaction")

# 取引明細
class TransactionDetail(Base):
    __tablename__ = "transaction_detail_horie"
    TRD_ID = Column(Integer, ForeignKey("transaction_horie.TRD_ID"), nullable=False, comment="取引キー")
    DTL_ID = Column(Integer, primary_key=True, autoincrement=True, comment="取引明細キー")
    PRD_ID = Column(Integer, ForeignKey("m_product_horie.PRD_ID"), nullable=False, comment="商品キー")
    PRD_CODE = Column(String(13), nullable=False, comment="商品コード")
    PRD_NAME = Column(String(50), nullable=False, comment="商品名")
    PRD_PRICE = Column(Integer, nullable=False, comment="商品単価")
    TAX_CD = Column(String(2),nullable=False, comment="消費税区分")

    # リレーションを定義する
    product = relationship("Product", back_populates="transaction_details")
    transaction = relationship("Transaction", back_populates="transaction_details")

# 税マスタ
class Tax(Base):
    __tablename__ = "tax_horie"
    ID = Column(Integer, primary_key=True, nullable=False, comment="Primary Key")
    CODE = Column(String(2), unique=True, nullable=False, comment="税率コード")
    NAME = Column(String(20), nullable=False, comment="税率名称")
    PERCENT = Column(DECIMAL(5,2), nullable=False, comment="税率(%)")
