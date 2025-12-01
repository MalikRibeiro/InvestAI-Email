import yfinance as yf
import pandas as pd
import json
import logging
from datetime import datetime
from bcb import sgs, currency
from config.settings import Settings

logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self):
        self.portfolio_data = self._load_portfolio()
        self.tickers = [item['ticker'] for item in self.portfolio_data]
        # Add USD/BRL explicitly if not in list
        if "BRL=X" not in self.tickers:
            self.tickers.append("BRL=X")

    def _load_portfolio(self):
        """Loads portfolio data from JSON file."""
        try:
            with open('data/portfolio.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load portfolio.json: {e}")
            return []

    def get_market_data(self):
        """Fetches prices, variations, and fundamentals for all assets."""
        logger.info("Fetching market data for tickers: %s", self.tickers)
        results = {}
        
        for ticker in self.tickers:
            try:
                logger.info(f"Processing {ticker}...")
                stock = yf.Ticker(ticker)
                
                # Get history for price and variation
                hist = stock.history(period="1y")
                
                if hist.empty:
                    logger.warning(f"No history found for {ticker}")
                    results[ticker] = {
                        "price": 0.0,
                        "change_1d": 0.0,
                        "change_12m": 0.0,
                        "dy_12m": 0.0,
                        "p_vp": 0.0,
                        "name": ticker
                    }
                    continue

                current_price = hist['Close'].iloc[-1]
                
                # 1D Variation
                if len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    change_1d = ((current_price - prev_close) / prev_close) * 100
                else:
                    change_1d = 0.0
                    
                # 12M Variation
                if len(hist) > 0:
                    price_12m_ago = hist['Close'].iloc[0]
                    change_12m = ((current_price - price_12m_ago) / price_12m_ago) * 100
                else:
                    change_12m = 0.0

                # Fundamentals
                try:
                    info = stock.info
                    dy = info.get('dividendYield', 0)
                    if dy is None: dy = 0
                    dy = dy * 100 # Convert to percentage
                    
                    p_vp = info.get('priceToBook', 0)
                    if p_vp is None: p_vp = 0
                    
                    name = info.get('shortName', ticker)
                except Exception as e:
                    logger.warning(f"Could not fetch info for {ticker}: {e}")
                    dy = 0
                    p_vp = 0
                    name = ticker

                results[ticker] = {
                    "price": current_price,
                    "change_1d": change_1d,
                    "change_12m": change_12m,
                    "dy_12m": dy,
                    "p_vp": p_vp,
                    "name": name
                }
                
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {e}")
                results[ticker] = {
                    "price": 0.0, "change_1d": 0.0, "change_12m": 0.0, "dy_12m": 0.0, "p_vp": 0.0, "name": ticker
                }

        return results

    def get_economic_indicators(self):
        """Fetches Selic, CDI, and PTAX using python-bcb."""
        indicators = {}
        
        try:
            # Selic Meta (432)
            selic_series = sgs.get({'selic': 432}, last=1)
            indicators['selic_meta'] = float(selic_series['selic'].iloc[-1])
        except Exception as e:
            logger.error(f"Error fetching Selic via BCB: {e}")
            indicators['selic_meta'] = 0.0

        try:
            # CDI (12) - Taxa DI % a.a.
            # Using Selic as proxy for CDI if we can't find the exact annualized CDI series easily, 
            # but usually CDI follows Selic Over.
            indicators['cdi'] = indicators['selic_meta'] - 0.10
        except Exception:
            indicators['cdi'] = 0.0

        try:
            # PTAX (USD)
            # python-bcb has a currency module
            # Fix: use 'start' and 'end' instead of 'start_date' and 'end_date'
            today_str = datetime.now().strftime('%Y-%m-%d')
            ptax = currency.get('USD', start=today_str, end=today_str)
            
            if not ptax.empty:
                indicators['ptax_venda'] = ptax['USD'].iloc[-1]
            else:
                # Try yesterday if today is empty (weekend/holiday)
                last_ptax = currency.get('USD', last=1)
                if not last_ptax.empty:
                    indicators['ptax_venda'] = last_ptax['USD'].iloc[-1]
                else:
                    indicators['ptax_venda'] = 0.0
        except Exception as e:
            logger.error(f"Error fetching PTAX via BCB: {e}")
            indicators['ptax_venda'] = 0.0

        return indicators
