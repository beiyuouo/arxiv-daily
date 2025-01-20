import sqlite3

def insert_model(name, category, github_url, license, db_path="db/database.db"):
    """
    데이터 삽입 함수
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO models (name, category, github_url, license)
        VALUES (?, ?, ?, ?)
    """, (name, category, github_url, license))
    conn.commit()
    conn.close()
    print(f"모델 '{name}' 데이터가 추가되었습니다!")



def insert_hf_news(news_data, db_path="db/database.db"):
    """
    Hugging Face 소식 데이터를 데이터베이스에 삽입 또는 업데이트
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 테이블 생성
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hf_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            paper TEXT,
            github_url TEXT,
            license TEXT,
            category TEXT
        )
    """)

    # 중복 확인 및 삽입 또는 업데이트
    for news in news_data:
        print(news)
        cursor.execute("""
            SELECT id FROM hf_news WHERE title = ?
        """, (news["title"],))
        row = cursor.fetchone()

        if row:
            # 데이터 업데이트
            cursor.execute("""
                UPDATE hf_news
                SET paper = ?, github_url = ?, license = ?, category = ?
                WHERE id = ?
            """, (news["title"], news["github_url"], news["license"], news["category"], row[0]))
        else:
            # 데이터 삽입
            cursor.execute("""
                INSERT INTO hf_news (title, paper, github_url, license, category)
                VALUES (?, ?, ?, ?, ?)
            """, (news["title"], news["arxiv_links"], news["github_url"], news["license"], news["category"]))

    conn.commit()
    conn.close()





def insert_blog_news(blog_news, db_path="db/database_blog.db"):
    """
    Hugging Face 블로그 소식 데이터를 데이터베이스에 삽입
    중복된 소식은 저장하지 않음
    """
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 테이블이 존재하지 않을 경우 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hf_blog_news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        url TEXT UNIQUE NOT NULL,
        date_published TEXT,
        category TEXT
    )
    """)

    # 중복 확인 및 삽입
    new_items_count = 0
    for news in blog_news:
        print(news)  # 디버깅 출력
        
        # 기본값 설정
        description = news.get("description", "No description available")
        date_published = news.get("date_published", "Unknown date")
        category = news.get("category", "Uncategorized")

        # 중복 데이터 확인
        cursor.execute("""
            SELECT COUNT(*) FROM hf_blog_news WHERE title = ? AND url = ?
        """, (news["title"], news["url"]))
        exists = cursor.fetchone()[0]

        if not exists:  # 중복되지 않은 경우에만 삽입
            cursor.execute("""
                INSERT INTO hf_blog_news (title, description, url, date_published, category)
                VALUES (?, ?, ?, ?, ?)
            """, (news["title"], description, news["url"], date_published, category))
            new_items_count += 1

    # 변경사항 커밋 및 연결 종료
    conn.commit()
    conn.close()
    print(f"{len(blog_news)}개의 블로그 소식 중 {new_items_count}개의 새 항목이 저장되었습니다!")