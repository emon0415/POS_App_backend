from mymodels import Base
from connect import AzureDBConnection
from sqlalchemy import inspect


def init_db():
    # データベース接続を確立
    db_connection = AzureDBConnection()
    engine = db_connection.connect()
    
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        print("既存のテーブルを確認しています...")
        if "transaction_horie" not in existing_tables or "transaction_detail_horie" not in existing_tables:
            print("テーブルを作成しています...")
            Base.metadata.create_all(bind=engine)
            print("テーブルの作成が完了しました！")
        else:
            print("すべてのテーブルが既に存在しています。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        db_connection.close()


if __name__ == "__main__":
    init_db()
