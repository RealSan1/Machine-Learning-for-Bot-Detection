# 뉴스 댓글 생성 및 진위 판별 모델 연구 프로젝트

## 개요
본 프로젝트는 네이버 뉴스 댓글 데이터를 기반으로, **댓글이 인간이 작성한 것인지 혹은 자동 생성된 것인지 판별하는 머신러닝 모델을 개발**하는 것을 목표로 한다.  
이를 위해 **실제 기사 기반으로 생성된 댓글(봇 데이터)** 과 **실제 사용자가 작성한 댓글(휴먼 데이터)** 를 모두 확보하여 비교/분류 학습에 사용한다.

---

## 전체 데이터 파이프라인 구성

### 1. 뉴스 데이터 수집
- 네이버 뉴스 섹션에서 기사 URL 수집
- 기사 페이지에서 **제목(Title), 본문(Content)** 크롤링
- 크롤링된 데이터는 MySQL `NEWS` 테이블에 저장

**NEWS 테이블 구조**
| Column | Type     | Description     |
|--------|----------|-----------------|
| newID  | INT PK   | 뉴스 식별 ID    |
| Title  | LONGTEXT | 기사 제목        |
| Content| LONGTEXT | 기사 본문 내용    |

---

### 2. 실 사용자 댓글 데이터 수집
- 네이버 공식 댓글 API(`cbox`)를 사용하여 댓글 데이터 수집
- 여러 페이지 댓글은 `moreParam.next` 파라미터를 활용하여 순차적으로 로딩
- 수집한 데이터는 `COMMENT` 테이블에 저장

**COMMENT 테이블 구조**
| Column    | Type     | Description                                   |
|-----------|----------|-----------------------------------------------|
| commentID | INT PK   | 댓글 식별 ID                                   |
| newID     | INT FK   | 연결된 뉴스 ID                                 |
| comment   | LONGTEXT | 댓글 내용                                      |
| judge     | INT      | 분류 상태 (0 = 실제댓글, 1 = 생성댓글)          |

---

### 3. 모델 기반 댓글 생성 (봇 댓글)
봇 댓글 생성에는 **Ollama 로컬 LLM 모델 `gpt-oss:20b`** 를 사용한다.  
뉴스 기사 **제목 + 본문** 을 입력하여 **자연스러운 한국어 댓글 4개를 생성**한다.

### 4. 실행 흐름 (의사 코드)

```python
#### 댓글 생성 코드
import ollama

def generate_comment(article):
    prompt = f"""
    다음 기사 제목과 본문을 참고하여 자연스럽고 공감 가능한 댓글을 4개 작성,
    댓글의 길이는 최대 100 최소 40 길이로 다양하게 작성, 특수기호 사용 금지.

    제목: {article['title']}
    본문: {article['content']}
    """
    response = ollama.chat(
        model="gpt-oss:20b",
        messages=[{"role":"user","content":prompt}]
    )
    return response["message"]["content"].strip()
```


