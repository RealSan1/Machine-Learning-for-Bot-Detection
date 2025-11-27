import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt

def load_data(data_path: str, label_path: str):
    x = torch.from_numpy(np.load(data_path))
    y = torch.from_numpy(np.load(label_path)).unsqueeze(1).float()
    return x, y

def split_data(x, y, test_size=0.15, valid_size=0.5, random_state=42):
    from sklearn.model_selection import train_test_split
    
    x_np = x.numpy()
    y_np = y.numpy().ravel()
    
    x_train_np, x_temp_np, y_train_np, y_temp_np = train_test_split(
        x_np, y_np, test_size=test_size, stratify=y_np, random_state=random_state
    )
    x_valid_np, x_test_np, y_valid_np, y_test_np = train_test_split(
        x_temp_np, y_temp_np, test_size=valid_size, stratify=y_temp_np, random_state=random_state
    )
    
    # 다시 torch tensor로
    x_train = torch.tensor(x_train_np, dtype=torch.float32)
    x_valid = torch.tensor(x_valid_np, dtype=torch.float32)
    x_test  = torch.tensor(x_test_np,  dtype=torch.float32)
    
    y_train = torch.tensor(y_train_np, dtype=torch.float32).view(-1, 1)
    y_valid = torch.tensor(y_valid_np, dtype=torch.float32).view(-1, 1)
    y_test  = torch.tensor(y_test_np,  dtype=torch.float32).view(-1, 1)
    
    return x_train, x_valid, x_test, y_train, y_valid, y_test

def find_optimal_threshold(y_true, y_prob):
    from sklearn.metrics import f1_score
    thresholds = np.linspace(0.01, 0.99, 99)
    best_f1 = 0
    best_thresh = 0.5
    for t in thresholds:
        y_pred = (y_prob > t).astype(int)
        f1 = f1_score(y_true, y_pred)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t
    return best_thresh, best_f1

def evaluate_model(model, x_test, y_test, threshold):
    model.eval()
    with torch.no_grad():
        logits = model(x_test)
        probs = torch.sigmoid(logits).numpy()
        preds = (probs > threshold).astype(int)
        y_true = y_test.numpy().ravel()
        
    metrics = {
        'accuracy': accuracy_score(y_true, preds),
        'precision': precision_score(y_true, preds),
        'recall': recall_score(y_true, preds),
        'f1': f1_score(y_true, preds),
        'auc': roc_auc_score(y_true, probs.ravel())
    }
    return metrics, probs, y_true

def plot_loss_history(train_losses, valid_losses):
    plt.figure(figsize=(12,6))
    plt.plot(train_losses, label='Train Loss')
    plt.plot(valid_losses, label='Valid Loss')
    plt.yscale('log')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Train / Valid Loss History')
    plt.grid(True)
    plt.legend()
    plt.show()

# 예측용 (배포용)
class CommentPredictor:
    def __init__(self, model_path='comment_classifier.pth', sbert_model_name='snunlp/KR-SBERT-V40K-klueNLI-augSTS', threshold=0.5):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        from model import MyModel
        embedding_dim = 768  # KR-SBERT 출력 차원
        self.model = MyModel(input_dim=embedding_dim)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        
        self.sbert = SentenceTransformer(sbert_model_name)
        self.threshold = threshold
    
    def predict(self, text: str):
        embedding = self.sbert.encode(text, convert_to_tensor=True).to(self.device)
        x = embedding.unsqueeze(0)
        
        with torch.no_grad():
            logit = self.model(x)
            prob = torch.sigmoid(logit).item()
        
        label = 1 if prob >= self.threshold else 0
        label_str = "봇" if label == 1 else "인간"
        
        return {
            "text": text,
            "probability": round(prob, 4),
            "prediction": label_str,
            "is_malicious": label
        }