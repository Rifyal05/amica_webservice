import os
import re
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    raise ValueError("DATABASE_URL tidak ditemukan di .env")

engine = create_engine(DB_URL)

def clean_text(text):
    if not text: return ""
    text = text.replace('\xa0', ' ').replace('\t', ' ')
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def export_final_jsonl():
    print("Mengexport dataset final untuk RAG...")
    
    separators = [
        r"\n\n",             # 1. Paragraf
        r"\n(?=\d+\.)",      # 2. List Angka 
        r"\n(?=[A-Z]\.)",    # 3. List Huruf 
        r"\n(?=\-)",         # 4. Bullet Dash
        r"\n",               # 5. Baris baru
        r"(?<=\.) ",         # 6. Kalimat 
        " ",                 # 7. Kata
        ""                   # 8. Karakter
    ]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        separators=separators,
        is_separator_regex=True
    )

    output_file = "dataset_rag_final.jsonl"

    with engine.connect() as conn:
        query = text("SELECT id, title, content, source_url, category FROM articles WHERE content IS NOT NULL")
        result = conn.execute(query)
        
        count = 0
        skipped = 0
        
        with open(output_file, "w", encoding="utf-8") as f:
            for article in result:
                clean_content = clean_text(article.content)
                chunks = text_splitter.split_text(clean_content)
                
                for i, chunk_text in enumerate(chunks):
                    if len(chunk_text) < 50: 
                        skipped += 1
                        continue
                    augmented_content = (
                        f"Topik Artikel: {article.title}\n"
                        f"Kategori: {article.category}\n\n"
                        f"{chunk_text}"
                    )
                    
                    chunk_obj = {
                        "page_content": augmented_content, 
                        "metadata": {
                            "article_id": article.id,
                            "title": article.title,
                            "source_url": article.source_url or "",
                            "original_text": chunk_text,
                            "chunk_index": i
                        }
                    }   

                    f.write(json.dumps(chunk_obj, ensure_ascii=False) + "\n")
                    count += 1

    print(f"Selesai! {count} chunks tersimpan di '{output_file}'.")
    print(f"{skipped} chunks kecil diabaikan.")

if __name__ == "__main__":
    export_final_jsonl()