"""
News Fetcher for Trading Bot
Fetches real-time news for stocks and cryptocurrencies for Gemini AI analysis
"""
import requests
from datetime import datetime, timedelta
from loguru import logger
import config


class CryptoNewsFetcher:
    """Fetches news from various sources (works for both stocks and crypto)"""

    def __init__(self):
        self.news_api_key = config.NEWS_API_KEY
        self.alpha_vantage_key = config.ALPHA_VANTAGE_KEY

    def get_crypto_news(self, symbol, hours=24, max_articles=5):
        """
        Get recent news for a symbol (stocks or crypto)

        Args:
            symbol: Stock ticker (e.g., 'AAPL', 'NVDA') or crypto symbol (e.g., 'BTC/USD')
            hours: Look back this many hours
            max_articles: Max number of articles to return

        Returns:
            List of news articles with title, source, and published date
        """
        # Convert symbol to search term
        search_term = self._symbol_to_search_term(symbol)

        news = []

        # Try NewsAPI first
        if self.news_api_key:
            news_api_articles = self._fetch_from_newsapi(search_term, hours, max_articles)
            news.extend(news_api_articles)

        # If we don't have enough news, add general market news
        if len(news) < 2:
            general_news = self._get_general_market_news(hours, max_articles, is_crypto='/' in symbol)
            news.extend(general_news)

        # Limit to max_articles
        return news[:max_articles]

    def _symbol_to_search_term(self, symbol):
        """Convert trading symbol to news search term"""
        # Crypto symbols (with slash)
        crypto_map = {
            'BTC/USD': 'Bitcoin',
            'ETH/USD': 'Ethereum',
            'DOGE/USD': 'Dogecoin',
            'SHIB/USD': 'Shiba Inu',
            'SOL/USD': 'Solana',
            'AVAX/USD': 'Avalanche',
            'MATIC/USD': 'Polygon',
            'UNI/USD': 'Uniswap',
            'LINK/USD': 'Chainlink',
            'LTC/USD': 'Litecoin',
        }

        # Stock name mappings (for better news results)
        stock_map = {
            'AAPL': 'Apple',
            'NVDA': 'NVIDIA',
            'AVGO': 'Broadcom',
            'TSLA': 'Tesla',
            'MSFT': 'Microsoft',
            'GOOGL': 'Google Alphabet',
            'AMZN': 'Amazon',
            'META': 'Meta Facebook',
            'GLD': 'Gold ETF',
            'SNDK': 'SanDisk Western Digital',
            'LITE': 'Lumentum',
            'MP': 'MP Materials',
            'RKLB': 'Rocket Lab',
            'USAR': 'American Strategic Investment',
            'APLD': 'Applied Blockchain',
            'IREN': 'Iris Energy',
            'UUUU': 'Energy Fuels',
        }

        # Check if crypto or stock
        if '/' in symbol:
            return crypto_map.get(symbol, symbol.split('/')[0])
        else:
            # For stocks, use company name if available, otherwise use ticker
            return stock_map.get(symbol, symbol)

    def _fetch_from_newsapi(self, search_term, hours, max_articles):
        """Fetch news from NewsAPI"""
        try:
            from_date = (datetime.now() - timedelta(hours=hours)).isoformat()

            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': f'{search_term} OR cryptocurrency OR crypto',
                'from': from_date,
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': max_articles,
                'apiKey': self.news_api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = []

            for article in data.get('articles', [])[:max_articles]:
                # Filter for relevant articles
                title = article.get('title', '')
                if title and title != '[Removed]':
                    articles.append({
                        'title': title,
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'published': article.get('publishedAt', ''),
                        'description': article.get('description', '')[:200]  # First 200 chars
                    })

            if articles:
                logger.info(f"Fetched {len(articles)} news articles from NewsAPI for {search_term}")

            return articles

        except Exception as e:
            logger.warning(f"Error fetching from NewsAPI: {e}")
            return []

    def _get_general_market_news(self, hours, max_articles, is_crypto=False):
        """Get general market news (crypto or stock)"""
        try:
            from_date = (datetime.now() - timedelta(hours=hours)).isoformat()

            url = 'https://newsapi.org/v2/everything'

            # Different search terms for crypto vs stocks
            if is_crypto:
                search_query = 'cryptocurrency OR bitcoin OR ethereum OR crypto market'
            else:
                search_query = 'stock market OR stocks OR nasdaq OR S&P 500 OR trading'

            params = {
                'q': search_query,
                'from': from_date,
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': max_articles,
                'apiKey': self.news_api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = []

            for article in data.get('articles', [])[:max_articles]:
                title = article.get('title', '')
                if title and title != '[Removed]':
                    articles.append({
                        'title': title,
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'published': article.get('publishedAt', ''),
                        'description': article.get('description', '')[:200]
                    })

            return articles

        except Exception as e:
            logger.warning(f"Error fetching general crypto news: {e}")
            return []

    def format_news_for_gemini(self, news_articles):
        """
        Format news articles for Gemini AI to analyze

        Args:
            news_articles: List of news article dicts

        Returns:
            Formatted string for Gemini
        """
        if not news_articles:
            return "No recent news available."

        formatted = "Recent News Headlines:\n\n"

        for i, article in enumerate(news_articles, 1):
            formatted += f"{i}. {article['title']}\n"
            formatted += f"   Source: {article['source']}"

            # Add time info
            try:
                pub_time = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
                hours_ago = int((datetime.now(pub_time.tzinfo) - pub_time).total_seconds() / 3600)
                if hours_ago < 1:
                    formatted += " (just now)\n"
                elif hours_ago < 24:
                    formatted += f" ({hours_ago}h ago)\n"
                else:
                    formatted += f" ({hours_ago//24}d ago)\n"
            except:
                formatted += "\n"

            # Add description if available
            if article.get('description'):
                formatted += f"   {article['description']}\n"

            formatted += "\n"

        return formatted.strip()


def test_news_fetcher():
    """Test the news fetcher"""
    fetcher = CryptoNewsFetcher()

    print("\n=== Testing BTC News Fetcher ===\n")
    news = fetcher.get_crypto_news('BTC/USD', hours=48, max_articles=5)

    if news:
        print(f"Found {len(news)} articles:\n")
        formatted = fetcher.format_news_for_gemini(news)
        print(formatted)
    else:
        print("No news found")


if __name__ == "__main__":
    test_news_fetcher()
