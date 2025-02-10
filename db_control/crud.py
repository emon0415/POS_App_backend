from sqlalchemy.orm import sessionmaker
from sqlalchemy import insert
from db_control.mymodels import TransactionDetail
from db_control.connect import AzureDBConnection

# transaction_detail_horieテーブルに商品名と単価を挿入する関数
def add_transaction_detail(data):
    db_connection = AzureDBConnection()
    engine = db_connection.create_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        query = insert(TransactionDetail).values(data)

        with session.begin():
            session.execute(query)
        print("データが正常に挿入されました。")
    except Exception as e:
        print(f"データ挿入中にエラーが発生しました: {e}")
        session.rollback()
    finally:
        session.close()
        db_connection.close()

# テスト用に固定データで処理が正しく動作するかを確認する
if __name__ == "__main__":
    data = {
        "TRD_ID": 1,  # トランザクションID
        "PRD_ID": 101,  # 商品ID
        "PRD_CODE": "4987035535409",  # 商品コード
        "PRD_NAME": "ポカリスエット",  # 商品名
        "PRD_PRICE": 170  # 商品単価
    }
    add_transaction_detail(data)



