from sqlalchemy import create_engine
import os
import tempfile
from dotenv import load_dotenv
import urllib.parse

# 環境変数をロード
load_dotenv()

# 環境変数の確認　デプロイ時は削除する事。
print("DB_USER:", os.getenv("DB_USER"))
print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))
print("DB_HOST:", os.getenv("DB_HOST"))
print("DB_PORT:", os.getenv("DB_PORT"))
print("DB_NAME:", os.getenv("DB_NAME"))
print("SSL_CA_CERT:", os.getenv("SSL_CA_CERT"))

# データベース接続情報
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = urllib.parse.quote_plus(os.getenv('DB_PASSWORD')) # DBパスワードに@が入るとエラーとなるためエンコードする
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

# MySQLのURL構築
if not DB_USER or not DB_PASSWORD or not DB_HOST or not DB_PORT or not DB_NAME:
    raise ValueError(
        "DATABASE_URL could not be constructed. Please check your .env file and ensure all required variables (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME) are set."
    )

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print("Constructed DATABASE_URL:", DATABASE_URL) # デプロイ時は削除すること

class AzureDBConnection:
    def __init__(self):
        self.database_url = DATABASE_URL
        self.pem_content = os.getenv("SSL_CA_CERT")
        self.engine = None
        self.ssl_cert_path = None

    def _get_ssl_cert_path(self): #環境変数内のSSL証明書内容を整形し、一時ファイルとして保存。
        if self.pem_content is None or self.pem_content.strip() == '':
            raise ValueError(
                "SSL_CA_CERT is not set or is empty in enviroment variables."
                "Ensure the SSL_CA_CERT variable is correctly configured in your .env file."
            )

        # 証明書内容の整形
        pem_content = self.pem_content.replace("\\n","\n").replace("\r", "")

        # デバッグ用に証明書を書き出し（本番では削除）
        with open("output_certificate.pem", "w") as f:
            f.write(pem_content)
        print("SSL証明書を output_certificate.pem に保存しました")
        
        try:
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix="pem") as temp_pem:
                temp_pem.write(pem_content)
                self.ssl_cert_path = temp_pem.name
                print(f"SSL certificate saved to: {self.ssl_cert_path}")
            return self.ssl_cert_path
        except Exception as e:
            raise RuntimeError(f"Failed to save SSL certificate to temporary file: {e}")
        
    def connect(self): #データベース接続を初期化し、接続オブジェクトを返す。
        print("===> Connecting to AzureDB ===")
        if not self.database_url:
            raise ValueError("DATABASE_URL is not set in environment variables.")
        
        try:
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
            print("Database connection established successfully.")
            return self.engine.connect()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to database: {e}")
    
    def close(self): #エンジンをクローズ。
        if self.engine:
            self.engine.dispose()
            print("Database connection closed")
        if self.ssl_cert_path and os.path.exists(self.ssl_cert_path):
            try:
                os.remove(self.ssl_cert_path)
                print("Temporary SSL certificate file removed")
            except Exception as e:
                print(f"Failed to remove temporary SSL certificate file: {e}")
