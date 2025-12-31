import os
import glob
import json
import logging
from pathlib import Path
from typing import List, Dict
import faiss
import numpy as np
from tqdm import tqdm
from pypdf import PdfReader
import docx2txt
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sentence_transformers import SentenceTransformer

# --- Configuration ---
DATA_FOLDER = "/Users/santoshkumarhiremath/Projects/hpe-rag/data_files"
STORAGE_STATE = "storage_state.json"
CACHE_FILE = "scraped_data_cache.json"
WIKI_ROOT_URL = "https://hpe.atlassian.net/wiki/spaces/CPC/pages/3572960914/Project+PCAI"
MAX_WIKI_PAGES = 200 
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
FORCE_RE_SCRAPE = True  # Set to True to re-scrape local + wiki

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

class UnifiedIngestor:
    def __init__(self, state_path: str):
        self.state_path = state_path
        self.dataset = [] # Stores chunks: {"text": ..., "source": ..., "type": ...}
        self.visited_wiki = set()

    def process_local_files(self):
        """Scans local path for documents."""
        print(f"\n🔍 [AUDIT] Scanning local path: {DATA_FOLDER}")
        local_files = []
        for ext in ["pdf", "txt", "docx", "html", "htm"]:
            local_files.extend(glob.glob(os.path.join(DATA_FOLDER, f"**/*.{ext}"), recursive=True))
            local_files.extend(glob.glob(os.path.join(DATA_FOLDER, f"**/*.{ext.upper()}"), recursive=True))
        
        local_files = sorted(list(set(local_files)))
        print(f"📊 [AUDIT] Found {len(local_files)} local files.")

        for p in tqdm(local_files, desc="Reading Local Files"):
            txt = ""
            ext = Path(p).suffix.lower()
            try:
                if ext == ".pdf":
                    reader = PdfReader(p)
                    txt = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                elif ext == ".docx":
                    txt = docx2txt.process(p)
                elif ext == ".txt":
                    txt = Path(p).read_text(errors="ignore")
                
                if txt.strip():
                    self.dataset.extend(self.chunk_text(txt, p, ext.strip('.')))
            except Exception as e:
                logger.error(f"Failed to read {p}: {e}")

    def chunk_text(self, text: str, source: str, doc_type: str):
        chunks = []
        clean_text = " ".join(text.split())
        for i in range(0, len(clean_text), 1000):
            chunk = clean_text[i : i + 1200].strip()
            if len(chunk) > 50:
                chunks.append({"text": chunk, "source": source, "type": doc_type})
        return chunks

    def process_wiki_recursive(self, start_url: str):
        """Restored logic from your ingest1.py"""
        queue = [start_url]
        base_domain = "https://hpe.atlassian.net"
        
        with sync_playwright() as p:
            # Headless=True is faster, but you can set to False to debug
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(storage_state=self.state_path)
            page = context.new_page()

            while queue and len(self.visited_wiki) < MAX_WIKI_PAGES:
                current_url = queue.pop(0)
                if current_url in self.visited_wiki: continue
                
                try:
                    logger.info(f"🌐 Crawling Wiki: {current_url}")
                    # Switched back to 'load' as per your working script
                    page.goto(current_url, wait_until="load", timeout=60000)

                    # --- HYDRATION CHECK (From your ingest1.py) ---
                    content_found = False
                    text = ""
                    for attempt in range(15): 
                        content_node = page.query_selector("#main-content") or \
                                       page.query_selector(".wiki-content") or \
                                       page.query_selector("article")
                        
                        if content_node:
                            text = content_node.inner_text().strip()
                            if len(text) > 150: 
                                logger.info(f"✅ Scraped {len(text)} chars.")
                                self.dataset.extend(self.chunk_text(text, current_url, "wiki"))
                                content_found = True
                                break
                        page.wait_for_timeout(1000) 

                    if not content_found:
                        logger.warning(f"⚠️ Page {current_url} didn't hydrate.")

                    self.visited_wiki.add(current_url)

                    # --- DISCOVERY (From your ingest1.py) ---
                    anchors = page.query_selector_all("a[href*='/wiki/spaces/CPC/']")
                    for a in anchors:
                        href = a.get_attribute("href")
                        if not href: continue
                        
                        full_url = href if href.startswith("http") else base_domain + href
                        
                        if full_url not in self.visited_wiki and ("/pages/" in full_url or "/display/" in full_url):
                            if not any(x in full_url for x in ["/edit", "mode=", "create", "action="]):
                                if full_url not in queue:
                                    queue.append(full_url)

                except Exception as e:
                    logger.error(f"❌ Wiki Error at {current_url}: {e}")
            
            browser.close()

    def build_index(self):
        if not self.dataset:
            print("❌ ABORTED: Dataset is empty. No index built.")
            return
        
        print(f"\n🧠 Building Index for {len(self.dataset)} total chunks...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        texts = [d['text'] for d in self.dataset]
        embeddings = model.encode(texts, show_progress_bar=True).astype('float32')
        
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        
        faiss.write_index(index, "combined_index.faiss")
        with open("metadata.json", "w") as f:
            json.dump(self.dataset, f, indent=4)
        print(f"✅ Success! Created index with {len(self.dataset)} total chunks.")

if __name__ == "__main__":
    ingestor = UnifiedIngestor(STORAGE_STATE)
    
    if os.path.exists(CACHE_FILE) and not FORCE_RE_SCRAPE:
        print(f"📂 [CACHE] Loading existing data from {CACHE_FILE}.")
        with open(CACHE_FILE, "r") as f:
            ingestor.dataset = json.load(f)
    else:
        print("🔄 Starting fresh scrape (Local + Wiki)...")
        ingestor.process_local_files()
        ingestor.process_wiki_recursive(WIKI_ROOT_URL)
        
        if ingestor.dataset:
            with open(CACHE_FILE, "w") as f:
                json.dump(ingestor.dataset, f, indent=4)
    
    ingestor.build_index()
