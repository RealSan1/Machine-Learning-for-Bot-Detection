import requests
from bs4 import BeautifulSoup
import json
import sys
import asyncio
import time
import DB  # DB.py에서 metadata, engine, NEWS, COMMENT 정의돼 있다고 가정
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

engine = DB.engine
NEWS = DB.NEWS
COMMENT = DB.COMMENT

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_LIST_URL = "https://news.naver.com/section/100"  # 정치 섹션

def fetch_article_list_multiple_pages(max_pages=1000):
    all_urls = []
    for page in range(1, max_pages + 1):
        url = f"https://news.naver.com/section/100?page={page}"
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.select("a[data-imp-url]")
        urls = [a["data-imp-url"] for a in links if a.has_attr("data-imp-url")]
        all_urls.extend(urls)
        time.sleep(1)  # 속도 제한
    return list(set(all_urls))  # 중복 제거


def fetch_article_content(article_url):
    res = requests.get(article_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    title_el = soup.select_one("h2.media_end_head_headline")
    content_el = soup.select_one("#dic_area")
    if not title_el or not content_el:
        return None

    title = title_el.get_text(strip=True)
    content = content_el.get_text("\n", strip=True)

    oid, aid = extract_ids_from_url(article_url)
    comments, _ = fetch_comments(oid, aid)

    return {
        "url": article_url,
        "title": title,
        "content": content,
        "comments": comments
    }

def extract_ids_from_url(url):
    parts = url.split("/")
    oid = parts[-2]
    aid = parts[-1]
    return oid, aid

def fetch_comments(oid, aid, next_id=None, page=1):
    api = "https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json"
    params = {
        "ticket": "news",
        "pool": "cbox5",
        "lang": "ko",
        "pageSize": "20",
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
        "Referer": f"https://news.naver.com/main/read.nhn?oid={oid}&aid={aid}",
        "X-Requested-With": "XMLHttpRequest",
    }

    res = requests.get(api, params=params, headers=headers)
    text = res.text

    try:
        text = text[text.index("(") + 1:text.rindex(")")]
        data = json.loads(text)

        comments = [item["contents"] for item in data["result"]["commentList"]]
        next_page_id = data["result"].get("morePage", {}).get("next")

        return comments, next_page_id
    except Exception as e:
        print("댓글 파싱 실패:", e)
        return [], None

def save_article_to_db(article):
    if not article.get("comments"):
        print("댓글 없음, 저장하지 않음:", article["title"])
        return

    with engine.connect() as conn:
        try:
            # 중복 URL 체크
            existing = conn.execute(
                NEWS.select().where(NEWS.c.Title == article["title"])
            ).fetchone()

            if existing:
                print("이미 저장된 기사:", article["title"])
                return

            # 뉴스 저장
            result = conn.execute(
                insert(NEWS).values(
                    Title=article["title"],
                    Content=article["content"]
                )
            )
            news_id = result.inserted_primary_key[0]

            # 댓글 저장
            for cmt in article["comments"]:
                conn.execute(
                    insert(COMMENT).values(
                        newID=news_id,
                        comment=cmt,
                        judge=None
                    )
                )
            conn.commit()
            print("저장 완료:", article["title"])

        except IntegrityError as e:
            print("DB 저장 오류:", e)

async def main():
    article_urls = fetch_article_list_multiple_pages()
    print(f"기사 수집 대상: {len(article_urls)}개")

    for url in article_urls:
        data = fetch_article_content(url)
        if data is None:
            continue
        save_article_to_db(data)
        time.sleep(1)  # 속도 제한

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
