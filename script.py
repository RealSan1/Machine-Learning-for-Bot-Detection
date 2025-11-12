import requests
import time
import json
import sys
import asyncio
from bs4 import BeautifulSoup
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

import DB

# -----------------------------
# 공통 설정
# -----------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://news.naver.com/section/100"
}

engine = DB.engine
NEWS = DB.NEWS
COMMENT = DB.COMMENT


# -----------------------------
# 1. API → HTML → 기사 목록 추출
# -----------------------------
def fetch_page(date, sid=100, page_no=1, next_cursor=""):
    url = "https://news.naver.com/section/template/SECTION_ARTICLE_LIST"
    params = {
        "sid": sid,
        "sid2": "",
        "cluid": "",
        "pageNo": page_no,
        "date": date,
        "next": next_cursor,
        "_": str(int(time.time() * 1000))
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print("API 요청 실패:", e)
        return {}


def extract_articles_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    articles = []

    for item in soup.select("li.sa_item"):
        link_tag = item.select_one("a.sa_thumb_link, a.sa_text_title")
        if not link_tag:
            continue

        url = link_tag.get("href")
        if not url or not url.startswith("http"):
            continue

        title = link_tag.get_text(strip=True)
        press_tag = item.select_one("div.sa_text_press")
        press = press_tag.get_text(strip=True) if press_tag else ""

        # URL에서 oid, aid 추출
        parts = url.split('/')
        oid = aid = ""
        for i, p in enumerate(parts):
            if p == "article" and len(parts) > i + 2:
                oid = parts[i + 1]
                aid = parts[i + 2]
                break

        if oid and aid:
            articles.append({
                "title": title,
                "url": url,
                "press": press,
                "oid": oid,
                "aid": aid
            })

    return articles


def fetch_article_urls(date, max_pages, sid=100):
    all_articles = []
    next_cursor = ""
    page_no = 1
    

    for _ in range(max_pages):
        print(f"\n[페이지 {page_no}] 수집 중... (cursor: {next_cursor[:30]}...)")
        data = fetch_page(date, sid, page_no, next_cursor)

        if not data or "renderedComponent" not in data:
            print("응답 구조 오류 또는 종료")
            break

        html_content = data["renderedComponent"].get("SECTION_ARTICLE_LIST", "")
        if not html_content:
            print("HTML 없음")
            break

        articles = extract_articles_from_html(html_content)
        print(f"  → {len(articles)}개 기사 발견")
        all_articles.extend(articles)

        # 다음 페이지 정보
        soup = BeautifulSoup(html_content, "html.parser")
        container = soup.select_one("div.section_article._TEMPLATE")
        if not container:
            break

        next_cursor = container.get("data-cursor", "")
        has_next = container.get("data-has-next") == "true"

        if not has_next or not next_cursor:
            print("더 이상 페이지 없음")
            break

        page_no += 1

    print(f"\n총 {len(all_articles)}개 기사 URL 수집 완료")
    return all_articles


# -----------------------------
# 2. 기사 본문 수집
# -----------------------------
def fetch_article_content(oid, aid, url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        title_el = soup.select_one("h2.media_end_head_headline")
        content_el = soup.select_one("#dic_area")

        if not title_el or not content_el:
            return None

        title = title_el.get_text(strip=True)
        content = content_el.get_text("\n", strip=True)

        comments, _ = fetch_comments_all(oid, aid)

        return {
            "title": title,
            "content": content,
            "url": url,
            "oid": oid,
            "aid": aid,
            "comments": comments
        }
    except Exception as e:
        print(f"본문 수집 실패 ({url}): {e}")
        return None


# -----------------------------
# 3. 댓글 전체 수집 (페이지네이션 포함)
# -----------------------------
def fetch_comments_all(oid, aid, max_pages=35):
    all_comments = []
    next_id = None
    page = 1

    while page <= max_pages:
        comments, next_id = fetch_comments(oid, aid, next_id, page)
        if not comments:
            break
        all_comments.extend(comments)
        print(f"  댓글 페이지 {page}: {len(comments)}개 (총 {len(all_comments)}개)")

        if not next_id:
            break

        page += 1
        time.sleep(0.3)

    return all_comments, None


def fetch_comments(oid, aid, next_id=None, page=1):
    api = "https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json"
    params = {
        "ticket": "news",
        "pool": "cbox5",
        "lang": "ko",
        "pageSize": "100",
        "indexSize": "10",
        "sort": "favorite",
        "objectId": f"news{oid},{aid}",
        "page": page,
        "pageType": "more",
    }
    if next_id:
        params["moreParam.next"] = next_id

    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": f"https://n.news.naver.com/mnews/article/comment/{oid}/{aid}",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        res = requests.get(api, params=params, headers=headers, timeout=10)
        text = res.text.strip()

        start = text.find("(")
        end = text.rfind(")")
        if start == -1 or end == -1:
            return [], None
        json_text = text[start + 1:end]

        data = json.loads(json_text)

        comment_list = data["result"]["commentList"]
        comments = [c["contents"] for c in comment_list if c.get("contents")]
        next_page = data["result"].get("morePage", {}).get("next")

        return comments, next_page
    except Exception as e:
        print(f"댓글 파싱 실패 (oid={oid}, aid={aid}): {e}")
        return [], None



# -----------------------------
# 4. DB 저장
# -----------------------------
def save_article_to_db(article):
    if not article or not article.get("comments"):
        print("댓글 없음 → 저장 스킵:", article.get("title", "제목 없음"))
        return

    with engine.begin() as conn:
        try:
            # 중복 체크
            existing = conn.execute(
                select(NEWS.c.Title).where(NEWS.c.Title == article["title"])
            ).first()
            if existing:
                print("이미 존재 → 스킵:", article["title"])
                return

            # 기사 저장
            result = conn.execute(
                insert(NEWS).values(
                    Title=article["title"],
                    Content=article["content"],
                )
            )
            news_id = result.inserted_primary_key[0]

            # 댓글 저장
            for cmt in article["comments"]:
                conn.execute(
                    insert(COMMENT).values(
                        newID=news_id,
                        comment=cmt,
                        judge=0
                    )
                )
            print(f"저장 완료: {article['title']} (댓글 {len(article['comments'])}개)")

        except IntegrityError as e:
            print("무결성 오류:", e)
        except Exception as e:
            print("DB 오류:", e)


# -----------------------------
# 5. 메인 실행 (비동기 + 세마포어)
# -----------------------------
async def process_article(article_info):
    data = fetch_article_content(article_info["oid"], article_info["aid"], article_info["url"])
    if data:
        save_article_to_db(data)


async def main():
    print("수집 시작")
    articles = fetch_article_urls(date="20251112", max_pages=300, sid=100)

    if not articles:
        print("수집된 기사 없음")
        return

    print(f"\n총 {len(articles)}개 기사 처리 시작...\n")

    semaphore = asyncio.Semaphore(3)

    async def sem_task(art):
        async with semaphore:
            await process_article(art)

    tasks = [sem_task(art) for art in articles]
    await asyncio.gather(*tasks)

    print("종료")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
