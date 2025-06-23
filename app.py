from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import CrawledPage, IndexedPage, WordScore, crawler_engine, indexer_engine
import time
import json
import os

app = Flask(__name__)

# Get the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create database sessions for both crawler and indexer
crawler_engine = create_engine(f'sqlite:///{os.path.join(BASE_DIR, "crawler.db")}')
crawler_session = scoped_session(sessionmaker(bind=crawler_engine))

indexer_engine = create_engine(f'sqlite:///{os.path.join(BASE_DIR, "indexer.db")}')
indexer_session = scoped_session(sessionmaker(bind=indexer_engine))

# Enhanced wrapper for IndexedPage
class EnhancedIndexedPage:
    def __init__(self, page):
        self._page = page
        self._word_scores_dict = None
    
    @property
    def id(self):
        return self._page.id
    
    @property
    def url(self):
        return self._page.url
    
    @property
    def title(self):
        return self._page.title
    
    @property
    def status_code(self):
        return self._page.status_code
    
    @property
    def crawled_at(self):
        return self._page.crawled_at
    
    @property
    def indexed_at(self):
        # If indexed_at is None, use crawled_at as fallback
        if not hasattr(self._page, 'indexed_at') or self._page.indexed_at is None:
            return self._page.crawled_at
        return self._page.indexed_at
    
    @property
    def score(self):
        # Calculate average score from word scores
        if not self._page.word_scores:
            return 0.0
        return sum(score.score for score in self._page.word_scores) / len(self._page.word_scores)
    
    @property
    def word_scores(self):
        return self._page.word_scores
    
    @property
    def word_scores_dict(self):
        if self._word_scores_dict is None:
            self._word_scores_dict = {score.word: score.score for score in self._page.word_scores}
        return self._word_scores_dict

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/crawled')
def crawled():
    try:
        pages = crawler_session.query(CrawledPage).order_by(CrawledPage.last_crawled.desc()).all()
        return render_template('crawled.html', pages=pages)
    finally:
        crawler_session.close()

@app.route('/indexed')
def indexed():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get total count
        total_count = indexer_session.query(func.count(IndexedPage.id)).scalar()
        total_pages = (total_count + per_page - 1) // per_page
        
        # Ensure page is within valid range
        page = max(1, min(page, total_pages))
        
        # Get paginated results
        pages = indexer_session.query(IndexedPage)\
            .order_by(IndexedPage.id.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()
            
        enhanced_pages = [EnhancedIndexedPage(page) for page in pages]
        return render_template('indexed.html', 
                             pages=enhanced_pages,
                             current_page=page,
                             total_pages=total_pages,
                             total_count=total_count,
                             per_page=per_page,
                             max=max,
                             min=min)
    finally:
        indexer_session.close()

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('search_results.html', query='', results=[], search_time=0)
    
    start_time = time.time()
    
    try:
        # Split the query into individual words
        words = query.lower().split()
        
        # Find pages containing any of the query words
        page_scores = {}
        for word in words:
            word_scores = indexer_session.query(
                WordScore.page_id, 
                WordScore.score
            ).filter(
                WordScore.word.like(f"%{word}%")
            ).all()
            
            for page_id, score in word_scores:
                if page_id not in page_scores:
                    page_scores[page_id] = 0
                page_scores[page_id] += score
        
        # Get page details for the scored pages
        results = []
        for page_id, score in sorted(page_scores.items(), key=lambda x: x[1], reverse=True):
            page = indexer_session.query(IndexedPage).filter_by(id=page_id).first()
            if page:
                # Create snippet from content if available
                snippet = ''
                if hasattr(page, 'content') and page.content:
                    content = page.content.lower()
                    for word in words:
                        idx = content.find(word)
                        if idx >= 0:
                            start = max(0, idx - 50)
                            end = min(len(content), idx + 50)
                            snippet = "..." + content[start:end] + "..."
                            break
                
                results.append({
                    'url': page.url,
                    'title': page.title,
                    'snippet': snippet,
                    'score': score
                })
        
        search_time = time.time() - start_time
        return render_template('search_results.html', query=query, results=results, search_time=search_time)
    
    finally:
        indexer_session.close()

if __name__ == '__main__':
    app.run(debug=True) 