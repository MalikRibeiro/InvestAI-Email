import pandas as pd
import json
import os
from datetime import datetime
from config.settings import Settings
import logging

logger = logging.getLogger(__name__)

class PortfolioManager:
    def __init__(self, market_data, indicators):
        self.market_data = market_data
        self.indicators = indicators
        self.target_alloc = Settings.TARGET_ALLOCATION
        self.portfolio_file = "data/portfolio.json"
        
        # Ensure data dir exists
        os.makedirs("data", exist_ok=True)

    def _load_portfolio_data(self):
        """Loads portfolio data from JSON file."""
        try:
            with open(self.portfolio_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load portfolio.json: {e}")
            return []

    def _get_rdb_value(self):
        """Calculates updated RDB value based on CDI."""
        # Using a separate state file for RDB since it's a simulated fixed income asset
        rdb_state_file = "data/rdb_state.json"
        
        default_state = {
            "rdb_value": 1000.00, # Placeholder
            "last_update": datetime.now().strftime("%Y-%m-%d")
        }
        
        if os.path.exists(rdb_state_file):
            with open(rdb_state_file, 'r') as f:
                state = json.load(f)
        else:
            state = default_state
            with open(rdb_state_file, 'w') as f:
                json.dump(state, f)
        
        last_date = datetime.strptime(state["last_update"], "%Y-%m-%d")
        today = datetime.now()
        
        if today.date() > last_date.date():
            # Get CDI daily rate (approx from Selic Meta)
            selic_meta = self.indicators.get('selic_meta', 11.75) 
            cdi_yearly = selic_meta - 0.10
            # Daily factor (1 + CDI)^(1/252) - 1
            # RDB is 115% of CDI
            daily_cdi = (1 + cdi_yearly/100)**(1/252) - 1
            daily_rdb = daily_cdi * 1.15
            
            days_diff = (today - last_date).days 
            # Ideally we check business days. For MVP, assuming every weekday run.
            
            # Update value
            new_value = state["rdb_value"] * ((1 + daily_rdb) ** days_diff) 
            
            state["rdb_value"] = new_value
            state["last_update"] = today.strftime("%Y-%m-%d")
            
            with open(rdb_state_file, 'w') as f:
                json.dump(state, f)
                
            return new_value
        else:
            return state["rdb_value"]

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
        portfolio_items = self._load_portfolio_data()
        portfolio = []
        total_value = 0
        
        # 1. Process Tickers
        for item in portfolio_items:
            ticker = item['ticker']
            qty = item['qty']
            avg_price = item.get('avg_price', 0.0)
            category = item.get('category', 'OUTROS')
            
            data = self.market_data.get(ticker, {})
            current_price = data.get('price', 0)
            
            # Currency Conversion
            # If category is Crypto or ticker ends with -USD, convert to BRL
            if category in ["US_REITS", "US_STOCKS", "CRYPTO"] or ticker.endswith("-USD"):
                usd_rate = self.market_data.get('BRL=X', {}).get('price', 5.0)
                if usd_rate == 0: usd_rate = 5.0 # Fallback
                
                # If it's already in BRL (like USDT-BRL), don't multiply
                if ticker.endswith("-BRL"):
                    value_brl = current_price * qty
                    avg_price_brl = avg_price # Assuming avg_price is in BRL for BRL assets
                else:
                    value_brl = current_price * qty * usd_rate
                    avg_price_brl = avg_price * usd_rate # Assuming avg_price is in USD for USD assets
            else:
                value_brl = current_price * qty
                avg_price_brl = avg_price
                
            if current_price == 0:
                logger.warning(f"Price for {ticker} is 0. Check data source.")

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
                "avg_price": avg_price,
                "value_brl": value_brl,
                "category": category,
                "name": data.get('name', ticker),
                "dy_12m": data.get('dy_12m', 0),
                "p_vp": data.get('p_vp', 0),
                "change_1d": data.get('change_1d', 0),
                "change_12m": data.get('change_12m', 0),
                "profit_loss_pct": profit_loss_pct,
                "profit_loss_val": profit_loss_val
            })
            
        # 2. Process RDB (Fixed Income)
        rdb_val = self._get_rdb_value()
        portfolio.append({
            "ticker": "RDB Nubank",
            "qty": 1,
            "price": rdb_val,
            "avg_price": 1000.00, # Initial investment placeholder
            "value_brl": rdb_val,
            "category": "RENDA_FIXA", # Internal name
            "name": "RDB Nubank 115% CDI",
            "dy_12m": 0,
            "p_vp": 0,
            "change_1d": 0,
            "change_12m": 0,
            "profit_loss_pct": ((rdb_val - 1000)/1000)*100,
            "profit_loss_val": rdb_val - 1000
        })
        total_value += rdb_val
        
        # 3. History & Variation
        history = self._load_history()
        daily_variation_pct = 0.0
        
        if history:
            # Sort by date just in case
            history.sort(key=lambda x: x['date'])
            # Get last entry that is NOT today
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
            "RENDA_FIXA": "Renda Fixa"
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
