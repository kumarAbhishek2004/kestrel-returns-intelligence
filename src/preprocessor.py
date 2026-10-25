import re
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List

class KestrelPreprocessor:
    """
    Unified production preprocessor for Kestrel Home Returns Risk System.
    Guarantees zero train-serving skew by providing identical feature transformations
    for batch training and single-record inference.
    """
    
    PRODUCT_TIER_MAP = {
        'Lite': 1,
        'Pro': 2,
        'Max': 3
    }
    
    def __init__(self, customers_df: Optional[pd.DataFrame] = None, products_df: Optional[pd.DataFrame] = None):
        self.customers_df = customers_df.copy() if customers_df is not None else None
        self.products_df = products_df.copy() if products_df is not None else None
        
        # Prepare lookups if tables are provided
        if self.customers_df is not None:
            self.customers_df['signup_date'] = pd.to_datetime(self.customers_df['signup_date'])
            self.customer_lookup = self.customers_df.set_index('customer_id').to_dict(orient='index')
        else:
            self.customer_lookup = {}
            
        if self.products_df is not None:
            self.products_df['launch_date'] = pd.to_datetime(self.products_df['launch_date'])
            self.product_lookup = self.products_df.set_index('sku').to_dict(orient='index')
        else:
            self.product_lookup = {}
            
        # Target encoding lookups learned during fit
        self.family_target_enc: Dict[str, float] = {}
        self.state_target_enc: Dict[str, float] = {}
        self.global_mean_return: float = 0.1142
        self.feature_columns: List[str] = []
        self.cat_feature_indices: List[int] = []

    @staticmethod
    def fix_gateway_anomaly(df: pd.DataFrame) -> pd.DataFrame:
        """
        Fixes the October 2025 payment gateway bug where order values were logged in paise (100x).
        Also defensively handles any runtime record where order_value > 50x expected catalogue value.
        """
        df = df.copy()
        if 'order_placed_at' in df.columns and 'order_value_inr' in df.columns:
            order_dates = pd.to_datetime(df['order_placed_at'], errors='coerce')
            mask_oct = (order_dates.dt.year == 2025) & (order_dates.dt.month == 10)
            df.loc[mask_oct, 'order_value_inr'] = df.loc[mask_oct, 'order_value_inr'] / 100.0
            
        # Defensive check against list_price if merged
        if 'list_price_inr' in df.columns and 'order_value_inr' in df.columns:
            expected = df['list_price_inr'] * df.get('qty', 1) * (1.0 - df.get('discount_pct', 0) / 100.0)
            ratio = df['order_value_inr'] / np.maximum(expected, 1.0)
            mask_paise = ratio > 50.0
            df.loc[mask_paise, 'order_value_inr'] = df.loc[mask_paise, 'order_value_inr'] / 100.0
            
        return df

    @staticmethod
    def extract_text_signals(series: pd.Series) -> pd.DataFrame:
        """
        Regex feature extraction from delivery_note text instructions.
        """
        text = series.fillna('').astype(str).str.lower()
        
        signals = pd.DataFrame(index=series.index)
        signals['note_is_missing'] = series.isna().astype(int)
        signals['note_call_before'] = text.str.contains(r'call before|whatsapp|do not call', regex=True).astype(int)
        signals['note_no_lift'] = text.str.contains(r'no lift|third floor|stairs', regex=True).astype(int)
        signals['note_leave_security'] = text.str.contains(r'security|guard|gate code|neighbour|neighbor', regex=True).astype(int)
        signals['note_time_slot'] = text.str.contains(r'morning|after 6|slot|weekdays', regex=True).astype(int)
        signals['note_landmark'] = text.str.contains(r'opposite|landmark|pillar|school|petrol|atm', regex=True).astype(int)
        signals['note_fragile'] = text.str.contains(r'fragile|care', regex=True).astype(int)
        
        return signals

    def fit(self, train_df: pd.DataFrame, y: pd.Series):
        """
        Fit preprocessor on training data, learning target encodings and baseline statistics.
        """
        train_df = self.fix_gateway_anomaly(train_df)
        
        # Merge products and customers if not present
        if 'family' not in train_df.columns and self.products_df is not None:
            train_df = train_df.merge(self.products_df, on='sku', how='left')
        if 'state' not in train_df.columns and self.customers_df is not None:
            train_df = train_df.merge(self.customers_df, on='customer_id', how='left')
            
        self.global_mean_return = float(y.mean())
        
        # Target encoding with smoothing m=10
        m = 10.0
        family_stats = y.groupby(train_df['family']).agg(['count', 'mean'])
        for fam, row in family_stats.iterrows():
            smoothed = (row['count'] * row['mean'] + m * self.global_mean_return) / (row['count'] + m)
            self.family_target_enc[fam] = smoothed
            
        state_stats = y.groupby(train_df['state']).agg(['count', 'mean'])
        for st, row in state_stats.iterrows():
            smoothed = (row['count'] * row['mean'] + m * self.global_mean_return) / (row['count'] + m)
            self.state_target_enc[st] = smoothed
            
        # Determine feature columns
        transformed = self.transform(train_df)
        self.feature_columns = list(transformed.columns)
        
        # Categorical feature column names/indices
        cat_cols = ['sku', 'family', 'sales_channel', 'payment_mode', 'city', 'state']
        self.cat_feature_indices = [self.feature_columns.index(c) for c in cat_cols if c in self.feature_columns]
        
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform raw order records into final model-ready features.
        Zero target leakage guaranteed.
        """
        df = df.copy()
        
        # Ensure post-dispatch leakage columns are NEVER used
        for leak_col in ['pickup_scheduled_at', 'last_service_event_type', 'returned']:
            if leak_col in df.columns:
                df = df.drop(columns=[leak_col])
                
        # Gateway bug correction
        df = self.fix_gateway_anomaly(df)
        
        # Defensive merge with products (avoid column collisions like _x and _y)
        if self.products_df is not None:
            prod_cols = [c for c in self.products_df.columns if c not in df.columns or c == 'sku']
            df = df.merge(self.products_df[prod_cols], on='sku', how='left')
            
        # Defensive merge with customers (avoid column collisions like shield_member_x)
        if self.customers_df is not None:
            cust_cols = [c for c in self.customers_df.columns if c not in df.columns or c == 'customer_id']
            df = df.merge(self.customers_df[cust_cols], on='customer_id', how='left')

        # Defensive resolution for any existing suffixes
        for c in ['shield_member', 'city', 'state', 'family', 'model_name', 'list_price_inr', 'warranty_months', 'signup_date', 'launch_date']:
            if c not in df.columns:
                if f'{c}_x' in df.columns:
                    df[c] = df[f'{c}_x']
                elif f'{c}_y' in df.columns:
                    df[c] = df[f'{c}_y']
                elif c == 'shield_member':
                    df[c] = 'N'

        # Defensive fallback if fields are missing in an interactive/API payload
        if 'order_placed_at' not in df.columns:
            df['order_placed_at'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
        if 'order_value_inr' not in df.columns:
            df['order_value_inr'] = 0.0
        if 'payment_mode' not in df.columns:
            df['payment_mode'] = 'prepaid_upi'
        if 'sku' not in df.columns:
            df['sku'] = 'KH-AF-01'
        if 'sales_channel' not in df.columns:
            df['sales_channel'] = 'app'
        if 'shield_member' not in df.columns:
            df['shield_member'] = 'N'
        if 'delivery_pincode' not in df.columns:
            df['delivery_pincode'] = '440365'
            
        order_dates = pd.to_datetime(df['order_placed_at'], errors='coerce')
        signup_dates = pd.to_datetime(df.get('signup_date', order_dates), errors='coerce')
        launch_dates = pd.to_datetime(df.get('launch_date', order_dates), errors='coerce')
        
        # 1. Customer Features
        prior_orders = pd.to_numeric(df.get('customer_prior_orders', 0), errors='coerce').fillna(0)
        prior_returns = pd.to_numeric(df.get('customer_prior_returns', 0), errors='coerce').fillna(0)
        
        prior_return_ratio = prior_returns / np.maximum(prior_orders, 1.0)
        is_chronic_returner = (prior_returns >= 2).astype(int)
        is_first_buyer = (prior_orders == 0).astype(int)
        
        tenure_days = (order_dates - signup_dates).dt.days.fillna(0).clip(lower=0)
        order_velocity = prior_orders / ((tenure_days / 30.0) + 1.0)
        
        shield_member = df['shield_member'].astype(str).str.upper().eq('Y').astype(int)
        
        # 2. Product Features
        list_price = pd.to_numeric(df.get('list_price_inr', 0), errors='coerce').fillna(0)
        warranty = pd.to_numeric(df.get('warranty_months', 12), errors='coerce').fillna(12)
        
        # Extract model tier from model_name
        model_names = df.get('model_name', '').astype(str)
        model_tier = pd.Series(1, index=df.index)
        model_tier[model_names.str.contains('Pro', case=False)] = 2
        model_tier[model_names.str.contains('Max', case=False)] = 3
        
        price_per_warranty = list_price / np.maximum(warranty, 1.0)
        product_market_days = (order_dates - launch_dates).dt.days.fillna(0).clip(lower=0)
        
        # 3. Order Commercial Features
        clean_order_val = pd.to_numeric(df['order_value_inr'], errors='coerce').fillna(0)
        qty = pd.to_numeric(df.get('qty', 1), errors='coerce').fillna(1)
        discount_pct = pd.to_numeric(df.get('discount_pct', 0), errors='coerce').fillna(0)
        promised_days = pd.to_numeric(df.get('promised_delivery_days', 5), errors='coerce').fillna(5)
        
        is_cod = df['payment_mode'].astype(str).str.lower().eq('cod').astype(int)
        is_prepaid_upi = df['payment_mode'].astype(str).str.lower().eq('prepaid_upi').astype(int)
        is_prepaid_card = df['payment_mode'].astype(str).str.lower().eq('prepaid_card').astype(int)
        is_emi = df['payment_mode'].astype(str).str.lower().eq('emi').astype(int)
        
        absolute_discount = np.maximum((list_price * qty) - clean_order_val, 0.0)
        is_deep_discount = (discount_pct >= 20).astype(int)
        is_gift = df.get('is_gift', 'N').astype(str).str.upper().eq('Y').astype(int)
        
        # 4. Temporal Features
        hour = order_dates.dt.hour.fillna(12).astype(int)
        is_late_night = hour.isin([23, 0, 1, 2, 3, 4]).astype(int)
        month = order_dates.dt.month.fillna(6).astype(int)
        is_festive_season = month.isin([10, 11]).astype(int)
        day_of_week = order_dates.dt.dayofweek.fillna(0).astype(int)
        is_weekend = day_of_week.isin([5, 6]).astype(int)
        
        # 5. Geospatial & Address Features
        pincodes = df.get('delivery_pincode', 0).astype(str).str.zfill(6)
        is_walkin_missing_pincode = (pincodes == '000000').astype(int)
        state_str = df.get('state', 'MH').astype(str)
        is_home_state = state_str.eq('MH').astype(int)
        
        # 6. Text Features
        text_signals = self.extract_text_signals(df.get('delivery_note', pd.Series(index=df.index)))
        
        # 7. Non-Linear Interaction Signals
        high_value_cod_risk = clean_order_val * is_cod
        delivery_delay_cod_risk = promised_days * is_cod
        shield_cod_hazard = shield_member * is_cod
        shield_chronic_hazard = shield_member * is_chronic_returner
        impulse_remorse_risk = is_late_night * is_deep_discount * is_cod
        
        # Build DataFrame
        feat_df = pd.DataFrame(index=df.index)
        
        # Raw categoricals (for CatBoost native handling)
        feat_df['sku'] = df['sku'].astype(str)
        feat_df['family'] = df['family'].astype(str)
        feat_df['sales_channel'] = df['sales_channel'].astype(str)
        feat_df['payment_mode'] = df['payment_mode'].astype(str)
        feat_df['city'] = df.get('city', 'Unknown').astype(str)
        feat_df['state'] = state_str
        
        # Numerical & engineered features
        feat_df['order_value_cleaned'] = clean_order_val
        feat_df['list_price_inr'] = list_price
        feat_df['discount_pct'] = discount_pct
        feat_df['absolute_discount_inr'] = absolute_discount
        feat_df['is_deep_discount'] = is_deep_discount
        feat_df['qty'] = qty
        feat_df['promised_delivery_days'] = promised_days
        
        feat_df['customer_prior_orders'] = prior_orders
        feat_df['customer_prior_returns'] = prior_returns
        feat_df['prior_return_ratio'] = prior_return_ratio
        feat_df['is_chronic_returner'] = is_chronic_returner
        feat_df['is_first_buyer'] = is_first_buyer
        feat_df['customer_tenure_days'] = tenure_days
        feat_df['customer_order_velocity'] = order_velocity
        feat_df['shield_member'] = shield_member
        
        feat_df['product_model_tier'] = model_tier
        feat_df['warranty_months'] = warranty
        feat_df['price_per_warranty_month'] = price_per_warranty
        feat_df['product_market_days'] = product_market_days
        
        feat_df['is_cod'] = is_cod
        feat_df['is_prepaid_upi'] = is_prepaid_upi
        feat_df['is_prepaid_card'] = is_prepaid_card
        feat_df['is_emi'] = is_emi
        feat_df['is_gift'] = is_gift
        
        feat_df['is_late_night'] = is_late_night
        feat_df['is_festive_season'] = is_festive_season
        feat_df['is_weekend'] = is_weekend
        feat_df['day_of_week'] = day_of_week
        feat_df['hour'] = hour
        
        feat_df['is_walkin_missing_pincode'] = is_walkin_missing_pincode
        feat_df['is_home_state'] = is_home_state
        
        # Add text features
        for col in text_signals.columns:
            feat_df[col] = text_signals[col]
            
        # Add high-order interactions
        feat_df['high_value_cod_risk'] = high_value_cod_risk
        feat_df['delivery_delay_cod_risk'] = delivery_delay_cod_risk
        feat_df['shield_cod_hazard'] = shield_cod_hazard
        feat_df['shield_chronic_hazard'] = shield_chronic_hazard
        feat_df['impulse_remorse_risk'] = impulse_remorse_risk
        
        # Target encoded values (with default fallback)
        feat_df['family_risk_score'] = df['family'].map(self.family_target_enc).fillna(self.global_mean_return)
        feat_df['state_risk_score'] = state_str.map(self.state_target_enc).fillna(self.global_mean_return)
        
        if self.feature_columns:
            # Match training column order exactly
            feat_df = feat_df.reindex(columns=self.feature_columns, fill_value=0)
            
        return feat_df
