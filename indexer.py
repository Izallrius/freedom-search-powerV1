from sqlalchemy.orm import sessionmaker
from database.models import crawler_engine, indexer_engine, CrawledPage, IndexedPage, WordScore
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter
import argparse
import re
import sys
import sqlite3
import time

# Download required NLTK data
try:
    print("Checking NLTK data...")
    nltk.download('punkt')
    nltk.download('stopwords')
except Exception as e:
    print(f"Warning: Could not download NLTK data: {str(e)}")
    print("Please run download_nltk_data.py to ensure all required data is available.")

class SearchIndexer:
    def __init__(self):
        self.Session = sessionmaker(bind=indexer_engine)
        try:
            self.stop_words = set(stopwords.words('english'))
        except Exception as e:
            print(f"Warning: Could not load stopwords: {str(e)}")
            print("Using a basic set of stopwords instead.")
            # Fallback to a basic set of stopwords
            self.stop_words = set(['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 
                                  'you', 'your', 'yours', 'yourself', 'yourselves', 
                                  'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 
                                  'herself', 'it', 'its', 'itself', 'they', 'them', 
                                  'their', 'theirs', 'themselves', 'what', 'which', 
                                  'who', 'whom', 'this', 'that', 'these', 'those', 
                                  'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                                  'have', 'has', 'had', 'having', 'do', 'does', 'did', 
                                  'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 
                                  'because', 'as', 'until', 'while', 'of', 'at', 'by', 
                                  'for', 'with', 'about', 'against', 'between', 'into', 
                                  'through', 'during', 'before', 'after', 'above', 'below', 
                                  'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 
                                  'over', 'under', 'again', 'further', 'then', 'once'])
        self.CrawlerSession = sessionmaker(bind=crawler_engine)
        
    def clean_text(self, text):
        """Clean and normalize text content."""
        if not text:
            return ""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return text
    
    def custom_tokenize(self, text):
        """Custom tokenization function that doesn't rely on NLTK's punkt_tab."""
        if not text:
            return []
        # Simple tokenization by splitting on whitespace and filtering out empty strings
        return [word for word in re.findall(r'\b\w+\b', text.lower()) if word]
    
    def process_text(self, text, weight=1.0):
        """Process text: clean, tokenize, and remove stop words."""
        if not text:
            return []
        text = self.clean_text(text)
        
        # Try to use NLTK's tokenizer, fall back to custom solution if it fails
        try:
            tokens = word_tokenize(text)
        except Exception as e:
            print(f"Warning: NLTK tokenization failed, using fallback: {str(e)}")
            tokens = self.custom_tokenize(text)
            
        return [word for word in tokens if word not in self.stop_words]
        
    def calculate_word_scores(self, text, title):
        """Calculate scores for words based on their importance."""
        # Clean and tokenize text
        text = self.clean_text(text)
        title = self.clean_text(title)
        
        # Tokenize
        try:
            text_tokens = word_tokenize(text)
            title_tokens = word_tokenize(title)
        except Exception as e:
            print(f"Warning: NLTK tokenization failed, using fallback: {str(e)}")
            text_tokens = self.custom_tokenize(text)
            title_tokens = self.custom_tokenize(title)
        
        # Remove stop words
        text_tokens = [word for word in text_tokens if word not in self.stop_words]
        title_tokens = [word for word in title_tokens if word not in self.stop_words]
        
        # Count word frequencies
        text_freq = Counter(text_tokens)
        title_freq = Counter(title_tokens)
        
        # Calculate scores
        word_scores = {}
        
        # Process title words (higher weight)
        for word, freq in title_freq.items():
            if word not in word_scores:
                word_scores[word] = min(100, freq * 20)  # Title words get higher weight
        
        # Process content words
        for word, freq in text_freq.items():
            if word not in word_scores:
                # Content words get lower weight
                word_scores[word] = min(100, freq * 5)
            else:
                # If word appears in both title and content, boost its score
                word_scores[word] = min(100, word_scores[word] + (freq * 5))
        
        return word_scores
        
    def index_page(self, page, max_retries=3, retry_delay=1):
        """Index a single crawled page."""
        # Skip indexing if URL already indexed
        indexer_session = self.Session()
        try:
            existing_page = indexer_session.query(IndexedPage).filter_by(url=page.url).first()
            if existing_page:
                print(f"Page already indexed: {page.url}")
                return "skipped"
        finally:
            indexer_session.close()
        
        # Process and index the page
        session = self.Session()
        retries = 0
        
        while retries <= max_retries:
            try:
                # Safely get status_code, default to 0 if attribute doesn't exist
                status_code = getattr(page, 'status_code', 0)
                
                # Create indexed page entry - without content and crawled_at
                indexed_page = IndexedPage(
                    url=page.url,
                    title=page.title if hasattr(page, 'title') and page.title else "",
                )
                
                # Set attributes separately to avoid constructor issues
                try:
                    if hasattr(page, 'content') and page.content:
                        indexed_page.content = page.content
                except Exception as e:
                    print(f"Warning: Could not set content for {page.url}: {str(e)}")
                
                try:
                    if hasattr(page, 'last_crawled'):
                        indexed_page.crawled_at = page.last_crawled
                except Exception as e:
                    print(f"Warning: Could not set crawled_at for {page.url}: {str(e)}")
                
                # Try to set status_code if the column exists
                try:
                    indexed_page.status_code = status_code
                except Exception as e:
                    print(f"Warning: Could not set status_code for {page.url}: {str(e)}")
                    
                session.add(indexed_page)
                session.flush()  # Get ID without committing
                
                # Get content for word scoring
                page_content = page.content if hasattr(page, 'content') and page.content else ""
                if not page_content:
                    # Skip word scoring if no content
                    session.commit()
                    return True
                
                # Process text to get word scores
                title_words = self.process_text(indexed_page.title, weight=2.0)
                content_words = self.process_text(page_content, weight=1.0)
                
                # Combine and normalize word scores
                word_scores = self.calculate_word_scores(content_words, title_words)
                
                # Add word scores in batches
                batch_size = 50
                word_batch = []
                
                for word, normalized_score in word_scores.items():
                    word_batch.append(
                        WordScore(
                            page_id=indexed_page.id,
                            word=word,
                            score=normalized_score
                        )
                    )
                    
                    # Commit in batches to avoid large transactions
                    if len(word_batch) >= batch_size:
                        session.add_all(word_batch)
                        session.commit()
                        word_batch = []
                
                # Add any remaining words
                if word_batch:
                    session.add_all(word_batch)
                
                session.commit()
                return True
                
            except sqlite3.OperationalError as e:
                # Handle database locked errors
                if "database is locked" in str(e) and retries < max_retries:
                    retries += 1
                    print(f"Database locked, retrying ({retries}/{max_retries}) after {retry_delay}s delay...")
                    session.rollback()
                    time.sleep(retry_delay)
                    # Increase delay exponentially for next retry
                    retry_delay *= 2
                else:
                    session.rollback()
                    print(f"Error indexing page {page.url}: {str(e)}")
                    return False
                    
            except Exception as e:
                session.rollback()
                print(f"Error indexing page {page.url}: {str(e)}")
                return False
                
            finally:
                if retries >= max_retries:
                    print(f"Max retries reached for {page.url}, skipping")
                    return False
        
        session.close()
        
    def index_all_pages(self, batch_size=10):
        """Index all crawled pages with built-in resilience."""
        crawler_session = self.CrawlerSession()
        
        try:
            # Get all crawled pages ordered by last crawl time
            pages = crawler_session.query(CrawledPage).order_by(CrawledPage.last_crawled.desc()).all()
            
            total_pages = len(pages)
            indexed_count = 0
            skipped_count = 0
            error_count = 0
            
            print(f"Starting indexing of {total_pages} pages...")
            start_time = time.time()
            
            # Process in batches for better throughput and to avoid long-running transactions
            for i in range(0, total_pages, batch_size):
                batch = pages[i:i+batch_size]
                
                for page in batch:
                    try:
                        result = self.index_page(page)
                        
                        if result == "skipped":
                            skipped_count += 1
                        elif result:
                            indexed_count += 1
                        else:
                            error_count += 1
                            
                    except KeyboardInterrupt:
                        elapsed_time = time.time() - start_time
                        print("\nIndexing interrupted by user!")
                        print(f"Stats: {indexed_count} indexed, {skipped_count} skipped, {error_count} errors")
                        print(f"Elapsed time: {elapsed_time:.2f} seconds")
                        return
                    except Exception as e:
                        print(f"Unexpected error processing page {page.url}: {str(e)}")
                        error_count += 1
                
                # Print progress after each batch
                current = min(i + batch_size, total_pages)
                print(f"Progress: {current}/{total_pages} pages processed ({indexed_count} indexed, {skipped_count} skipped, {error_count} errors)")
                
                # Estimate remaining time
                elapsed_time = time.time() - start_time
                pages_per_second = current / elapsed_time if elapsed_time > 0 else 0
                remaining_pages = total_pages - current
                estimated_remaining_time = remaining_pages / pages_per_second if pages_per_second > 0 else 0
                
                print(f"Speed: {pages_per_second:.2f} pages/second, Estimated time remaining: {estimated_remaining_time:.2f} seconds")
            
            elapsed_time = time.time() - start_time
            print(f"\nIndexing complete! {indexed_count} pages indexed, {skipped_count} skipped, {error_count} errors.")
            print(f"Total time: {elapsed_time:.2f} seconds")
            
        except KeyboardInterrupt:
            print("\nIndexing interrupted by user!")
        finally:
            crawler_session.close()
            
def main():
    parser = argparse.ArgumentParser(description='Search Indexer')
    args = parser.parse_args()
    
    indexer = SearchIndexer()
    indexer.index_all_pages()

if __name__ == "__main__":
    main() 