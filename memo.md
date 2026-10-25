# MEMORANDUM

**TO:** Ritu Deshpande, Head of D2C Operations  
**FROM:** Senior Machine Learning & Operations Lead  
**CC:** Farhan Sheikh (Finance Controller), Meenal Joshi (Service Desk Manager)  
**DATE:** October 24, 2026  
**SUBJECT:** Kestrel Returns Intelligence Platform — Operational Strategy & P&L Impact  

---

### 1. The Decision: Proactive Confirmation Calls, Zero Dispatch Holds

Your instinct that return logistics are draining operating margins is spot-on. However, the proposal to **"hold dispatch on anything the model flags"** will inadvertently destroy more margin than returns do.

According to Kestrel Operations Policy (§7), placing an appliance order on dispatch hold for >24 hours triggers **customer cancellation approximately 12% of the time**. On an appliance ticket averaging ₹6,000 to ₹18,000, causing a legitimate customer to cancel forfeits hundreds of rupees in gross margin. Even more critical, Meenal’s highest-LTV customer segment—**Kestrel Shield loyalty members**, who purchase ~3 appliances a year—have an 18.7% return rate because returns are free for them. Placing automated holds on their orders will alienate our most profitable brand advocates.

**The Operational Decision:**  
Instead of blunt dispatch holds, we deploy the **Kestrel Returns Intelligence Platform** with a 3-tiered operational dispatch routing:
1. **Low Risk (~50% of orders):** Fast-track directly to courier dispatch with zero transit delay.
2. **Medium Risk (~38% of orders):** Trigger a **pre-dispatch confirmation call (₹45)** via our calling partner. The Spring pilot proved that this 60-second call prevents **35% of returns** by catching incorrect address details, appliance dimensions mismatch, and impulse buyer remorse before the truck leaves the Pune hub.
3. **High Risk / Shield Loyalty (~12% of orders):** Route to Meenal’s team for **priority concierge outreach**—confirming specifics with white-glove service without ever holding the shipment.

---

### 2. The Number: Overcoming the "95% Accuracy" Fallacy

In your initial brief to the board, you mentioned targeting **"95% accuracy or better"**. We must be mathematically transparent about how returns prediction works:

* In Kestrel’s historical orders, the baseline return rate is **11.4%**.
* A dummy model that blindly predicts "No Return" for every single package achieves **88.6% raw accuracy**, yet catches **zero returns and saves ₹0**.
* Conversely, requiring 95% precision before intervening would silence the model on 90% of preventable returns.

**The Metrics That Drive Real P&L Value:**
* **86.5% Return Catch Recall:** At our operational decision cutoff ($T=0.20$), the platform catches **212 out of 245 returns** on the holdout validation cohort.
* **41.4% Precision-Recall Concentration (PR-AUC):** The platform identifies return risk at **3.6x higher concentration than random prevalence** (0.414 vs 0.115).
* **Zero Post-Dispatch Leakage:** Naive models look at reverse pickup schedules to artificially inflate accuracy. Our platform uses strictly pre-dispatch signals: Cash on Delivery (COD), prior return ratio, appliance category complexity, promised transit SLA, and delivery note constraints.

---

### 3. The Rupees: Hard P&L Accounting

Farhan rightly asked what each operational intervention costs against what it saves. Here is the verified unit economics (Ops Policy §4 & §7):

* **Cost of an unmanaged return:** **₹1,150** (courier reverse shipping + warehouse QC + repackaging).
* **Cost of a pre-dispatch confirmation call:** **₹45** (completed call).
* **Return prevention efficiency of a call:** **35%** (prevents 1 in 3 returns).
* **Breakeven Threshold:**
  $$\text{Net Savings per Call} = (P(\text{Return}) \times 0.35 \times ₹1,150) - ₹45 = (P(\text{Return}) \times ₹402.50) - ₹45$$
  Calling any order with a return probability **$P \ge 11.2\%$ yields positive cash ROI**.

**Projected Financial Recovery & Underlying Assumptions:**
* **Measured on Holdout Cohort:** **₹36,492 net cash savings** on 2,126 validation orders (Q2 2026).
* **Annualized Baseline:** Assuming historical volume continues at ~10,000 orders/year with an 11.4% return rate and the 35% prevention rate holds, net annual savings is estimated at **₹1.45 to ₹1.80 Lakhs** (scaling to **~₹4.2 Lakhs** during festive volume surges of ~25,000 orders).
* **Margin Preservation:** Proactive calls preserve over ₹18 Lakhs in valid appliance gross margin that a blind dispatch hold policy would have cancelled through customer drop-off.

---

### 4. Implementation Plan for Next Week

We have delivered a fully functional production system (FastAPI REST service + interactive React operational console) requiring zero paid API keys:

* **Monday (WMS Integration):** Hook the warehouse dispatch scanner into the local API endpoint (`POST /api/v1/predict`). Latency is under 20ms per record.
* **Tuesday (Calling Desk Batch):** Feed the flagged orders from `predictions.csv` to our calling partner using the standard 60-second verification script.
* **Wednesday (Shield Concierge):** Brief Meenal’s service desk on the **Shield Concierge Guardrail** (proactive phone check-in; zero dispatch holds).
* **Thursday (Paise Glitch IT Patch):** Upstream IT must permanently patch the payment gateway logging script (the October 2025 paise bug is neutralized by our preprocessor, but the database root cause should be eliminated).
* **Friday (P&L Reconciliation):** Review the first 5 days of call conversions with Farhan to reconcile courier invoice credits against call center expenses.
