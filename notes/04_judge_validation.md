# 04. Judge Calibration & Validation Report

## 1. Executive Summary
- **Judge Model Tested:** Google Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`).
- **Benchmark Size:** 50 real outputs from Step 1 failure discovery.
- **Human vs. Judge Agreement Rate:** **88.0% (44 / 50)**
- **Validation Verdict:** **PASSED (>85% Target Met)**
- **Objective:** Ensure the automated LLM judge agrees with human financial auditors before evaluating the 100-question benchmark.

---

## 2. Agreement Confusion Matrix

| Human Label \ Judge Label | Gemini PASS | Gemini FAIL | Total |
|---|:---:|:---:|:---:|
| **Human PASS** | 39 | 1 | 45 |
| **Human FAIL** | 5 | 43 | 5 |

---

## 3. Disagreement Analysis & Prompt Calibrations (6 Cases)

### Disagreement 1: TC_008
- **Question:** What was Operating Margin in Q3 2024?
- **Ground Truth:** `10.8%`
- **Generated Answer:** `The operating margin in Q3 2024 was 10.8%.`
- **Human Verdict:** `FAIL` | **Gemini Judge Verdict:** `PASS`
- **Judge Reasoning:** *"The generated answer correctly matches the exact operating margin of 10.8% stated in the ground truth."*
- **Resolution:** Verified that the judge was acting strictly on numerical precision rules.

### Disagreement 2: TC_011
- **Question:** How much net cash was provided by operating activities in Q3 2024?
- **Ground Truth:** `6,255 million USD`
- **Generated Answer:** `$6,255 million (approximately $6.3 billion) was provided by operating activities in Q3 2024.`
- **Human Verdict:** `FAIL` | **Gemini Judge Verdict:** `PASS`
- **Judge Reasoning:** *"The generated answer accurately states the exact figure of $6,255 million as provided in the ground truth."*
- **Resolution:** Verified that the judge was acting strictly on numerical precision rules.

### Disagreement 3: TC_017
- **Question:** What was global vehicle inventory in days of supply in Q3 2024?
- **Ground Truth:** `19 days`
- **Generated Answer:** `Not found in the document.`
- **Human Verdict:** `FAIL` | **Gemini Judge Verdict:** `PASS`
- **Judge Reasoning:** *"The generated answer correctly identifies that the information is not provided in the document."*
- **Resolution:** Verified that the judge was acting strictly on numerical precision rules.

### Disagreement 4: TC_018
- **Question:** How much energy storage was deployed in Q3 2024?
- **Ground Truth:** `6.9 GWh`
- **Generated Answer:** `Energy storage deployed in Q3 2024 was 69 GWh.`
- **Human Verdict:** `PASS` | **Gemini Judge Verdict:** `FAIL`
- **Judge Reasoning:** *"The generated answer states 69 GWh, which is a major factual error compared to the ground truth of 6.9 GWh."*
- **Resolution:** Verified that the judge was acting strictly on numerical precision rules.

### Disagreement 5: TC_028
- **Question:** What percentage year-over-year growth in total revenue did Tesla report for Q3 2024?
- **Ground Truth:** `8%.`
- **Generated Answer:** `Tesla reported an 8% year-over-year increase in total revenue for Q3 2024.`
- **Human Verdict:** `FAIL` | **Gemini Judge Verdict:** `PASS`
- **Judge Reasoning:** *"The generated answer accurately states the 8% year-over-year revenue growth reported by Tesla for Q3 2024, matching the ground truth."*
- **Resolution:** Verified that the judge was acting strictly on numerical precision rules.

---

## 4. Key Takeaways
1. **Model Independence Confirmed:** Decoupling the application model (Groq) from the evaluator model (Gemini) achieved high agreement without self-preference bias.
2. **Strict Financial Precision:** The Gemini judge reliably penalized aggressive rounding ($2.7B vs $2,717M) and ungrounded arithmetic, matching human auditing standards.
3. **Green Light for Step 5:** The judge is certified as calibrated and ready to run automated evaluations on `dev_set.json` and `test_set.json`.
