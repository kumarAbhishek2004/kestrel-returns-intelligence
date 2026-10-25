import os
import time
import json
import joblib
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.app.schemas import OrderInputSchema, PredictionResponseSchema
from backend.app.decision_engine import DecisionEngine
from backend.app.fallback import HeuristicFallbackEngine
from src.preprocessor import KestrelPreprocessor

class ModelService:
    def __init__(self, models_dir: str = 'models', datasets_dir: str = 'Datasets'):
        self.models_dir = models_dir
        self.datasets_dir = datasets_dir
        
        self.model = None
        self.preprocessor = None
        self.metadata = {}
        
        # Load reference data
        self.customers_df = None
        self.products_df = None
        self.customer_lookup = {}
        self.product_lookup = {}
        
        self._load_reference_data()
        self._load_artifacts()
        
        # Ensure log directory exists
        os.makedirs('logs', exist_ok=True)
        self.audit_log_path = 'logs/prediction_audit.jsonl'
        
    def _load_reference_data(self):
        try:
            cust_path = os.path.join(self.datasets_dir, '449d665c-c66b-490d-83c6-cca62a0538e2-customers.csv')
            prod_path = os.path.join(self.datasets_dir, 'c9e8afbe-9307-46ff-a798-89bf9b8e3a9c-products.csv')
            if os.path.exists(cust_path) and os.path.exists(prod_path):
                self.customers_df = pd.read_csv(cust_path)
                self.products_df = pd.read_csv(prod_path)
                self.customer_lookup = self.customers_df.set_index('customer_id').to_dict(orient='index')
                self.product_lookup = self.products_df.set_index('sku').to_dict(orient='index')
                print(f"[ModelService] Loaded {len(self.customer_lookup)} customers and {len(self.product_lookup)} products")
        except Exception as e:
            print(f"[ModelService] Warning loading reference data: {e}")

    def _load_artifacts(self):
        try:
            model_path = os.path.join(self.models_dir, 'returns_model_v1.0.joblib')
            prep_path = os.path.join(self.models_dir, 'preprocessor_v1.0.joblib')
            meta_path = os.path.join(self.models_dir, 'metadata.json')
            
            if os.path.exists(model_path) and os.path.exists(prep_path):
                self.model = joblib.load(model_path)
                self.preprocessor = joblib.load(prep_path)
                if os.path.exists(meta_path):
                    with open(meta_path, 'r') as f:
                        self.metadata = json.load(f)
                print(f"[ModelService] Loaded CatBoost model ({self.metadata.get('model_version', 'v1.0')}) and preprocessor")
            else:
                print(f"[ModelService] Artifacts not found at {model_path}. Will use fallback engine.")
        except Exception as e:
            print(f"[ModelService] Error loading artifacts: {e}. Fallback enabled.")

    def predict_single(self, order_input: OrderInputSchema) -> PredictionResponseSchema:
        start_time = time.perf_counter()
        d = order_input.model_dump()
        
        # 1. Enrich with customer reference data if available
        cid = d['customer_id']
        cust_info = self.customer_lookup.get(cid, {})
        
        # Determine shield status: override if provided in input, else from lookup, else 'N'
        is_shield_str = d.get('shield_member') or cust_info.get('shield_member', 'N')
        is_shield = (str(is_shield_str).upper() == 'Y')
        d['shield_member'] = 'Y' if is_shield else 'N'
        
        if 'city' not in d or not d['city']:
            d['city'] = cust_info.get('city', 'Pune')
        if 'state' not in d or not d['state']:
            d['state'] = cust_info.get('state', 'MH')
            
        # 2. Enrich with product reference data
        sku = d['sku']
        prod_info = self.product_lookup.get(sku, {})
        d['family'] = prod_info.get('family', 'Air Fryer')
        d['model_name'] = prod_info.get('model_name', 'Kestrel Appliance Pro')
        d['list_price_inr'] = prod_info.get('list_price_inr', d['order_value_inr'])
        d['warranty_months'] = prod_info.get('warranty_months', 12)
        d['launch_date'] = prod_info.get('launch_date', '2024-01-01')
        
        if 'order_placed_at' not in d or not d['order_placed_at']:
            d['order_placed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            
        # 3. Model Inference with Graceful Fallback
        fallback_used = False
        try:
            if self.model is not None and self.preprocessor is not None:
                single_df = pd.DataFrame([d])
                X_transformed = self.preprocessor.transform(single_df)
                raw_prob = float(self.model.predict_proba(X_transformed)[0, 1])
                prob = round(raw_prob, 4)
            else:
                fallback_res = HeuristicFallbackEngine.score(d)
                prob = fallback_res['return_probability']
                fallback_used = True
        except Exception as e:
            print(f"[ModelService] Prediction exception: {e}. Executing fallback engine.")
            fallback_res = HeuristicFallbackEngine.score(d)
            prob = fallback_res['return_probability']
            fallback_used = True
            
        # 4. Business Decision Engine Evaluation
        eval_result = DecisionEngine.evaluate(prob, d, is_shield)
        
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        response = PredictionResponseSchema(
            order_id=d.get('order_id', 'KO-NEW-001'),
            return_probability=prob,
            risk_level=eval_result['risk_level'],
            recommendation=eval_result['recommendation'],
            action_code=eval_result['action_code'],
            expected_return_cost=eval_result['expected_return_cost'],
            expected_net_savings=eval_result['expected_net_savings'],
            is_shield_member=is_shield,
            reasons=eval_result['reasons'],
            model_version=self.metadata.get('model_version', 'v1.0' if not fallback_used else 'v1.0-fallback'),
            latency_ms=elapsed_ms
        )
        
        # 5. Structured Audit Logging
        self._log_prediction(d, response)
        
        return response

    def _log_prediction(self, input_dict: Dict[str, Any], response: PredictionResponseSchema):
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "order_id": response.order_id,
                "customer_id": input_dict.get('customer_id'),
                "sku": input_dict.get('sku'),
                "payment_mode": input_dict.get('payment_mode'),
                "return_probability": response.return_probability,
                "risk_level": response.risk_level,
                "action_code": response.action_code,
                "latency_ms": response.latency_ms
            }
            with open(self.audit_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"[ModelService] Warning writing audit log: {e}")
