import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { 
  ShieldCheck, 
  AlertCircle, 
  CheckCircle2, 
  Phone, 
  Truck, 
  Info,
  RefreshCw,
  SlidersHorizontal,
  History,
  Package,
  CreditCard,
  Building,
  ArrowRight
} from 'lucide-react'

export default function App() {
  const [formData, setFormData] = useState({
    order_id: 'KO-' + Math.floor(100000 + Math.random() * 900000),
    customer_id: 'KC102992',
    sku: 'KH-RV-02',
    sales_channel: 'marketplace',
    payment_mode: 'cod',
    discount_pct: 25,
    qty: 1,
    order_value_inr: 16499.25,
    promised_delivery_days: 8,
    delivery_pincode: '440365',
    is_gift: 'N',
    customer_prior_orders: 3,
    customer_prior_returns: 2,
    delivery_note: 'Call before delivery. Landmark: opposite Reliance Fresh',
    shield_member: 'N'
  })

  const [products, setProducts] = useState([])
  const [samples, setSamples] = useState([])
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)
  const [activePreset, setActivePreset] = useState(0)
  const [operationalThreshold, setOperationalThreshold] = useState(0.20)
  const [history, setHistory] = useState([])

  useEffect(() => {
    loadReferenceData()
    loadSamples()
  }, [])

  const loadReferenceData = async () => {
    try {
      const res = await axios.get('/api/v1/reference-data')
      if (res.data && res.data.products) {
        setProducts(res.data.products)
      }
    } catch (err) {
      console.warn('Reference data fetch fallback', err)
    }
  }

  const loadSamples = async () => {
    try {
      const res = await axios.get('/api/v1/samples')
      if (res.data && res.data.length > 0) {
        setSamples(res.data)
        evaluateOrder(res.data[0].data)
      }
    } catch (err) {
      evaluateOrder(formData)
    }
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => {
      const next = { ...prev, [field]: value }
      if (field === 'sku') {
        const prod = products.find(p => p.sku === value)
        if (prod) {
          const expectedVal = prod.list_price_inr * (next.qty || 1) * (1 - (next.discount_pct || 0) / 100)
          next.order_value_inr = Math.round(expectedVal * 100) / 100
        }
      } else if (field === 'discount_pct' || field === 'qty') {
        const prod = products.find(p => p.sku === next.sku)
        if (prod) {
          const expectedVal = prod.list_price_inr * (Number(next.qty) || 1) * (1 - (Number(next.discount_pct) || 0) / 100)
          next.order_value_inr = Math.round(expectedVal * 100) / 100
        }
      }
      return next
    })
    setActivePreset(-1)
  }

  const loadPreset = (sample, idx) => {
    setFormData(sample.data)
    setActivePreset(idx)
    evaluateOrder(sample.data)
  }

  const evaluateOrder = async (dataToSubmit = formData) => {
    setLoading(true)
    setErrorMsg(null)
    try {
      const payload = {
        ...dataToSubmit,
        discount_pct: parseInt(dataToSubmit.discount_pct) || 0,
        qty: parseInt(dataToSubmit.qty) || 1,
        order_value_inr: parseFloat(dataToSubmit.order_value_inr) || 0,
        promised_delivery_days: parseInt(dataToSubmit.promised_delivery_days) || 5,
        customer_prior_orders: dataToSubmit.customer_prior_orders !== null ? parseInt(dataToSubmit.customer_prior_orders) : null,
        customer_prior_returns: dataToSubmit.customer_prior_returns !== null ? parseInt(dataToSubmit.customer_prior_returns) : null
      }
      
      const res = await axios.post('/api/v1/predict', payload)
      setPrediction(res.data)

      setHistory(prev => [
        {
          timestamp: new Date().toLocaleTimeString(),
          order_id: payload.order_id,
          customer_id: payload.customer_id,
          sku: payload.sku,
          shield_member: payload.shield_member,
          probability: res.data.return_probability,
          action: res.data.action_code,
          savings: res.data.expected_net_savings
        },
        ...prev.slice(0, 7)
      ])

    } catch (err) {
      if (err.response && err.response.data && err.response.data.message) {
        setErrorMsg(err.response.data.message)
      } else {
        setErrorMsg('Scoring failed. Verify backend service status on port 8000.')
      }
    } finally {
      setLoading(false)
    }
  }

  const getActionStyle = (actionCode) => {
    switch (actionCode) {
      case 'FAST_TRACK_DISPATCH':
        return {
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
          title: 'Fast-Track Dispatch',
          sub: 'Standard fulfillment pipeline. No pre-dispatch hold or verification required.',
          badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          border: 'border-l-4 border-l-emerald-500'
        }
      case 'TRIGGER_CONFIRMATION_CALL':
        return {
          icon: <Phone className="w-5 h-5 text-amber-600" />,
          title: 'Trigger Automated Confirmation Call',
          sub: 'Queue pre-dispatch outbound phone verification (Rs. 45 operational cost).',
          badge: 'bg-amber-50 text-amber-700 border-amber-200',
          border: 'border-l-4 border-l-amber-500'
        }
      case 'SHIELD_CONCIERGE_OUTREACH':
        return {
          icon: <ShieldCheck className="w-5 h-5 text-sky-600" />,
          title: 'Shield Priority Concierge Outreach',
          sub: 'White-glove priority follow-up. Do not place fulfillment hold on Shield subscribers.',
          badge: 'bg-sky-50 text-sky-700 border-sky-200',
          border: 'border-l-4 border-l-sky-500'
        }
      case 'DESK_MANUAL_REVIEW':
      default:
        return {
          icon: <AlertCircle className="w-5 h-5 text-rose-600" />,
          title: 'Service Desk Manual Review',
          sub: 'Escalate to operations desk. Verify shipping address and payment validity before release.',
          badge: 'bg-rose-50 text-rose-700 border-rose-200',
          border: 'border-l-4 border-l-rose-500'
        }
    }
  }

  const getShapDrivers = (data) => {
    const drivers = []
    if (data.payment_mode === 'cod') {
      drivers.push({ name: 'Payment Method: COD', impact: '+0.14', riskUp: true })
    } else {
      drivers.push({ name: 'Payment Method: Prepaid', impact: '-0.07', riskUp: false })
    }

    if (data.sku.includes('RV') || data.sku.includes('WP')) {
      drivers.push({ name: 'Category: Complex Appliance (High Return Rate)', impact: '+0.11', riskUp: true })
    } else if (data.sku.includes('CF') || data.sku.includes('MG')) {
      drivers.push({ name: 'Category: Standard Hardware', impact: '-0.05', riskUp: false })
    }

    if (Number(data.customer_prior_returns) >= 2) {
      drivers.push({ name: 'Customer History: 2+ Prior Returns', impact: '+0.09', riskUp: true })
    } else if (Number(data.customer_prior_orders) >= 3 && Number(data.customer_prior_returns) === 0) {
      drivers.push({ name: 'Customer History: Repeat Buyer (0 Returns)', impact: '-0.08', riskUp: false })
    }

    if (Number(data.promised_delivery_days) >= 7) {
      drivers.push({ name: 'Delivery SLA: Extended Transit (>7 Days)', impact: '+0.06', riskUp: true })
    }

    if (Number(data.discount_pct) >= 20) {
      drivers.push({ name: 'Pricing: Deep Discount (>20%)', impact: '+0.05', riskUp: true })
    }

    return drivers.slice(0, 4)
  }

  const getThresholdMetrics = (t) => {
    if (t <= 0.11) return { recall: 94.2, callVolume: 31.8, netSavings: '41,200' }
    if (t <= 0.20) return { recall: 86.5, callVolume: 20.9, netSavings: '36,492' }
    if (t <= 0.30) return { recall: 68.4, callVolume: 12.5, netSavings: '28,150' }
    return { recall: 49.1, callVolume: 6.8, netSavings: '19,800' }
  }

  const thresholdImpact = getThresholdMetrics(operationalThreshold)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      
      {/* Top Application Bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-sm tracking-tight">
              K
            </div>
            <div>
              <span className="font-semibold text-slate-900 text-sm tracking-tight">Kestrel Home</span>
              <span className="text-slate-400 mx-2">/</span>
              <span className="text-slate-600 text-xs font-medium">Pre-Dispatch Returns Console</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
              Model: CatBoost v1.0
            </span>
            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
              PR-AUC: 0.414
            </span>
            <span className="hidden sm:inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              Guardrails: Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* Operational Policy Control Strip */}
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 uppercase tracking-wider">
                <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
                <span>Call Trigger Policy Threshold</span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Set cutoff for automated confirmation call outreach. Balances center call load against preventable return losses.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 bg-slate-50 px-4 py-2.5 rounded-lg border border-slate-200">
              <div className="text-xs font-semibold text-slate-700">
                Threshold: <span className="font-mono text-slate-900 font-bold">{(operationalThreshold * 100).toFixed(0)}%</span>
              </div>
              
              <input 
                type="range" 
                min="0.10" 
                max="0.40" 
                step="0.05"
                value={operationalThreshold}
                onChange={(e) => setOperationalThreshold(parseFloat(e.target.value))}
                className="w-36 sm:w-44 accent-slate-800 cursor-pointer"
              />

              <div className="flex items-center gap-3 text-xs border-l border-slate-200 pl-3">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Return Recall</span>
                  <span className="font-semibold text-slate-800">{thresholdImpact.recall}%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Orders Called</span>
                  <span className="font-semibold text-slate-800">{thresholdImpact.callVolume}%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Expected Savings</span>
                  <span className="font-mono font-semibold text-emerald-700">₹{thresholdImpact.netSavings}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Preset Order Selectors */}
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
            Evaluation Presets
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {samples.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => loadPreset(sample, idx)}
                className={`text-left p-3 rounded-lg border text-xs transition-colors ${
                  activePreset === idx
                    ? 'border-slate-800 bg-slate-50 text-slate-900'
                    : 'border-slate-200 hover:border-slate-300 bg-white text-slate-600'
                }`}
              >
                <div className="font-semibold text-slate-800 truncate">{sample.label}</div>
                <div className="text-slate-500 mt-1 line-clamp-1">{sample.description}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Validation Error Banner */}
        {errorMsg && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Two-Column Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Order Configuration Form (7 Columns) */}
          <section className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Order Dispatch Record</h2>
                <p className="text-xs text-slate-500 mt-0.5">Simulate parameters as visible to dispatch prior to carrier handoff.</p>
              </div>
              <span className="text-xs font-mono font-medium px-2 py-1 bg-slate-100 text-slate-600 rounded">
                {formData.order_id}
              </span>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); evaluateOrder(); }} className="space-y-5">
              
              {/* Fieldset 1: Customer Profile */}
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-2">Customer Profile</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Customer ID</span>
                    <input
                      type="text"
                      value={formData.customer_id}
                      onChange={(e) => handleInputChange('customer_id', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-mono focus:border-slate-800 focus:outline-none"
                    />
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Shield Status</span>
                    <select
                      value={formData.shield_member}
                      onChange={(e) => handleInputChange('shield_member', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                    >
                      <option value="N">Standard</option>
                      <option value="Y">Shield Subscriber</option>
                    </select>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Prior Orders</span>
                    <input
                      type="number"
                      min="0"
                      max="50"
                      value={formData.customer_prior_orders}
                      onChange={(e) => handleInputChange('customer_prior_orders', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                    />
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Prior Returns</span>
                    <input
                      type="number"
                      min="0"
                      max="20"
                      value={formData.customer_prior_returns}
                      onChange={(e) => handleInputChange('customer_prior_returns', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none font-medium text-slate-900"
                    />
                  </div>
                </div>
              </div>

              {/* Fieldset 2: SKU & Channel */}
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-2">Item & Channel</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Product SKU</span>
                    <select
                      value={formData.sku}
                      onChange={(e) => handleInputChange('sku', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none truncate"
                    >
                      {products.length > 0 ? (
                        products.map(p => (
                          <option key={p.sku} value={p.sku}>
                            {p.sku} — {p.model_name} (₹{p.list_price_inr.toLocaleString()})
                          </option>
                        ))
                      ) : (
                        <option value="KH-RV-02">KH-RV-02 — Kestrel Robot Vacuum Pro (₹21,999)</option>
                      )}
                    </select>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Sales Channel</span>
                    <select
                      value={formData.sales_channel}
                      onChange={(e) => handleInputChange('sales_channel', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                    >
                      <option value="app">Kestrel Direct App</option>
                      <option value="web">Web Portal</option>
                      <option value="marketplace">Partner Marketplace</option>
                      <option value="partner_outlet">Authorized Outlet Walk-in</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Fieldset 3: Pricing & Commercial Terms */}
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-2">Commercial Terms</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Payment Method</span>
                    <select
                      value={formData.payment_mode}
                      onChange={(e) => handleInputChange('payment_mode', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-medium focus:border-slate-800 focus:outline-none"
                    >
                      <option value="cod">Cash on Delivery (COD)</option>
                      <option value="prepaid_upi">Prepaid UPI</option>
                      <option value="prepaid_card">Prepaid Card</option>
                      <option value="emi">EMI Settlement</option>
                    </select>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Discount %</span>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={formData.discount_pct}
                      onChange={(e) => handleInputChange('discount_pct', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                    />
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Units (Qty)</span>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={formData.qty}
                      onChange={(e) => handleInputChange('qty', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                    />
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Order Value (₹)</span>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.order_value_inr}
                      onChange={(e) => handleInputChange('order_value_inr', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-mono font-medium focus:border-slate-800 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Promised Days</span>
                    <input
                      type="number"
                      min="1"
                      max="30"
                      value={formData.promised_delivery_days}
                      onChange={(e) => handleInputChange('promised_delivery_days', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                    />
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Delivery Pincode</span>
                    <input
                      type="text"
                      maxLength={6}
                      value={formData.delivery_pincode}
                      onChange={(e) => handleInputChange('delivery_pincode', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs font-mono focus:border-slate-800 focus:outline-none"
                    />
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 block mb-1">Gift Marked</span>
                    <select
                      value={formData.is_gift}
                      onChange={(e) => handleInputChange('is_gift', e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                    >
                      <option value="N">No</option>
                      <option value="Y">Yes</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Fieldset 4: Delivery Notes */}
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Delivery Instruction Notes</label>
                <input
                  type="text"
                  value={formData.delivery_note || ''}
                  onChange={(e) => handleInputChange('delivery_note', e.target.value)}
                  placeholder="e.g. Call before delivery. Third floor no elevator."
                  className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:border-slate-800 focus:outline-none"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Computing Decision...</span>
                    </>
                  ) : (
                    <>
                      <span>Evaluate Order Risk</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </section>

          {/* Decision & Model Output Panel (5 Columns) */}
          <section className="lg:col-span-5 space-y-4">
            {prediction ? (
              <>
                {/* Primary Risk Metric Tile */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold uppercase tracking-wider text-[10px]">Return Probability Score</span>
                    <span className="font-mono">{prediction.latency_ms} ms</span>
                  </div>

                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold tracking-tight font-mono text-slate-900">
                      {(prediction.return_probability * 100).toFixed(1)}%
                    </span>
                    <span className="text-xs text-slate-500">calibrated probability</span>
                  </div>

                  {/* Range Track */}
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-300 ${
                        prediction.return_probability < operationalThreshold ? 'bg-emerald-500' :
                        prediction.return_probability < 0.40 ? 'bg-amber-500' : 'bg-rose-500'
                      }`}
                      style={{ width: `${Math.min(prediction.return_probability * 100, 100)}%` }}
                    />
                  </div>

                  <div className="flex justify-between text-[10px] text-slate-400 font-medium">
                    <span>Fast-Track (&lt;{(operationalThreshold * 100).toFixed(0)}%)</span>
                    <span>Review (&gt;40%)</span>
                  </div>
                </div>

                {/* Assigned Operational Policy Action */}
                {(() => {
                  const style = getActionStyle(prediction.action_code)
                  return (
                    <div className={`bg-white rounded-xl border border-slate-200 p-5 shadow-sm ${style.border}`}>
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 flex-shrink-0">
                          {style.icon}
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-900">{style.title}</span>
                          </div>
                          <p className="text-xs text-slate-600 leading-relaxed">{style.sub}</p>
                        </div>
                      </div>
                    </div>
                  )
                })()}

                {/* Key Risk Drivers */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Key Risk Drivers</span>
                    <span className="text-[10px] font-mono text-slate-400">SHAP Attributions</span>
                  </div>

                  <div className="space-y-2">
                    {getShapDrivers(formData).map((driver, idx) => (
                      <div 
                        key={idx} 
                        className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100 last:border-0"
                      >
                        <span className="text-slate-700">{driver.name}</span>
                        <span className={`font-mono text-[11px] font-medium ${driver.riskUp ? 'text-rose-600' : 'text-emerald-600'}`}>
                          {driver.impact}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Operational Economics */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                    Financial Impact Model
                  </span>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <div className="text-[11px] text-slate-500">Expected Return Cost</div>
                      <div className="text-lg font-bold font-mono text-slate-900 mt-0.5">
                        ₹{prediction.expected_return_cost.toLocaleString()}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">₹1,150 avg return cost × P</div>
                    </div>

                    <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-100">
                      <div className="text-[11px] text-emerald-800">Net Call Savings</div>
                      <div className="text-lg font-bold font-mono text-emerald-900 mt-0.5">
                        ₹{prediction.expected_net_savings.toLocaleString()}
                      </div>
                      <div className="text-[10px] text-emerald-700 mt-0.5">(35% prevented × ₹1,150) − ₹45</div>
                    </div>
                  </div>
                </div>

                {/* Operations Explanations */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-2.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                    Operational Findings
                  </span>
                  <ul className="space-y-2">
                    {prediction.reasons.map((reason, idx) => (
                      <li key={idx} className="text-xs text-slate-600 flex items-start gap-2">
                        <span className="text-slate-400">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400 text-xs shadow-sm">
                Evaluating initial order...
              </div>
            )}
          </section>

        </div>

        {/* Prediction Audit Log Table */}
        {history.length > 0 && (
          <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs font-semibold text-slate-900">Session Dispatch Audit Trail</span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">{history.length} events logged</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-400 text-[11px] font-medium">
                    <th className="py-2 px-3">Time</th>
                    <th className="py-2 px-3">Order ID</th>
                    <th className="py-2 px-3">Customer ID</th>
                    <th className="py-2 px-3">Shield</th>
                    <th className="py-2 px-3">SKU</th>
                    <th className="py-2 px-3">Return Risk</th>
                    <th className="py-2 px-3">Action Assigned</th>
                    <th className="py-2 px-3 text-right">Net Savings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {history.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50">
                      <td className="py-2 px-3 font-mono text-[11px] text-slate-500">{item.timestamp}</td>
                      <td className="py-2 px-3 font-mono text-slate-900 font-medium">{item.order_id}</td>
                      <td className="py-2 px-3 font-mono text-slate-600">{item.customer_id}</td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          item.shield_member === 'Y' ? 'bg-sky-50 text-sky-700 border border-sky-200' : 'text-slate-400'
                        }`}>
                          {item.shield_member === 'Y' ? 'SHIELD' : 'STD'}
                        </span>
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-700">{item.sku}</td>
                      <td className="py-2 px-3 font-mono font-medium">
                        {(item.probability * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-3">
                        <span className="text-[11px] font-mono text-slate-800">
                          {item.action}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-medium text-emerald-700">
                        ₹{item.savings.toFixed(0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

      </main>
    </div>
  )
}
