import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from sqlalchemy.orm import sessionmaker
from models import crawler_engine, CrawledPage, PageLink
import argparse
from datetime import datetime
import time
from requests.exceptions import RequestException
from sqlalchemy.exc import SQLAlchemyError

class WebCrawler:
    def __init__(self, start_url, max_pages=100, max_depth=3, follow_external_links=False):
        """Initialize the web crawler."""
        self.start_url = start_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.follow_external_links = follow_external_links
        self.visited_urls = set()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        }
        self.Session = sessionmaker(bind=crawler_engine)
        self.delay = 1  # Delay between requests in seconds
        
    def is_valid_url(self, url):
        """Check if URL is valid and belongs to the same domain."""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)
        except:
            return False
            
    def clean_text(self, text):
        """Clean and normalize text content."""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
        
    def crawl(self, url, depth=0):
        """Crawl a URL and its links recursively."""
        # Skip if max pages reached or max depth exceeded
        if len(self.visited_urls) >= self.max_pages or depth > self.max_depth:
            return
        
        # Skip if already crawled
        if url in self.visited_urls:
            return
        
        # Add to crawled set
        self.visited_urls.add(url)
        print(f"Crawling ({len(self.visited_urls)}/{self.max_pages}): {url}")
        
        session = self.Session()
        
        try:
            # Check if URL already exists in database
            existing_page = session.query(CrawledPage).filter_by(url=url).first()
            
            try:
                # Fetch page content
                response = requests.get(url, headers=self.headers, timeout=10)
                
                # Get page title and content
                title = ""
                content = ""
                links = []
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Get title
                    title_tag = soup.find('title')
                    if title_tag:
                        title = title_tag.text.strip()
                    
                    # Get content (main text)
                    content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    content = ' '.join([tag.text.strip() for tag in content_tags])
                    
                    # Extract links
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        
                        # Skip empty, javascript, and anchor links
                        if not href or href.startswith('javascript:') or href.startswith('#'):
                            continue
                        
                        # Handle relative URLs
                        if href.startswith('/'):
                            parsed_url = urlparse(url)
                            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                        
                        # Skip external domains if configured
                        if not self.follow_external_links:
                            base_domain = urlparse(self.start_url).netloc
                            link_domain = urlparse(href).netloc
                            if link_domain and link_domain != base_domain:
                                continue
                        
                        links.append(href)
                
                # Update or create page in database
                if existing_page:
                    existing_page.title = title
                    existing_page.content = content
                    existing_page.last_crawled = datetime.utcnow()
                    existing_page.status_code = response.status_code
                else:
                    page = CrawledPage(
                        url=url,
                        title=title,
                        content=content,
                        status_code=response.status_code,
                        crawled_at=datetime.utcnow(),
                        last_crawled=datetime.utcnow()
                    )
                    session.add(page)
                    session.flush()  # Flush to get page ID
                    
                    # Add links to database
                    for link_url in links:
                        link = PageLink(
                            source_page_id=page.id,
                            target_url=link_url
                        )
                        session.add(link)
                
                session.commit()
                
                # Recursively crawl links
                if depth < self.max_depth:
                    for link_url in links:
                        # Make sure we don't exceed max pages
                        if len(self.visited_urls) >= self.max_pages:
                            break
                        
                        # Sleep to avoid overloading the server
                        time.sleep(self.delay)
                        
                        try:
                            self.crawl(link_url, depth + 1)
                        except Exception as link_error:
                            print(f"Error crawling link {link_url}: {str(link_error)}")
                            continue
                
            except requests.exceptions.RequestException as e:
                print(f"Error accessing {url}: {str(e)}")
                
                # Still record the failed attempt in the database
                if existing_page:
                    existing_page.last_crawled = datetime.utcnow()
                    existing_page.status_code = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
                else:
                    page = CrawledPage(
                        url=url,
                        title="",
                        content="",
                        status_code=getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0,
                        crawled_at=datetime.utcnow(),
                        last_crawled=datetime.utcnow()
                    )
                    session.add(page)
                
                session.commit()
                
        except Exception as e:
            session.rollback()
            print(f"Database error for {url}: {str(e)}")
        finally:
            session.close()
            
    def start_crawling(self):
        """Start the crawling process from the start URL."""
        print(f"Starting crawl from {self.start_url}")
        print(f"Max pages: {self.max_pages}, Max depth: {self.max_depth}")
        
        start_time = time.time()
        
        try:
            self.crawl(self.start_url)
            
            elapsed_time = time.time() - start_time
            print(f"Crawling complete! Visited {len(self.visited_urls)} URLs in {elapsed_time:.2f} seconds")
        except KeyboardInterrupt:
            print("\nCrawling interrupted by user.")
            elapsed_time = time.time() - start_time
            print(f"Partial crawl completed. Visited {len(self.visited_urls)} URLs in {elapsed_time:.2f} seconds")
        except Exception as e:
            print(f"Crawling error: {str(e)}")
            elapsed_time = time.time() - start_time
            print(f"Crawling failed after {elapsed_time:.2f} seconds. Visited {len(self.visited_urls)} URLs")
            
        # Summary of crawl
        print("\nCrawl Summary:")
        print(f"- Start URL: {self.start_url}")
        print(f"- Pages crawled: {len(self.visited_urls)}")
        print(f"- Elapsed time: {elapsed_time:.2f} seconds")
        
        if self.visited_urls:
            print("- First 5 crawled URLs:")
            for url in list(self.visited_urls)[:5]:
                print(f"  - {url}")
        else:
            print("- No URLs were successfully crawled")

def main():
    parser = argparse.ArgumentParser(description='Web Crawler')
    parser.add_argument('url', help='Starting URL to crawl')
    parser.add_argument('--max-pages', type=int, default=100, help='Maximum number of pages to crawl')
    parser.add_argument('--max-depth', type=int, default=3, help='Maximum depth of crawling')
    parser.add_argument('--follow-external-links', action='store_true', help='Follow external links')
    
    args = parser.parse_args()
    
    crawler = WebCrawler(args.url, args.max_pages, args.max_depth, args.follow_external_links)
    crawler.start_crawling()

if __name__ == "__main__":
    main() 