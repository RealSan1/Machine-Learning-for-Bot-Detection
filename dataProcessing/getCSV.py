import sys, os
import pandas as pd
from sqlalchemy import text
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import DB

engine = DB.engine

query = text("""
SELECT 
    n.Title AS title,
    n.Content AS content,
    c.comment AS comment,
    c.judge AS judge
FROM COMMENT c
JOIN NEWS n ON c.newID = n.newID;
""")

with engine.connect() as conn:
    df = pd.read_sql(query, conn)

# CSV 저장
output_path = "dataProcessing/dataset/commentData.csv"
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"CSV 추출 완료: {len(df)}건 저장됨 → {output_path}")