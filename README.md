# Freedom Search - Your Personal Search Engine

Freedom Search is a custom search engine that allows you to crawl, index, and search web pages. This guide will help you get started with using the search engine.

## Prerequisites

- Python 3.7 or higher
- SQLite3
- Required Python packages (install using `pip install -r requirements.txt`):
  - Flask
  - SQLAlchemy
  - requests
  - beautifulsoup4
  - nltk

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd freedom-search
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Initialize the databases:
```bash
python init_db.py
```

## Running the Application

### Step 1: Crawl web pages

Use the crawler to collect web pages:

```bash
python crawler.py <url> [--max-pages MAX_PAGES] [--max-depth MAX_DEPTH]
```

Example:
```bash
python crawler.py https://example.com --max-pages 100 --max-depth 3
```

Parameters:
- `<url>`: The starting URL to crawl
- `--max-pages`: Maximum number of pages to crawl (default: 100)
- `--max-depth`: Maximum depth of links to follow (default: 3)

### Step 2: Index the crawled pages

Process the crawled pages to make them searchable:

```bash
python indexer.py
```

The indexer will:
- Process all crawled pages
- Calculate word importance scores
- Store indexed information in the database

### Step 3: Start the web application

```bash
python app.py
```

Then open your web browser and navigate to:
```
http://localhost:5000
```

## Using the Search Engine

### 1. Crawling Web Pages

The crawler collects web pages and their content for indexing. To crawl pages:

1. Run the crawler command with a starting URL
2. The crawler will automatically collect pages from the specified URL and follow links
3. You can view crawled pages in the Crawled Pages section of the web interface, including:
   - Page title
   - URL
   - Status code
   - Last crawl time
   - Page content (click "View" to see)

### 2. Indexing Pages

The indexer processes crawled pages to make them searchable:

1. Run the indexer command to process all crawled pages
2. The indexer will extract words, calculate their importance, and store them in the database
3. You can view indexed pages in the Indexed Pages section of the web interface, including:
   - View the page URL and title
   - See word scores (click "View Scores")
   - View the full page content

### 3. Searching

To search the indexed pages:

1. On the homepage, enter your search query in the search box
2. Click the search button or press Enter
3. Results will be displayed with:
   - Page title
   - URL
   - Snippet containing your search terms
   - Relevance score

Example searches:
```
india news
technology updates
sports headlines
```

### 4. Advanced Features

#### Word Scores
- Click "View Scores" on any indexed page to see word frequency scores
- Words with higher scores appear more frequently in the page
- This helps understand the page's main topics

#### Content Viewing
- Click "View" on crawled pages to see the full content
- Content is displayed in a modal window
- You can copy or read the content directly

#### Sorting and Filtering
- Click column headers to sort tables
- Use the search box in Crawled/Indexed pages to filter results
- Results update in real-time as you type

## Example Usage

1. **Crawling a Website**:
   ```bash
   python crawler.py https://news.ycombinator.com --max-pages 50 --max-depth 2
   ```
   This will crawl Hacker News, following links up to 2 levels deep and collecting up to 50 pages.

2. **Indexing the Crawled Pages**:
   ```bash
   python indexer.py
   ```
   This will process all crawled pages and calculate word scores.

3. **Basic Search**:
   - Start the web application: `python app.py`
   - Go to homepage (http://localhost:5000)
   - Type "technology news"
   - Press Enter
   - View results with snippets and scores

4. **Viewing Crawled Pages**:
   - Click "Crawled Pages" in navigation
   - Find a page of interest
   - Click "View" to see content
   - Check status code and last crawl time

5. **Analyzing Word Scores**:
   - Go to "Indexed Pages"
   - Find a page
   - Click "View Scores"
   - Analyze word frequency distribution

## Troubleshooting

1. **No Results Found**:
   - Ensure pages have been crawled (`python crawler.py <url>`)
   - Check if indexing is complete (`python indexer.py`)
   - Try different search terms

2. **Database Errors**:
   - Run `python init_db.py` to recreate tables
   - Check database file permissions
   - Verify database paths in configuration

3. **Crawling Issues**:
   - Check internet connection
   - Verify URL accessibility
   - Use lower values for `--max-pages` and `--max-depth`
   - Check crawler logs for errors

4. **Indexing Errors**:
   - Make sure NLTK data is downloaded: 
     ```python
     import nltk
     nltk.download('punkt')
     nltk.download('stopwords')
     ```
   - Check if there's enough disk space

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the code documentation
3. Contact support or create an issue

## License

[Your License Information]

## Contributing

[Contribution Guidelines]