from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os

Base = declarative_base()

# Crawler Database Models
class CrawledPage(Base):
    __tablename__ = 'crawled_pages'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    title = Column(String)
    content = Column(String)
    last_crawled = Column(DateTime, default=datetime.utcnow)
    links = relationship("PageLink", back_populates="page")

class PageLink(Base):
    __tablename__ = 'page_links'
    
    id = Column(Integer, primary_key=True)
    source_page_id = Column(Integer, ForeignKey('crawled_pages.id'))
    target_url = Column(String)
    page = relationship("CrawledPage", back_populates="links")

# Indexer Database Models
class IndexedPage(Base):
    __tablename__ = 'indexed_pages'
    
    id = Column(Integer, primary_key=True)
    crawled_page_id = Column(Integer, ForeignKey('crawled_pages.id'))
    url = Column(String, unique=True)
    title = Column(String)
    word_scores = relationship("WordScore", back_populates="page")

class WordScore(Base):
    __tablename__ = 'word_scores'
    
    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey('indexed_pages.id'))
    word = Column(String)
    score = Column(Float)
    page = relationship("IndexedPage", back_populates="word_scores")

# Get the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create database engines with absolute paths
crawler_engine = create_engine(f'sqlite:///{os.path.join(BASE_DIR, "..", "crawler.db")}')
indexer_engine = create_engine(f'sqlite:///{os.path.join(BASE_DIR, "..", "indexer.db")}')

# Create all tables
Base.metadata.create_all(crawler_engine)
Base.metadata.create_all(indexer_engine) 