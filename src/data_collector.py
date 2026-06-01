import yfinance as yf
import pandas as pd
import json
import logging
import requests
from datetime import datetime
from bcb import sgs, currency
from config.settings import Settings

logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self, portfolio_data):
        self.portfolio_data = portfolio_data
        self.tickers = [item['ticker'] for item in self.portfolio_data]
        
        # Check if we need USD conversion
        has_international = any(
            item.get('category') in ['US_STOCKS', 'US_REITS', 'ETF_USA'] or
            (item.get('category') == 'CRYPTO' and not item['ticker'].endswith('-BRL'))
            for item in self.portfolio_data
        )
        
        # Add USD/BRL explicitly if needed and not in list
        if has_international and "BRL=X" not in self.tickers:
            self.tickers.append("BRL=X")

    def get_market_data(self):
        """Fetches prices, variations, and fundamentals for all assets."""
        logger.info("Fetching market data for tickers: %s", self.tickers)
        results = {}

        indicators = self.get_economic_indicators()
        cdi_diario = (indicators.get('cdi', 0.11) / 100) / 252
        
        for ticker in self.tickers:
            # Mock Logic for Renda Fixa
            if ticker == "RDB-NUBANK" or ticker.startswith("RDB"):
                results[ticker] = {
                    "price": 1.0, 
                    "change_1d": cdi_diario * 100, 
                    "change_12m": indicators.get('cdi', 11.0),
                    "dy_12m": 0.0,
                    "p_vp": 1.0,
                    "pe": 0.0,
                    "roe": 0.0,
                    "sector": "Renda Fixa",
                    "recommendation": "Hold",
                    "name": "Renda Fixa (Liquidez)"
                }
                continue

            try:
                logger.info(f"Processing {ticker}...")
                # Removed custom session to fix ValueError with yfinance
                stock = yf.Ticker(ticker)
                
                # Get history for price and variation
                try:
                    hist = stock.history(period="1y")
                except Exception as e:
                    logger.warning(f"Failed to fetch history for {ticker}: {e}")
                    hist = pd.DataFrame()
                
                if not hist.empty:
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
                else:
                    # Fallback: Try fast_info if history fails
                    logger.info(f"History empty for {ticker}, trying fast_info...")
                    current_price = stock.fast_info.get('last_price', 0.0)
                    change_1d = 0.0
                    change_12m = 0.0

                if ticker == "BRL=X":
                    logger.info(f"💵 Cotação Dólar (BRL=X): R$ {current_price:.4f}")

                # Fundamentals
                try:
                    info = stock.info
                    
                    # Dividend Yield
                    dy = info.get('dividendYield', 0)
                    if dy is None: dy = 0
                    dy = dy * 100 # Convert to percentage
                    
                    # Price to Book
                    p_vp = info.get('priceToBook', 0)
                    if p_vp is None: p_vp = 0
                    
                    # P/E Ratio
                    pe = info.get('trailingPE', 0)
                    if pe is None: pe = 0
                    
                    # ROE
                    roe = info.get('returnOnEquity', 0)
                    if roe is None: roe = 0
                    roe = roe * 100
                    
                    # Sector & Recommendation
                    sector = info.get('sector', 'Unknown')
                    recommendation = info.get('recommendationKey', 'None')
                    
                    name = info.get('shortName', ticker)
                except Exception as e:
                    logger.warning(f"Could not fetch info for {ticker}: {e}")
                    dy = 0
                    p_vp = 0
                    pe = 0
                    roe = 0
                    sector = "Unknown"
                    recommendation = "None"
                    name = ticker

                results[ticker] = {
                    "price": current_price,
                    "change_1d": change_1d,
                    "change_12m": change_12m,
                    "dy_12m": dy,
                    "p_vp": p_vp,
                    "pe": pe,
                    "roe": roe,
                    "sector": sector,
                    "recommendation": recommendation,
                    "name": name
                }
                
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {e}")
                results[ticker] = {
                    "price": 0.0, "change_1d": 0.0, "change_12m": 0.0, 
                    "dy_12m": 0.0, "p_vp": 0.0, "pe": 0.0, "roe": 0.0,
                    "sector": "Unknown", "recommendation": "None", "name": ticker
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
            from datetime import timedelta # Certifique-se de importar timedelta no topo ou aqui
            
            today = datetime.now()
            start_date = (today - timedelta(days=5)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            
            # Pega o intervalo dos últimos 5 dias para garantir que pegue o último dia útil
            ptax = currency.get('USD', start=start_date, end=end_date)
            
            if not ptax.empty:
                indicators['ptax_venda'] = ptax['USD'].iloc[-1]
            else:
                indicators['ptax_venda'] = 0.0
        except Exception as e:
            logger.error(f"Error fetching PTAX via BCB: {e}")
            indicators['ptax_venda'] = 0.0

        return indicators
