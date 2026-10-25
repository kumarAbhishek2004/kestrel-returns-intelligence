# 3-Minute Walkthrough Screen Recording Script (No Slides)

**System:** Kestrel Returns Intelligence Platform — Pre-Dispatch Return Prevention System  
**Presenter:** Senior Machine Learning Engineer  
**Format:** Live Screen Recording & System Demonstration (Strictly No Slides)  
**Target Duration:** Exactly 180 seconds (3 minutes)

---

## Recording Overview & Screen Setup

* **Screen 1 (0:00 – 1:00):** Terminal / Notebook showing data audit, baseline return rates (11.4%), and multi-model benchmarking.
* **Screen 2 (1:00 – 2:00):** Visualizing data fixes in code (`fix_gateway_anomaly`, deduplication, 5-stage feature ablation, and NLP note extraction).
* **Screen 3 (2:00 – 3:00):** Live browser demonstration of the **Kestrel Returns Intelligence Platform Dashboard** calling `http://localhost:8000` showing the interactive Threshold Slider, SHAP waterfall badges, and Session Prediction Audit log.

---

## Timing & Spoken Script

### [0:00 – 0:58] PART 1: What We Tried

**[SCREEN ACTION: Open terminal or notebook showing data statistics and the 5-model leaderboard.]**

> *"Hi everyone. In this video, I’m walking you through how we designed and built the **Kestrel Returns Intelligence Platform**—an AI operational decision support system to stop return costs before packages leave the warehouse.
> 
> When we received the brief, the initial stakeholder request from Ritu was simple on paper: 'Give us a model with 95% accuracy and hold dispatch on anything it flags.'
> 
> What we tried first was auditing the historical data and establishing multi-model benchmarks. Right away, the data revealed why 95% raw accuracy was a trap: only 11.4% of orders are actually returned. A naive dummy model that predicts 'No Return' for every single package achieves 88.6% accuracy, but it catches zero returns and saves Kestrel zero rupees. 
> 
> We benchmarked five distinct algorithm families: Logistic Regression, Random Forests, LightGBM, XGBoost, and CatBoost with class imbalance weighting. We prioritized Precision-Recall AUC alongside ROC-AUC, lifting return detection concentration to 3.6 times the baseline."*

---

### [0:59 – 1:55] PART 2: What We Changed

**[SCREEN ACTION: Switch to code highlighting `src/preprocessor.py` showing the Oct 2025 gateway fix, deduplication, and 5-stage feature ablation study.]**

> *"Here is what we changed. 
> 
> First, we discovered two major data anomalies that would have destroyed any standard model in production:
> Number one: in October 2025, during the festive surge, the payment gateway logged order values in paise instead of rupees—exactly 100 times higher than list price. We built an automated sanitizer to normalize this.
> Number two: 651 partner-outlet orders had been re-imported twice, creating identical duplicate rows. We deduplicated the training set to 10,504 clean historical orders.
> 
> Next, we changed the feature engineering. Rather than treating delivery notes as unstructured text, we engineered regex NLP signals capturing gate codes, no-lift staircase deliveries, and security desk requests. 
> 
> We conducted a 5-tier Feature Ablation Study: jumping from 0.70 ROC on base order attributes up to 0.781 with customer history, product mechanics, and non-linear interactions like Cash-on-Delivery on Robot Vacuums, where return rates surge past 28%."*

---

### [1:56 – 3:00] PART 3: What We Threw Away & Live Service Demo

**[SCREEN ACTION: Open Browser at `http://localhost:8000`, show the live dashboard: drag the Threshold Slider to 20%, click 'High Risk: COD Robot Vacuum', then click 'Shield Member: Water Purifier', showing the SHAP badges and Prediction History.]**

> *"Finally, here is what we threw away.
> 
> First, we threw away target leakage. In `train.csv`, columns like `pickup_scheduled_at` and `last_service_event_type` contain post-dispatch lifecycle events like `REVERSE_PICKUP`. In the unlabelled test data, `pickup_scheduled_at` is 100% null because at dispatch, reverse pickup hasn't happened yet! Any naive model trained on those columns collapses in production. We completely purged them.
> 
> Second, we threw away the proposal to blindly hold dispatch. Ops Policy §7 clearly states that holding an order for 24 hours causes a 12% customer cancellation rate. Cancelling high-margin appliance sales to avoid a return destroys profitability.
> 
> Instead, we adopted the Spring Pilot confirmation call policy: spending ₹45 on an outbound call prevents 35% of returns, making any order with risk above 11.2% cash-ROI positive.
> 
> Watch the live service in action. Here is our React dashboard running on FastAPI. Notice the interactive Threshold Slider: operations managers can live-tune the trigger cutoff to balance call center capacity against return recall. 
> 
> When we score an order—like this ₹21,999 Robot Vacuum ordered via Cash on Delivery with two prior returns—the engine evaluates it in 18 milliseconds. It flags it as High Risk (70.6%), displays the SHAP factor contributions (+14% COD, +11% Category Risk), calculates expected return costs of ₹812, and routes it to desk review.
> 
> And notice our Shield Guardrail: when a high-LTV Shield customer places an order, the system never puts it on administrative hold; it routes it to priority concierge outreach. Every scored transaction is logged to our live audit history.
> 
> All 2,096 test predictions are saved in `predictions.csv`, and this entire platform runs locally with zero paid API dependencies directly from our README. Thank you."*
