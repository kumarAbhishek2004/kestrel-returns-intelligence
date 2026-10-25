from typing import Dict, Any, List, Tuple

class DecisionEngine:
    """
    Production business decision engine translating raw return probabilities
    into operations actions, cost-benefit savings, and plain-English reasons.
    """
    
    RETURN_COST_INR = 1150.0  # Ops Policy §4
    CALL_COST_INR = 45.0      # Ops Policy §4
    CALL_PREVENTION_RATE = 0.35  # Ops Policy §7
    
    CALL_THRESHOLD = 0.1100   # Empirically validated optimal cutoff
    REVIEW_THRESHOLD = 0.4000 # High-risk desk review cutoff
    
    @classmethod
    def evaluate(cls, prob: float, row_dict: Dict[str, Any], is_shield: bool) -> Dict[str, Any]:
        """
        Calculates operational recommendation, financial impact, and human-readable reasons.
        """
        # Financial Impact
        expected_return_cost = round(prob * cls.RETURN_COST_INR, 2)
        
        # Expected savings from a confirmation call
        # Savings = (P(Return) * 0.35 * 1150) - 45
        potential_savings = (prob * cls.CALL_PREVENTION_RATE * cls.RETURN_COST_INR) - cls.CALL_COST_INR
        expected_net_savings = round(max(potential_savings, 0.0), 2)
        
        # Risk Level & Operational Action
        if prob < cls.CALL_THRESHOLD:
            risk_level = "LOW"
            action_code = "FAST_TRACK_DISPATCH"
            recommendation = "Fast-track dispatch. No customer intervention required."
        elif prob < cls.REVIEW_THRESHOLD:
            risk_level = "MEDIUM"
            action_code = "TRIGGER_CONFIRMATION_CALL"
            recommendation = "Schedule pre-dispatch confirmation call (Rs. 45). Verify delivery address & model fit."
        else:
            risk_level = "HIGH"
            if is_shield:
                # SHIELD GUARDRAIL: Never hold a high-LTV Shield customer's order blindly
                action_code = "SHIELD_CONCIERGE_OUTREACH"
                recommendation = "Shield Concierge Priority. Call customer immediately; DO NOT place blind hold."
            else:
                action_code = "DESK_MANUAL_REVIEW"
                recommendation = "Route to service desk for pre-dispatch verification. Confirm payment & address before shipping."
                
        # Generate Human-Friendly Reasons
        reasons = cls.generate_reasons(prob, row_dict, is_shield)
        
        return {
            "risk_level": risk_level,
            "action_code": action_code,
            "recommendation": recommendation,
            "expected_return_cost": expected_return_cost,
            "expected_net_savings": expected_net_savings,
            "reasons": reasons
        }
        
    @classmethod
    def generate_reasons(cls, prob: float, d: Dict[str, Any], is_shield: bool) -> List[str]:
        """
        Generates actionable, plain-English reasons for the operations team.
        """
        reasons = []
        
        # 1. Payment mode
        payment = str(d.get('payment_mode', '')).lower()
        if payment == 'cod':
            reasons.append("Cash on Delivery (COD) order — historically doubles return and doorstep refusal risk.")
        elif payment in ['prepaid_upi', 'prepaid_card']:
            if prob < cls.CALL_THRESHOLD:
                reasons.append("Prepaid transaction — confirmed buyer financial commitment.")
                
        # 2. Customer history
        prior_returns = int(d.get('customer_prior_returns', 0) or 0)
        prior_orders = int(d.get('customer_prior_orders', 0) or 0)
        if prior_returns >= 2:
            reasons.append(f"Customer has {prior_returns} prior returns ({prior_returns}/{max(prior_orders, 1)} order history) — chronic return pattern.")
        elif prior_returns == 1:
            reasons.append("Customer returned a previous order — elevated return probability.")
        elif prior_orders == 0:
            reasons.append("First-time buyer — no previous appliance purchase track record.")
            
        # 3. Product Family
        family = str(d.get('family', '')).lower()
        sku = str(d.get('sku', '')).upper()
        if 'robot vacuum' in family or 'KH-RV' in sku:
            reasons.append("Product is Robot Vacuum — high-ticket, setup-intensive appliance with highest category return rate (19.5%).")
        elif 'water purifier' in family or 'KH-WP' in sku:
            reasons.append("Product is Water Purifier — installation and plumbing prerequisites increase return likelihood (14.8%).")
        elif 'ceiling fan' in family or 'mixer grinder' in family:
            if prob < cls.CALL_THRESHOLD:
                reasons.append(f"Product is {family.title()} — historically low-return, high-satisfaction category.")
                
        # 4. Promised delivery timeline
        delivery_days = int(d.get('promised_delivery_days', 5) or 5)
        if delivery_days >= 8:
            reasons.append(f"Long delivery window ({delivery_days} days promised) — delivery delays heavily amplify buyer remorse.")
            
        # 5. Discount
        discount = int(d.get('discount_pct', 0) or 0)
        if discount >= 25:
            reasons.append(f"Deep promotional discount ({discount}%) — strongly correlates with impulse markdown purchasing.")
            
        # 6. Shield Status
        if is_shield:
            reasons.append("Kestrel Shield Member — entitled to free 30-day returns; highest lifetime value segment.")
            
        # 7. Delivery note context
        note = str(d.get('delivery_note', '')).lower()
        if 'call before' in note or 'whatsapp' in note:
            reasons.append("Customer delivery note requests phone contact before delivery.")
        if 'no lift' in note or 'third floor' in note:
            reasons.append("Delivery note indicates physical access barrier (no lift / upper floor).")
        if '000000' in str(d.get('delivery_pincode', '')):
            reasons.append("Pincode is 000000 (walk-in partner order with uncaptured shipping address).")
            
        # Ensure at least 2 distinct operational reasons
        if len(reasons) < 2:
            if prob >= cls.CALL_THRESHOLD:
                reasons.append(f"Combined risk score ({prob:.1%}) exceeds the ₹45 confirmation call threshold.")
            else:
                reasons.append("Low overall composite risk score across order, customer, and category features.")
                
        return reasons[:4]
