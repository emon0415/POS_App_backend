from sqlalchemy import create_engine
import os
import tempfile
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()

class AzureDBConnection:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.pem_content = os.getenv("SSL_CA_CERT")
        self.engine = None

    def _get_ssl_cert_path(self): #環境変数内のSSL証明書内容を整形し、一時ファイルとして保存。
        if self.pem_content is None or self.pem_content.strip() == '':
            raise ValueError("SSL_CA_CERT is not set or is empty in enviroment variables.")

        # 証明書内容の整形
        pem_content = self.pem_content.replace("\\n","\n").replace("\r", "")

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(model="w", delete=False, suffix="pem") as temp_pem:
            temp_pem.write(pem_content)
            return temp_pem.name
        
    def connect(self): #データベース接続を初期化し、接続オブジェクトを返す。
        print("===> Connecting to AzureDB ===")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not set in environment variables.")
        
        # SSL証明書のパスを取得して接続
        ssl_cert_path = self._get_ssl_cert_path()
        self.engine = create_engine(
            self.database_url,
            connect_args={
                "ssl": {
                    "ca": ssl_cert_path
                }
            }
        )
        return self.engine.connect()
    
    def close(self): #エンジンをクローズ。
        if self.engine:
            self.engine.dispose()
            print("Database connection closed")
