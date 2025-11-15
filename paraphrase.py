import ollama
import DB, time, os
from sqlalchemy import select, insert, and_, func
from google import genai
from dotenv import load_dotenv
engine = DB.engine
COMMENT = DB.COMMENT
load_dotenv("api.env")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def paraphrase_comment_with_ollama(comment_text):
    prompt = f"""
    다음 댓글을 자연스럽게 바꾸되, 의미는 유지하고, 출력은 한 문장으로만 작성하세요.
    특수기호 사용 금지:
    댓글: {comment_text}
    """
    try:
        response = ollama.chat(
            model="gpt-oss:20b",
            messages=[{"role": "user", "content": prompt}],
        )

        if "message" in response:
            paraphrased = response["message"].get("content", "").strip()
        elif "messages" in response and len(response["messages"]) > 0:
            paraphrased = response["messages"][-1].get("content", "").strip()
        else:
            paraphrased = str(response).strip()

        return paraphrased
    except Exception as e:
        print(f"[Ollama 오류] 패러프레이징 실패: {e}")
        return None

def paraphrase_comment_with_gemini(comment_text):
    prompt = f"""
    다음 댓글을 자연스럽게 바꾸되, 의미는 유지하고, 출력은 한 문장으로만 작성하세요.
    특수기호 사용 금지:
    댓글: {comment_text}
    """
    try:
        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        time.sleep(4) # 쌀먹 시간제한

        if response.candidates:
            cand = response.candidates[0]
            if cand.content and cand.content.parts:
                return cand.content.parts[0].text.strip()

        # 혹시 대비
        return None

    except Exception as e:
        print(f"[Ollama 오류] 패러프레이징 실패: {e}")
        return None
    

def paraphrase_and_insert_comments():
    with engine.begin() as conn:
        result = conn.execute(
            select(COMMENT.c.commentID, COMMENT.c.newID, COMMENT.c.comment).where(COMMENT.c.judge == 1))
        comments = result.all()

    for row in comments:
        comment_id = row.commentID
        new_id = row.newID
        original_comment = row.comment

        paraphrased = paraphrase_comment_with_gemini(original_comment)
        if paraphrased:
            print(f"\n[원본 댓글]\n{original_comment}\n")
            print(f"[패러프레이징된 댓글]\n{paraphrased}\n")

            with engine.begin() as conn:
                conn.execute(
                    insert(COMMENT).values(
                        newID=new_id,
                        comment=paraphrased,
                        judge=1
                    )
                )
            print(f"기사 ID {new_id} 댓글 패러프레이징 후 신규 저장 완료 (원본 commentID: {comment_id})")

if __name__ == "__main__":
    paraphrase_and_insert_comments()