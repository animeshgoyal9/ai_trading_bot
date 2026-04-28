"""
Sentiment Analysis Module
Analyzes news, social media, and market sentiment
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import config
from textblob import TextBlob
import re


class SentimentAnalyzer:
    """Analyzes sentiment from multiple sources"""

    def __init__(self):
        self.news_api_key = config.NEWS_API_KEY
        self.alpha_vantage_key = config.ALPHA_VANTAGE_KEY

    def get_news_sentiment(self, symbol, days=7):
        """
        Get news sentiment for a symbol

        Args:
            symbol: Stock ticker
            days: Number of days to look back

        Returns:
            Dict with sentiment scores
        """
        try:
            # Try multiple news sources
            news_data = []

            # 1. NewsAPI
            if self.news_api_key:
                news_data.extend(self._fetch_newsapi(symbol, days))

            # 2. Alpha Vantage News Sentiment
            if self.alpha_vantage_key:
                news_data.extend(self._fetch_alpha_vantage_news(symbol))

            # 3. Yahoo Finance News (free, no API key needed)
            news_data.extend(self._fetch_yahoo_news(symbol, days))

            if not news_data:
                logger.warning(f"No news found for {symbol}")
                return self._default_sentiment()

            # Analyze sentiment
            sentiment_scores = self._analyze_news_sentiment(news_data)

            logger.debug(f"{symbol} news sentiment: {sentiment_scores['overall_sentiment']:.3f}")
            return sentiment_scores

        except Exception as e:
            logger.error(f"Error getting news sentiment for {symbol}: {e}")
            return self._default_sentiment()

    def _fetch_newsapi(self, symbol, days):
        """Fetch news from NewsAPI"""
        try:
            url = "https://newsapi.org/v2/everything"
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            params = {
                'q': symbol,
                'from': from_date,
                'sortBy': 'relevancy',
                'apiKey': self.news_api_key,
                'language': 'en'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            articles = response.json().get('articles', [])
            return [{'title': a['title'], 'description': a.get('description', ''),
                    'source': 'newsapi', 'published': a['publishedAt']}
                   for a in articles[:20]]  # Limit to 20 most relevant

        except Exception as e:
            logger.warning(f"NewsAPI error: {e}")
            return []

    def _fetch_alpha_vantage_news(self, symbol):
        """Fetch news sentiment from Alpha Vantage"""
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': symbol,
                'apikey': self.alpha_vantage_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = data.get('feed', [])

            return [{'title': a['title'], 'description': a.get('summary', ''),
                    'source': 'alphavantage',
                    'sentiment_score': float(a.get('overall_sentiment_score', 0)),
                    'published': a.get('time_published')}
                   for a in articles[:20]]

        except Exception as e:
            logger.warning(f"Alpha Vantage news error: {e}")
            return []

    def _fetch_yahoo_news(self, symbol, days):
        """Fetch news from Yahoo Finance (free, no API key)"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            news = ticker.news

            if not news:
                return []

            # Filter by date
            cutoff_date = datetime.now() - timedelta(days=days)

            articles = []
            for article in news[:20]:  # Limit to 20 articles
                pub_date = datetime.fromtimestamp(article.get('providerPublishTime', 0))
                if pub_date >= cutoff_date:
                    articles.append({
                        'title': article.get('title', ''),
                        'description': article.get('summary', ''),
                        'source': 'yahoo',
                        'published': pub_date.isoformat()
                    })

            return articles

        except Exception as e:
            logger.warning(f"Yahoo Finance news error: {e}")
            return []

    def _analyze_news_sentiment(self, news_data):
        """Analyze sentiment from news articles"""
        if not news_data:
            return self._default_sentiment()

        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for article in news_data:
            # Get pre-computed sentiment if available
            if 'sentiment_score' in article:
                score = article['sentiment_score']
            else:
                # Use TextBlob for sentiment analysis
                text = f"{article.get('title', '')} {article.get('description', '')}"
                blob = TextBlob(text)
                score = blob.sentiment.polarity  # -1 to 1

            sentiments.append(score)

            if score > 0.1:
                positive_count += 1
            elif score < -0.1:
                negative_count += 1
            else:
                neutral_count += 1

        total = len(sentiments)
        return {
            'overall_sentiment': np.mean(sentiments),
            'sentiment_std': np.std(sentiments),
            'positive_ratio': positive_count / total if total > 0 else 0,
            'negative_ratio': negative_count / total if total > 0 else 0,
            'neutral_ratio': neutral_count / total if total > 0 else 0,
            'news_volume': total,
            'max_sentiment': max(sentiments) if sentiments else 0,
            'min_sentiment': min(sentiments) if sentiments else 0
        }

    def get_social_sentiment(self, symbol):
        """
        Get social media sentiment (Twitter, Reddit, StockTwits)

        Args:
            symbol: Stock ticker

        Returns:
            Dict with social sentiment scores
        """
        try:
            sentiment_data = {
                'twitter_sentiment': 0,
                'reddit_sentiment': 0,
                'stocktwits_sentiment': 0,
                'social_volume': 0
            }

            # StockTwits (free, no API key needed)
            stocktwits_data = self._fetch_stocktwits(symbol)
            if stocktwits_data:
                sentiment_data.update(stocktwits_data)

            logger.debug(f"{symbol} social sentiment: {sentiment_data}")
            return sentiment_data

        except Exception as e:
            logger.error(f"Error getting social sentiment for {symbol}: {e}")
            return {
                'twitter_sentiment': 0,
                'reddit_sentiment': 0,
                'stocktwits_sentiment': 0,
                'social_volume': 0
            }

    def _fetch_stocktwits(self, symbol):
        """Fetch sentiment from StockTwits (free API)"""
        try:
            url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            messages = data.get('messages', [])

            if not messages:
                return None

            bullish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bullish')
            bearish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bearish')
            total = len(messages)

            # Calculate sentiment score (-1 to 1)
            if total > 0:
                sentiment = (bullish - bearish) / total
            else:
                sentiment = 0

            return {
                'stocktwits_sentiment': sentiment,
                'stocktwits_bullish_ratio': bullish / total if total > 0 else 0,
                'stocktwits_bearish_ratio': bearish / total if total > 0 else 0,
                'social_volume': total
            }

        except Exception as e:
            logger.warning(f"StockTwits error: {e}")
            return None

    def get_market_sentiment(self):
        """
        Get overall market sentiment indicators

        Returns:
            Dict with market sentiment data
        """
        try:
            sentiment_data = {}

            # Fear & Greed Index
            fear_greed = self._fetch_fear_greed_index()
            if fear_greed:
                sentiment_data.update(fear_greed)

            # VIX (Volatility Index)
            vix_data = self._fetch_vix()
            if vix_data:
                sentiment_data.update(vix_data)

            # Put/Call Ratio
            put_call = self._fetch_put_call_ratio()
            if put_call:
                sentiment_data.update(put_call)

            return sentiment_data

        except Exception as e:
            logger.error(f"Error getting market sentiment: {e}")
            return {
                'fear_greed_index': 50,
                'vix': 20,
                'put_call_ratio': 1.0
            }

    def _fetch_fear_greed_index(self):
        """Fetch CNN Fear & Greed Index"""
        try:
            # Alternative Fear & Greed API
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                value = int(data['data'][0]['value'])
                classification = data['data'][0]['value_classification']

                # Normalize to -1 to 1 scale
                normalized = (value - 50) / 50

                return {
                    'fear_greed_index': value,
                    'fear_greed_normalized': normalized,
                    'fear_greed_classification': classification
                }

        except Exception as e:
            logger.warning(f"Fear & Greed Index error: {e}")
            return None

    def _fetch_vix(self):
        """Fetch VIX (Volatility Index)"""
        try:
            import yfinance as yf
            vix = yf.Ticker('^VIX')
            data = vix.history(period='5d')

            if data.empty:
                return None

            current_vix = data['Close'].iloc[-1]
            vix_change = data['Close'].pct_change().iloc[-1]

            # Normalize VIX (typical range 10-40)
            vix_normalized = (current_vix - 20) / 20

            return {
                'vix': current_vix,
                'vix_change': vix_change,
                'vix_normalized': vix_normalized
            }

        except Exception as e:
            logger.warning(f"VIX error: {e}")
            return None

    def _fetch_put_call_ratio(self):
        """Fetch Put/Call Ratio"""
        try:
            # This would require options data
            # For now, return default
            return {
                'put_call_ratio': 1.0
            }

        except Exception as e:
            logger.warning(f"Put/Call ratio error: {e}")
            return None

    def _default_sentiment(self):
        """Return default neutral sentiment"""
        return {
            'overall_sentiment': 0,
            'sentiment_std': 0,
            'positive_ratio': 0.33,
            'negative_ratio': 0.33,
            'neutral_ratio': 0.34,
            'news_volume': 0,
            'max_sentiment': 0,
            'min_sentiment': 0
        }

    def get_comprehensive_sentiment(self, symbol):
        """
        Get all sentiment data for a symbol

        Args:
            symbol: Stock ticker

        Returns:
            Dict with all sentiment features
        """
        logger.info(f"Fetching comprehensive sentiment for {symbol}")

        # News sentiment
        news_sentiment = self.get_news_sentiment(symbol, days=7)

        # Social sentiment
        social_sentiment = self.get_social_sentiment(symbol)

        # Market sentiment
        market_sentiment = self.get_market_sentiment()

        # Combine all
        comprehensive = {
            **news_sentiment,
            **social_sentiment,
            **market_sentiment
        }

        # Calculate composite sentiment score
        composite = (
            news_sentiment['overall_sentiment'] * 0.4 +
            social_sentiment.get('stocktwits_sentiment', 0) * 0.3 +
            market_sentiment.get('fear_greed_normalized', 0) * 0.3
        )

        comprehensive['composite_sentiment'] = composite
        comprehensive['sentiment_strength'] = abs(composite)

        return comprehensive
