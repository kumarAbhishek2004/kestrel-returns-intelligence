from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re

class OrderInputSchema(BaseModel):
    order_id: Optional[str] = Field(default="KO-NEW-001", description="Unique order identifier")
    customer_id: str = Field(..., description="Customer ID, e.g. KC105196")
    sku: str = Field(..., description="Product SKU, e.g. KH-RV-01")
    sales_channel: Literal['app', 'web', 'marketplace', 'partner_outlet'] = Field(
        default='app', description="Sales channel"
    )
    payment_mode: Literal['cod', 'prepaid_upi', 'prepaid_card', 'emi'] = Field(
        default='prepaid_upi', description="Payment method"
    )
    discount_pct: int = Field(default=0, ge=0, le=100, description="Discount percentage (0-100)")
    qty: int = Field(default=1, ge=1, le=10, description="Quantity of units")
    order_value_inr: float = Field(..., gt=0, description="Transaction order value in INR")
    promised_delivery_days: int = Field(default=5, ge=1, le=30, description="Promised delivery timeline in days")
    delivery_pincode: Any = Field(default="440365", description="Delivery pincode or 000000")
    is_gift: Literal['Y', 'N'] = Field(default='N', description="Gift order flag")
    customer_prior_orders: Optional[int] = Field(default=None, ge=0, description="Prior order count (auto-filled if omitted)")
    customer_prior_returns: Optional[int] = Field(default=None, ge=0, description="Prior returns count (auto-filled if omitted)")
    delivery_note: Optional[str] = Field(default=None, description="Free text delivery notes")
    shield_member: Optional[Literal['Y', 'N']] = Field(default=None, description="Shield membership status override")

    @field_validator('delivery_pincode')
    def validate_pincode(cls, v):
        s = str(v).strip().zfill(6)
        if not re.match(r'^\d{6}$', s):
            return "000000"
        return s

class PredictionResponseSchema(BaseModel):
    order_id: str
    return_probability: float
    risk_level: Literal['LOW', 'MEDIUM', 'HIGH']
    recommendation: str
    action_code: Literal['FAST_TRACK_DISPATCH', 'TRIGGER_CONFIRMATION_CALL', 'DESK_MANUAL_REVIEW', 'SHIELD_CONCIERGE_OUTREACH']
    expected_return_cost: float
    expected_net_savings: float
    is_shield_member: bool
    reasons: List[str]
    model_version: str
    latency_ms: float
