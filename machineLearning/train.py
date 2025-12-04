import torch
import torch.nn as nn
import torch.optim as optim

from model import MyModel
from utils import load_data, split_data, find_optimal_threshold, evaluate_model, plot_loss_history, CommentPredictor
from trainer import Trainer

if __name__ == "__main__":
    # 데이터 경로 (본인 환경에 맞게 수정)
    DATA_PATH = "dataProcessing\dataset\commentData_sbert_embeddings.npy"
    LABEL_PATH = "dataProcessing\dataset\commentData_labels.npy"
    
    x, y = load_data(DATA_PATH, LABEL_PATH)
    x_train, x_valid, x_test, y_train, y_valid, y_test = split_data(x, y)
    
    print(f"Train/Valid/Test: {len(x_train)} / {len(x_valid)} / {len(x_test)}")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MyModel(input_dim=x_train.size(1)).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0)
    
    trainer = Trainer(model, criterion, optimizer, device=device)
    
    trainer.fit(
        x_train, y_train, x_valid, y_valid,
        n_epochs=200,
        batch_size=512,
        early_stop_patience=20,
        print_every=10
    )
    
    # Loss 그래프
    plot_loss_history(trainer.train_losses, trainer.valid_losses)
    
    # 최적 threshold 찾기
    with torch.no_grad():
        val_logits = model(x_valid.to(device))
        val_probs = torch.sigmoid(val_logits).cpu().numpy()
    best_thresh, best_f1 = find_optimal_threshold(y_valid.numpy().ravel(), val_probs.ravel())
    print(f"Optimal threshold: {best_thresh:.3f} (F1={best_f1:.4f})")
    
    # 테스트 성능
    metrics, test_probs, test_true = evaluate_model(model, x_test.to(device), y_test, best_thresh)
    print("\n=== Final Test Performance ===")
    for k, v in metrics.items():
        print(f"{k.capitalize():9}: {v:.4f}")
    
    # 모델 저장
    torch.save(model.state_dict(), "comment_classifier.pth")
    print("\n모델 저장 완료 → comment_classifier.pth")
    
    # 예측기 테스트
    predictor = CommentPredictor(model_path="comment_classifier.pth", threshold=best_thresh)
    
    test_comments = [
        "특검에만 의존 말고 독자 조사도 해야 공무원들이 사회적 책임을 명확히 이행하고 있는지 확인하는 것이 우리 모두의 권리이며 이는 국가의 신뢰와 직결되기 때문에 매우 중요합니다",
        "국짐은 정말....헌법 명시된 일자를 시간으로 바꿔 써결이 풀어줬고 즉시 항소포기를 눈감고 모른체 했던 내란세력이.....하늘을 손가리고 아웅해도 유분수지!! 개돼지 노인들과 개독교, 사이비 질질끌고 근근히 살아가는 국짐은 해체가 답이다!!",
        "軍, 남북군사회담 제안…'군사분계선 기준선 설정 논의' 찢재명 대통령 되니까 아예 북한에다가 남한 땅 주려고 난리네. 정은이가 시키드나!! ㅋㅋㅋㅋㅋ",
    ]
    
    print("\n" + "="*60)
    print("봇 탐지기 실시간 테스트")
    print("="*60)
    for comment in test_comments:
        result = predictor.predict(comment)
        print(f"입력: {result['text'][:60]}...")
        print(f"예측: {result['prediction']} (확률: {result['probability']})")
        print("-" * 60)