from typing import Dict, Any

class HeuristicFallbackEngine:
    """
    Zero-downtime deterministic rule engine.
    Executes if the machine learning pipeline encounters an unexpected exception.
    """
    
    HIGH_RISK_SKUS = ['KH-RV-01', 'KH-RV-02', 'KH-RV-03', 'KH-WP-01', 'KH-WP-02', 'KH-WP-03']
    
    @classmethod
    def score(cls, d: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates baseline risk probability and recommendation using heuristic business rules.
        """
        score = 0.08  # Baseline Kestrel return rate
        
        # Payment mode
        if str(d.get('payment_mode', '')).lower() == 'cod':
            score += 0.10
            
        # Prior returns
        prior_returns = int(d.get('customer_prior_returns', 0) or 0)
        score += min(prior_returns * 0.15, 0.40)
        
        # Product category
        sku = str(d.get('sku', '')).upper()
        if sku in cls.HIGH_RISK_SKUS:
            score += 0.08
            
        # Delivery days
        delivery_days = int(d.get('promised_delivery_days', 5) or 5)
        if delivery_days >= 8:
            score += 0.06
            
        score = min(max(score, 0.01), 0.95)
        
        reasons = ["Fallback Rule Engine: Scored using deterministic heuristics."]
        if str(d.get('payment_mode', '')).lower() == 'cod':
            reasons.append("Cash on Delivery orders flagged for payment verification.")
        if prior_returns > 0:
            reasons.append(f"Customer has {prior_returns} recorded prior return(s).")
            
        return {
            "return_probability": round(score, 4),
            "reasons": reasons,
            "fallback_used": True
        }
