from sqlalchemy import create_engine, MetaData, Table, Column, Integer, ForeignKey
from sqlalchemy.dialects.mysql import LONGTEXT

DB_USER = "root"
DB_PASS = "rootpw"
DB_HOST = "127.0.0.1"
DB_NAME = "news"


engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4",
    echo=False
)

metadata = MetaData()

# -------------------------
# 테이블 정의
# -------------------------

NEWS = Table(
    "NEWS", metadata,
    Column("newID", Integer, primary_key=True),
    Column("Title", LONGTEXT),
    Column("Content", LONGTEXT)
)

COMMENT = Table(
    "COMMENT", metadata,
    Column("commentID", Integer, primary_key=True, autoincrement=True),
    Column("newID", Integer, ForeignKey("news.newID", onupdate="CASCADE", ondelete="CASCADE")),
    Column("comment", LONGTEXT),
    Column("judge", Integer)
)
