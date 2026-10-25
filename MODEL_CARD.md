# Model Card: Kestrel Returns Risk Classifier (v1.2)

Following the Model Cards for Model Reporting framework (Mitchell et al., 2019).

---

## 1. Model Details
* **Model Name:** Kestrel Returns Risk Classifier (`returns_model_v1.0.joblib`)
* **Model Version:** v1.2 (Regularized Class-Weighted CatBoost)
* **Architecture:** Gradient Boosted Decision Trees (CatBoost Classifier)
* **Release Date:** October 2026
* **Developer:** Senior Machine Learning Engineer, Kestrel Operations Team
* **License / Access:** Internal Operations Use Only (Zero external API dependencies)

---

## 2. Intended Use
* **Primary Intended Use:** Pre-dispatch risk assessment of e-commerce and retail appliance orders to identify high-probability returns before carrier pickup.
* **Primary Intended Users:** Warehouse operations dispatch teams, customer service supervisors, and delivery logistics coordinators at Kestrel Home Appliances (Pune Hub).
* **Out-of-Scope Uses:** 
  * Credit scoring or customer loan underwriting.
  * Automated cancellation of orders without human review.
  * Application to unmapped third-party product categories outside Kestrel's 21 appliance SKUs without fallback rules.

---

## 3. Training & Validation Data
* **Training Dataset:** 8,378 orders from `train.csv` (Temporal window: April 1, 2025 to March 31, 2026).
  * Class Balance: 11.40% returns (955 returned, 7,423 kept).
  * Ingestion Hygiene: 651 partner feed duplicate rows removed; October 2025 paise currency bug normalized.
* **Validation Dataset:** 2,126 orders from `train.csv` (Temporal out-of-time window: April 1, 2026 to June 30, 2026).
  * Class Balance: 11.52% returns (245 returned, 1,881 kept).
* **Test Dataset (Unlabelled):** 2,096 orders from `test_unlabelled.csv` (Scored to `predictions.csv`).
* **Feature Schema:** 43 engineered tabular features across 5 operational levels (Customer History, Product Mechanics, Commercial Terms, Delivery Note NLP, Non-Linear Interactions).
* **Leakage Exclusions:** Strict purging of `pickup_scheduled_at` and `last_service_event_type`.

---

## 4. Performance Metrics (Out-of-Time Validation)
* **Primary Metric (Discrimination):** Out-of-Time ROC-AUC = **0.7804 – 0.7814**
* **Imbalance Metric (Concentration):** Out-of-Time PR-AUC = **0.4139** (3.60x higher than random prevalence baseline of 0.1152)
* **Probability Calibration:** Brier Score Loss = **0.1064**
* **Operating Threshold ($T=0.20$):**
  * Recall: **86.5%** (212 of 245 actual returns captured)
  * Precision: **18.8%**
  * Specificity: **51.3%**
* **Inference Latency:** **18 ms** per record on single CPU thread.

---

## 5. Quantitative Business Assumptions & P&L Impact
* **Cost of Unmanaged Return:** ₹1,150 (courier reverse logistics + QC inspection + repackaging, Ops Policy §4).
* **Cost of Confirmation Call:** ₹45 (completed call, Ops Policy §4).
* **Call Prevention Efficiency:** 35% return reduction on called orders (Spring Pilot, Ops Policy §7).
* **Theoretical Breakeven:** $P^* = \frac{₹45}{0.35 \times ₹1,150} = \mathbf{11.18\%}$.
* **Quarterly Validation Net Savings:** **₹36,492** on 2,126 validation orders.
* **Annualized Net Savings:** **~₹1.45 Lakhs to ₹1.80 Lakhs** across typical baseline volume (~10,000 orders/year), scaling to **~₹4.2 Lakhs** during high-volume festive periods (~25,000 orders/year), assuming prevention rates hold constant.

---

## 6. Operational Guardrails & Limitations
1. **Shield Loyalty Customer Policy:**
   * *Limitation:* Shield members exhibit an 18.1% return rate due to free return privileges. Placing dispatch holds on their orders risks churn of high-LTV accounts (buying ~3 appliances/yr).
   * *Guardrail:* Automated dispatch holds are hard-disabled for Shield members. Orders exceeding threshold are routed to **Priority Concierge Outreach** (white-glove verification, zero dispatch hold).
2. **Cold-Start Fallback (New SKUs / New Customers):**
   * *Limitation:* First-time customers have no prior order history (`customer_prior_orders = 0`).
   * *Mitigation:* The feature pipeline defaults missing behavioral signals to global baseline averages with an active `is_first_buyer` indicator. If CatBoost dependencies fail, an in-memory rule engine (`backend/app/fallback.py`) provides uninterrupted scoring.
3. **Distribution Drift Monitoring:**
   * Two-sample Kolmogorov-Smirnov tests confirmed no statistically significant evidence of distribution drift on `order_value` ($p = 0.513$) and `discount_pct` ($p = 0.983$).
   * P-values on postal carrier transit times should be re-evaluated quarterly.
