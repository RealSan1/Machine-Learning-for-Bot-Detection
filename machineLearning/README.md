# Machine Learning for Bot Detection

댓글(봇 / 인간) 탐지 모델입니다.  
한국어 SBERT 임베딩 + 간단한 MLP로 이진 분류 수행

**성능 (Test Set 기준)**  
> Accuracy: 0.9864 | Precision: 0.9931 | Recall: 0.9795 | **F1: 0.9862** | **AUC: 0.9994**

## Requirements
- Python 3.10 이상 (Google Colab 기준)

### 패키지 설치
```python
pip install -r requirements.txt
```

## 데이터 준비
- [commentData_sbert_embeddings.npy](https://github.com/RealSan1/Machine-Learning-for-Bot-Detection/blob/main/dataProcessing/dataset/commentData_sbert_embeddings.npy)
- [commentData_labels.npy](https://github.com/RealSan1/Machine-Learning-for-Bot-Detection/blob/main/dataProcessing/dataset/commentData_labels.npy)

 > 두 파일을 프로젝트 루트(machineLearning/)에 위치시키거나,
train.py 내의 경로를 본인 환경에 맞게 수정하세요.

## 학습 실행
```python
python train.py
```

## 예측 테스트 (학습 완료 후)
```python
predictor = CommentPredictor("comment_classifier.pth", threshold=0.52)

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

============================================================
봇 탐지기 실시간 테스트
============================================================
입력: 특검에만 의존 말고 독자 조사도 해야 공무원들이 사회적 책임을 명확히 이행하고 있는지 확인하는 것이 우리 모...
예측: 봇 (확률: 1.0)
------------------------------------------------------------
입력: 국짐은 정말....헌법 명시된 일자를 시간으로 바꿔 써결이 풀어줬고 즉시 항소포기를 눈감고 모른체 했던 내란...
예측: 인간 (확률: 0.0009)
------------------------------------------------------------
입력: 軍, 남북군사회담 제안…'군사분계선 기준선 설정 논의' 찢재명 대통령 되니까 아예 북한에다가 남한 땅 주려고...
예측: 인간 (확률: 0.001)
------------------------------------------------------------
```

## 모델 구조
- `model.py`      : MyModel 정의
- `trainer.py`    : 학습 루프 + Early Stopping
- `utils.py`      : 데이터 로딩, 평가, 예측 클래스
- `train.py`      : 전체 학습 파이프라인 (메인)

## 학습된 모델
- `comment_classifier.pth` : 최적 threshold 기준으로 저장된 모델
