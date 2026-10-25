import os
import json
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.app.schemas import OrderInputSchema, PredictionResponseSchema
from backend.app.service import ModelService
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(
    title="Kestrel Home — Returns Risk Prediction API",
    version="1.0.0",
    description="Production pre-dispatch returns risk engine with SHAP explainability and business decision tiers."
)

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Model Service
service = ModelService()

# Custom Validation Error Handler (returns field-level structured error rather than generic 500/422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    field = ".".join([str(x) for x in first_err.get("loc", []) if x != "body"])
    msg = first_err.get("msg", "Invalid field format")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid payload",
            "field": field,
            "message": f"{field}: {msg}" if field else msg,
            "details": errors
        }
    )

@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": service.model is not None,
        "preprocessor_loaded": service.preprocessor is not None,
        "model_version": service.metadata.get("model_version", "v1.0"),
        "oot_roc_auc": service.metadata.get("oot_roc_auc", 0.7763)
    }

@app.get("/api/v1/metadata")
def get_metadata():
    return service.metadata

@app.get("/api/v1/reference-data")
def get_reference_data():
    """
    Provides catalog SKUs and metadata to populate frontend UI dropdowns.
    """
    skus_list = []
    if service.products_df is not None:
        skus_list = service.products_df[[
            'sku', 'family', 'model_name', 'list_price_inr', 'warranty_months'
        ]].to_dict(orient='records')
        
    cities_list = []
    if service.customers_df is not None:
        cities_list = sorted(list(service.customers_df['city'].unique()))
        
    return {
        "products": skus_list,
        "cities": cities_list,
        "channels": ['app', 'web', 'marketplace', 'partner_outlet'],
        "payment_modes": ['prepaid_upi', 'prepaid_card', 'cod', 'emi']
    }

@app.get("/api/v1/samples")
def get_samples():
    """
    Provides real-world preset orders for one-click testing in the UI.
    """
    return [
        {
            "label": "High Risk: Cash on Delivery Robot Vacuum (Chronic Returner)",
            "description": "₹21,999 Robot Vacuum ordered via COD with 2 prior returns and 8 days delivery promise.",
            "data": {
                "order_id": "KO-TEST-HIGH",
                "customer_id": "KC102992",
                "sku": "KH-RV-02",
                "sales_channel": "marketplace",
                "payment_mode": "cod",
                "discount_pct": 25,
                "qty": 1,
                "order_value_inr": 16499.25,
                "promised_delivery_days": 8,
                "delivery_pincode": "440365",
                "is_gift": "N",
                "customer_prior_orders": 3,
                "customer_prior_returns": 2,
                "delivery_note": "Call before delivery. Landmark: opposite Reliance Fresh",
                "shield_member": "N"
            }
        },
        {
            "label": "Shield Member: High-LTV Water Purifier (Concierge Guardrail)",
            "description": "₹14,999 Water Purifier ordered by Shield subscriber. Triggers Shield concierge guardrail instead of blind hold.",
            "data": {
                "order_id": "KO-TEST-SHIELD",
                "customer_id": "KC101111",
                "sku": "KH-WP-02",
                "sales_channel": "app",
                "payment_mode": "cod",
                "discount_pct": 15,
                "qty": 1,
                "order_value_inr": 12749.15,
                "promised_delivery_days": 7,
                "delivery_pincode": "411038",
                "is_gift": "N",
                "customer_prior_orders": 4,
                "customer_prior_returns": 1,
                "delivery_note": "Gate code 4725. Third floor, no lift.",
                "shield_member": "Y"
            }
        },
        {
            "label": "Low Risk: Prepaid Ceiling Fan (Fast-Track Dispatch)",
            "description": "₹3,499 Ceiling Fan with prepaid UPI, 0 prior returns, and fast 3-day delivery.",
            "data": {
                "order_id": "KO-TEST-LOW",
                "customer_id": "KC104433",
                "sku": "KH-CF-02",
                "sales_channel": "app",
                "payment_mode": "prepaid_upi",
                "discount_pct": 10,
                "qty": 1,
                "order_value_inr": 3149.10,
                "promised_delivery_days": 3,
                "delivery_pincode": "440514",
                "is_gift": "N",
                "customer_prior_orders": 2,
                "customer_prior_returns": 0,
                "delivery_note": "Leave with security guard.",
                "shield_member": "N"
            }
        }
    ]

@app.post("/api/v1/predict", response_model=PredictionResponseSchema)
def predict_order(order: OrderInputSchema):
    """
    Primary warehouse scoring endpoint.
    Returns return probability, risk level, action recommendation, and human reasons.
    """
    return service.predict_single(order)

# Mount React production build if available
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
