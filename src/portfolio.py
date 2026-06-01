import pandas as pd
import json
import os
from datetime import datetime
from config.settings import Settings
import logging

logger = logging.getLogger(__name__)

class PortfolioManager:
    def __init__(self, portfolio_data, market_data, indicators):
        self.portfolio_data = portfolio_data
        self.market_data = market_data
        self.indicators = indicators
        self.target_alloc = Settings.TARGET_ALLOCATION
        
        # Ensure data dir exists
        os.makedirs("data", exist_ok=True)

    def _load_history(self):
        """Loads history data from JSON file."""
        history_file = "data/history.json"
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to load history.json: {e}")
            return []

    def _save_history(self, total_value):
        """Saves daily total value to history."""
        history_file = "data/history.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        history = self._load_history()
        
        # Check if today is already in history, update if so
        updated = False
        for entry in history:
            if entry['date'] == today:
                entry['value'] = total_value
                updated = True
                break
        
        if not updated:
            history.append({
                "date": today,
                "value": total_value
            })
            
        try:
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history.json: {e}")

    def calculate_portfolio(self):
        portfolio = []
        total_value = 0
        
        # 1. Process Tickers from Sheet Data
        for item in self.portfolio_data:
            ticker = item['ticker']
            qty = item['quantity'] # Note: key is 'quantity' from SheetsManager, not 'qty'
            category = item.get('category', 'OUTROS')
            
            # Market Data
            data = self.market_data.get(ticker, {})
            current_price = data.get('price', 0)
            
            # --- LOGIC CORRECTIONS ---
            
            # 1. Renda Fixa: Value = Qty * 1.0
            if category == "RENDA_FIXA":
                value_brl = qty * 1.0
                current_price = 1.0
                avg_price_brl = 0 # Not tracking avg price for RF yet
                
            # 2. Crypto Logic
            elif category == "CRYPTO":
                if ticker.endswith("-BRL"):
                    value_brl = current_price * qty
                    avg_price_brl = 0
                else:
                    # USDT-USD, BTC-USD, etc.
                    usd_rate = self.market_data.get('BRL=X', {}).get('price', 0)
                    
                    # Fallback de segurança se o Yahoo falhar no dólar
                    if usd_rate <= 0:
                        usd_rate = 6.00 # Taxa aproximada segura
                        logger.warning("Usando taxa de dólar fallback (6.00) para conversão de cripto.")
                        
                    value_brl = current_price * qty * usd_rate
                    avg_price_brl = 0

            # 3. US Stocks/REITs -> Convert to BRL
            elif category in ["US_REITS", "US_STOCKS", "ETF_USA"]:
                usd_rate = self.market_data.get('BRL=X', {}).get('price', 0)
                if usd_rate <= 0: 
                    usd_rate = 6.00
                    logger.warning("Usando taxa de dólar fallback (6.00) para ativos EUA.")
                    
                value_brl = current_price * qty * usd_rate
                avg_price_brl = 0
                
            # 4. Brazilian Assets (Stocks, FIIs, ETFs, BDRs)
            else:
                value_brl = current_price * qty
                avg_price_brl = 0

            if current_price == 0 and category != "RENDA_FIXA":
                logger.warning(f"Price for {ticker} is 0. Check data source.")

            # Safety check for NaN
            if pd.isna(value_brl):
                value_brl = 0.0

            total_value += value_brl
            
            # Calculate Profit/Loss
            if avg_price_brl > 0:
                profit_loss_pct = ((value_brl - (avg_price_brl * qty)) / (avg_price_brl * qty)) * 100
                profit_loss_val = value_brl - (avg_price_brl * qty)
            else:
                profit_loss_pct = 0.0
                profit_loss_val = 0.0

            portfolio.append({
                "ticker": ticker,
                "qty": qty,
                "price": current_price,
                "value_brl": value_brl,
                "category": category,
                "name": data.get('name', ticker),
                "dy_12m": data.get('dy_12m', 0),
                "p_vp": data.get('p_vp', 0),
                "pe": data.get('pe', 0),
                "roe": data.get('roe', 0),
                "sector": data.get('sector', 'Unknown'),
                "recommendation": data.get('recommendation', 'None'),
                "change_1d": data.get('change_1d', 0),
                "change_12m": data.get('change_12m', 0),
                "profit_loss_pct": profit_loss_pct,
                "profit_loss_val": profit_loss_val
            })
            
        # 2. History & Variation
        history = self._load_history()
        daily_variation_pct = 0.0
        
        if history:
            history.sort(key=lambda x: x['date'])
            today = datetime.now().strftime("%Y-%m-%d")
            last_entry = None
            for entry in reversed(history):
                if entry['date'] != today:
                    last_entry = entry
                    break
            
            if last_entry and last_entry['value'] > 0:
                daily_variation_pct = ((total_value - last_entry['value']) / last_entry['value']) * 100

        # Save today's value
        self._save_history(total_value)

        df = pd.DataFrame(portfolio)
        if not df.empty:
            df['allocation'] = (df['value_brl'] / total_value) * 100
        else:
            df['allocation'] = 0
        
        return df, total_value, daily_variation_pct

    def get_rebalancing_suggestions(self, df, total_value):
        # Map internal categories to Target Allocation keys
        cat_map = {
            "BR_STOCKS": "Ações BR",
            "FIIS": "FIIs",
            "ETFS": "ETFs",
            "US_REITS": "REITs",
            "US_STOCKS": "Ações EUA",
            "CRYPTO": "Cripto",
            "RENDA_FIXA": "Renda Fixa",
            "ETF_USA": "ETFs EUA"
        }
        
        # Group by category
        if not df.empty:
            df['target_cat'] = df['category'].map(cat_map)
            current_alloc = df.groupby('target_cat')['value_brl'].sum() / total_value
        else:
            current_alloc = pd.Series()
        
        suggestions = []
        
        for cat, target_pct in self.target_alloc.items():
            current_pct = current_alloc.get(cat, 0.0)
            diff = (current_pct * 100) - (target_pct * 100)
            
            status = "OK"
            if diff > 5:
                status = "VENDER"
            elif diff < -5:
                status = "COMPRAR"
                
            suggestions.append({
                "category": cat,
                "current_pct": current_pct * 100,
                "target_pct": target_pct * 100,
                "diff": diff,
                "status": status
            })
            
        return pd.DataFrame(suggestions)

    def suggest_contribution(self, amount, df_suggestions):
        # Simple logic: Distribute amount to categories with biggest negative deviation (COMPRAR)
        # Prioritize Variable Income if RF > 40% (User rule: "priorizar variável enquanto RF >40%")
        
        # Check RF allocation
        rf_row = df_suggestions[df_suggestions['category'] == "Renda Fixa"]
        rf_pct = rf_row['current_pct'].values[0] if not rf_row.empty else 0
        
        # Filter candidates
        candidates = df_suggestions[df_suggestions['diff'] < 0].copy()
        
        if rf_pct > 40:
            # Exclude RF from contributions
            candidates = candidates[candidates['category'] != "Renda Fixa"]
            
        if candidates.empty:
            return "Nenhuma sugestão específica (alocação equilibrada)."
            
        # Distribute proportionally to the "gap"
        total_gap = candidates['diff'].abs().sum()
        if total_gap > 0:
            candidates['contribution'] = (candidates['diff'].abs() / total_gap) * amount
        else:
            candidates['contribution'] = 0
        
        return candidates[['category', 'contribution']]
