import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

# 데이터 로드
df = pd.read_csv("dataProcessing/dataset/commentData.csv")
df["text"] = df["title"].fillna("") + " " + df["comment"].fillna("")

model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

# 임베딩 계산
print("Computing embeddings with Sentence-BERT...")
embeddings = model.encode(df["text"].tolist(), batch_size=64, show_progress_bar=True)

labels = df["judge"].values

# 저장
np.save("dataProcessing/dataset/commentData_sbert_embeddings_TitleComment.npy", embeddings)
np.save("dataProcessing/dataset/commentData_labels_TitleComment.npy", labels)

print("Saved SBERT embeddings:", embeddings.shape)
print("Saved labels:", labels.shape)
