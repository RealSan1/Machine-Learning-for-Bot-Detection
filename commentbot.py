import ollama
from sqlalchemy import select, insert
import DB

engine = DB.engine
NEWS = DB.NEWS
COMMENT = DB.COMMENT

def generate_comment_with_ollama(article):
    if not article.get("title") or not article.get("content"):
        return None

    prompt = f"""
        다음 기사 제목과 본문을 참고하여 자연스럽고 공감 가는 댓글을 4개 작성, 댓글의 길이는 최대 100 최소 40 길이로 다양하게 작성, 특수기호 사용 금지.

    제목: {article['title']}
    본문: {article['content']}
    """

    try:
        response = ollama.chat(
            model="gpt-oss:20b",
            messages=[{"role": "user", "content": prompt}],
        )

        if "message" in response:
            output_text = response["message"].get("content", "").strip()
        elif "messages" in response and len(response["messages"]) > 0:
            output_text = response["messages"][-1].get("content", "").strip()
        else:
            output_text = str(response).strip()

        print(f"[Ollama 댓글 생성] 기사 ID {article.get('id', 'N/A')} | 댓글 시작: {output_text[:100]}...")
        return output_text

    except Exception as e:
        print(f"[Ollama 오류] 기사 ID {article.get('id', 'N/A')} | 오류: {e}")
        return None


import re

def generate_and_save_comments():
    with engine.begin() as conn:
        result = conn.execute(select(NEWS.c.newID, NEWS.c.Title, NEWS.c.Content))
        articles = result.all()

    for art in articles:
        article = {
            "id": art.newID,
            "title": art.Title,
            "content": art.Content
        }
        comments_text = generate_comment_with_ollama(article)
        if comments_text:
            # 줄바꿈으로 분리 후 번호 제거
            lines = comments_text.split('\n')
            comments = []
            for line in lines:
                # '1. ', '2) ', '3 -' 등 번호 제거
                cleaned = re.sub(r'^\s*\d+[\.\)\-\s]*', '', line).strip()
                if cleaned:
                    comments.append(cleaned)
            comments = comments[:4]

            with engine.begin() as conn:
                for comment in comments:
                    conn.execute(
                        insert(COMMENT).values(
                            newID=article["id"],
                            comment=comment,
                            judge=1
                        )
                    )
            print(f"댓글 저장 완료: 기사 ID {article['id']}")


if __name__ == "__main__":
    generate_and_save_comments()
