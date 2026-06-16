# TruckPro PERF vs PROD Search Evaluation Report

**Date**: 2026-06-15
**Evaluator**: Claude Haiku 4.5 (automated)
**PROD**: search-ecprodauth.truckpro.com
**PERF**: search.tpdevauth.truckpro.com

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total search terms tested | 26 |
| PROD wins | **13** |
| PERF wins | 9 |
| Ties | 4 |
| PROD avg relevance | **6.96 / 10** |
| PERF avg relevance | 6.35 / 10 |
| Overall winner | **PROD** |

**Bottom line**: PERF has regressions in 13 search terms that must be fixed before it can replace PROD. The most critical issues are broken cross-reference matching, reduced index coverage, and degraded multi-term query handling.

---

## PROD Wins: Cases Requiring PERF Fixes

The following 13 search terms perform better in PROD. Each is detailed below with root cause analysis and recommended fix.

---

### 1. B7177 (part_number) — CRITICAL

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **9/10** | 3/10 |
| **Total Results** | 5 | 1 |
| **Expected SKUs Found** | 3/3 | 1/3 |

**What broke**: Cross-reference resolution is completely broken in PERF. Searching "B7177" should return the primary product (BAB7177) plus cross-referenced products (DNP550428, DNP551019, FCLF3970, LULFP3970). PERF only returns BAB7177.

**PROD top 5**:
1. BAB7177 — Baldwin Lube Spin-On (VPN: B7177) — exact match
2. LULFP3970 — Luber-Finer Full Flow Oil Filter (cross-ref match)
3. DNP551019 — Donaldson Full Flow Oil Filter (cross-ref match)
4. FCLF3970 — FleetGuard Oil Filter (cross-ref match)
5. DNP550428 — Donaldson Full Flow Oil Filter (cross-ref match)

**PERF top 5**:
1. BAB7177 — Baldwin Lube Spin-On (VPN: B7177) — only result

**Root cause**: Cross-reference field (`TP_tpcrossref`) is either not indexed or not being queried in PERF.

**Fix required**: Verify that `TP_tpcrossref` field is indexed and included in the search profile query in PERF. This is a data completeness / search profile configuration issue.

---

### 2. 3529900C98 (part_number) — CRITICAL

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **6/10** | 1/10 |
| **Total Results** | 1 | **0** |
| **Expected SKUs Found** | 1/2 | 0/2 |

**What broke**: PERF returns zero results. This is a cross-reference search — 3529900C98 is a cross-ref to RQ888-5125 (Dayton Lamp - Marker). PROD finds RQ888-5125 via cross-ref; PERF finds nothing.

**PROD top result**: RQ888-5125 — Dayton Lamp - Marker (VPN: 888-5125)

**PERF**: No results

**Root cause**: Same as B7177 — cross-reference matching disabled or broken in PERF.

**Fix required**: Restore cross-reference lookup in PERF search profile. Validate `TP_tpcrossref` field indexing.

---

### 3. 308925-25 (part_number) — HIGH

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **9/10** | 5/10 |
| **Total Results** | 6 | 2 |
| **Expected SKUs Found** | 2/2 | 1/2 |

**What broke**: PERF is missing IANMU898-147-6 (Illinois Auto CLUTCH) and 3 other results. The 67% result count reduction suggests a query parsing issue with hyphenated part numbers or broken cross-reference data.

**PROD top 5**:
1. SC308925-25 — Eaton Clutch Assembly (VPN: 308925-25) — exact match
2. SR308925-25MO — Eaton Reman (VPN: 308925-25MO) — partial match
3. IANMU898-147-6 — Illinois Auto CLUTCH (VPN: NMU898-147-6) — cross-ref
4. ROMAF10892525 — Meritor Ez Clutch
5. ROMAF20892525 — Meritor Ez Clutch

**PERF top 2** (only 2 results):
1. SC308925-25 — exact match
2. SR308925-25MO — partial match

**Root cause**: Cross-reference and normalized-no-special-char matching appears degraded. Hyphenated part number "308925-25" is not expanding to related products.

**Fix required**: Verify `normalized_no_special_char` field and cross-reference indexing in PERF. Check that hyphen-stripping normalization is applied consistently.

---

### 4. gunite 1140 (multiple_terms) — HIGH

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **6/10** | 3/10 |
| **Total Results** | 14 | 3 |
| **Expected SKUs Found** | 1/3 | 1/3 |

**What broke**: PERF collapsed from 14 results to 3. Entire product families are missing — all MDAS automatic slack adjusters and secondary GUAS manual slack adjusters gone.

**PROD top 5**:
1. TB1140 — Timken Seal (VPN: 1140) — irrelevant but matches "1140"
2. MDAS1140 — Gunite Brake Adjuster (VPN: AS1140)
3. **GUAS1140** — Gunite Slack Adjuster (VPN: AS1140) — expected top result
4. MDAS1172 — Gunite Brake Slack Adjuster
5. MDAS1138 — Gunite Brake Slack Adjuster

**PERF top 3** (only 3 results):
1. TB1140 — Timken Seal — irrelevant
2. MDAS1140 — Gunite Brake Adjuster
3. GUAS1140 — Gunite Slack Adjuster

**Root cause**: Multi-term query handling is too restrictive in PERF. "gunite 1140" should expand to match products containing either term in name/manufacturer/SKU fields, but PERF appears to require tighter matching, eliminating valid results.

**Fix required**: Review multi-term query logic in PERF. Ensure tokenized search for "gunite" AND "1140" includes wildcard expansion on `normalized_no_special_char`, `custom_stemmed_search`, and name fields. The 78.6% result reduction indicates over-filtering.

**Note**: Both environments have a relevance issue — TB1140 (Timken Seal, unrelated) ranks #1 because "1140" matches its vendor PN. GUAS1140 should be #1 since it matches BOTH terms.

---

### 5. armada 4707q (multiple_terms) — HIGH

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **8/10** | 7/10 |
| **Total Results** | 42 | 27 |
| **Expected SKUs Found** | 4/4 | 2/4 |

**What broke**: PERF is missing 2 expected SKUs (BK4707QPAR23P, BK4707QPV23) and has 36% fewer results.

**PROD top 5** (all Armada + 4707Q — correct):
1. NK4707QPAR1 — Armada NEW KIT
2. LS4707QPARCM — Armada Brake Shoe, Reman
3. LS4707QPAR2 — Armada Brake Shoe, Reman
4. LS4707QPAR1 — Armada Brake Shoe, Reman
5. NK4707QPAR2 — Armada Brake Shoe Kit, New

**PERF top 5** (all Armada + 4707Q — correct but different set):
1. LS4707QPARWBTR — Armada BRK SHOE
2. NK4707QPAR23HD — Armada BRK KIT
3. NK4707QPHS20 — Armada Brake Shoe
4. LS4707QPRK20 — Armada BRK SHOE
5. LS4707QPARWBT — Armada BRK SHOE

**Root cause**: Reduced index coverage in PERF. Both environments correctly prioritize Armada+4707Q products, but PERF is missing products from the index.

**Fix required**: Sync PERF catalog data with PROD. Verify that BK-prefixed kit variants (BK4707QPAR23P, BK4707QPV23) are indexed in PERF.

---

### 6. BK4707 (part_number) — MEDIUM

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **9/10** | 7/10 |
| **Total Results** | 48 | 36 |
| **Expected SKUs Found** | 3/3 | 2/3 |

**What broke**: BK4707QPV23 (expected #1) demoted to rank 2 in PERF. BK4707QPFS20 missing from top 15. 25% fewer total results.

**PROD #1**: BK4707QPV23 — Advantage HD Brake Shoe Kit (correct)
**PERF #1**: BK4707QPEL — Abex Brake Shoe Kit (not expected top)

**Root cause**: Ranking weight for exact prefix match may differ. PERF index missing ~12 products.

**Fix required**: Verify ranking boost for exact SKU prefix matches in PERF search profile. Sync catalog data.

---

### 7. BK4515 (part_number) — MEDIUM

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **7/10** | 6/10 |
| **Total Results** | 65 | 50 |
| **Expected SKUs Found** | ~2/3 | ~2/3 |

**What broke**: 23% fewer results in PERF. Top result (BK4515QAXRN) is less relevant than PROD's top result (BK4515X3AR23HD). Neither environment surfaces exact expected SKUs.

**Fix required**: Sync catalog data to close the 15-result gap. Review ranking to prioritize BK4515X3AR variants.

---

### 8. K2924 (part_number) — MEDIUM

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **9/10** | 8/10 |
| **Total Results** | 18 | 15 |
| **Expected SKUs Found** | 3/3 | 3/3 |

**What broke**: Minor ranking degradation. CRSTK2924 dropped from position 5 to 7. Both find all expected SKUs, but PROD has better ordering. Both environments incorrectly rank HK29248-000 (Hendrickson 7/8-14UNF, VPN: 029248-000) highly — it's irrelevant.

**Fix required**: Suppress false-positive match on HK29248-000 (partial number coincidence). Adjust ranking to push CRSTK2924 higher.

---

### 9. truck-lite (english_word) — MEDIUM

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **8/10** | 7/10 |
| **Total Results** | 3497 | 2855 |
| **Expected SKUs Found** | 2/3 | 2/3 |

**What broke**: 18% fewer results. PERF has heavy presence of OBSOLETE products in top 15 (ranks 4, 5, 8, 9, 11, 12, 13), degrading result quality.

**Fix required**: Apply OBSOLETE product demotion/filtering in PERF ranking. Investigate 642-result index gap.

---

### 10. gladhand seal (english_word) — LOW-MEDIUM

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **8/10** | 7/10 |
| **Total Results** | 26,899 | 23,399 |
| **Expected SKUs Found** | 1/4 | 0/4 |

**What broke**: TQ16110 (Tectran Seal, Gladhand) appears at PROD rank 4 but is missing from PERF top 15. Note: both environments massively over-return (26K/23K vs expected 92).

**Fix required**: Verify TQ16110 indexing in PERF. Both environments need result precision improvement.

---

### 11. gladhand seals (english_word) — LOW-MEDIUM

Same pattern as "gladhand seal". TQ16110 present in PROD (rank 4), absent from PERF top 15. Stemming appears to work correctly (both queries return similar results).

**Fix required**: Same as gladhand seal.

---

### 12. brake chamber (english_word) — LOW

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | 8/10 | 8/10 |
| **Total Results** | 47,130 | 44,501 |
| **Expected SKUs Found** | 1/3 | 1/3 |

**What broke**: Minor ranking shuffles. Both find TVTR24SC but miss MM3531851X and TVTR3030C. Top results are nearly identical (Haldex Spring Brake Chambers).

**Fix required**: Low priority. Verify MM3531851X and TVTR3030C are in PERF catalog. Both environments perform similarly.

---

### 13. air spring (english_word) — LOW-MEDIUM

| | PROD | PERF |
|---|---|---|
| **Relevance Score** | **5/10** | 3/10 |
| **Total Results** | 34,637 | 33,188 |
| **Expected SKUs Found** | 0/3 | 0/3 |

**What broke**: Neither environment surfaces expected VX-series SKUs. PROD at least ranks one actual "AIR SPRING" product at #1 (FAW013589655). PERF's entire top 15 is "AIR BAG" products — no semantic distinction.

**Fix required**: Review synonym configuration. "air spring" and "air bag" may be configured as synonyms, drowning out actual air spring products. Consider adjusting synonym weight or boosting products with exact term match in name/description.

---

## Priority Fix Summary

### Priority 1 — CRITICAL (broken functionality)

| Issue | Affected Terms | Impact |
|-------|---------------|--------|
| **Cross-reference matching broken/disabled** | B7177, 3529900C98, 308925-25 | Customers cannot find products via cross-reference numbers. Complete search failure for some queries. |
| **Multi-term query over-filtering** | gunite 1140 | 78% result reduction. Entire product families missing. |

### Priority 2 — HIGH (significant degradation)

| Issue | Affected Terms | Impact |
|-------|---------------|--------|
| **Catalog data gap / index incompleteness** | armada 4707q, BK4707, BK4515, truck-lite | 15-36% fewer results across part_number and brand queries. Expected products missing from index. |
| **Ranking order degraded** | BK4707, K2924 | Expected top SKUs demoted; less-relevant products ranked higher. |

### Priority 3 — MEDIUM (quality issues)

| Issue | Affected Terms | Impact |
|-------|---------------|--------|
| **OBSOLETE products not demoted** | truck-lite | OBSOLETE products appearing in top 15. |
| **Synonym over-expansion** | air spring | "air spring" returning only "air bag" products. |
| **Baseline SKU absence** | gladhand seal/seals | Tectran products missing from PERF top results. |

### Priority 4 — LOW (minor differences)

| Issue | Affected Terms | Impact |
|-------|---------------|--------|
| **Minor ranking shuffles** | brake chamber | Top results nearly identical; mid-list reordering. |

---

## Where PERF is Better (for reference)

PERF outperforms PROD in 9 cases. These are wins to preserve:

| Term | PERF Score | PROD Score | Why PERF Wins |
|------|-----------|-----------|---------------|
| 4707Q | 6 | 5 | More logical kit-focused ranking |
| K-2924 | 8 | 8 | Count closer to baseline (15 vs 18 vs expected 14) |
| Armada Battery | 6 | 5 | DB1050-4D appears at rank 14 (absent from PROD top 15) |
| air drier | 8 | 5 | Better synonym handling, more relevant top results |
| air dryer | 9 | 6 | Better relevance ordering for dryer products |
| glad hand seal | 8 | 7 | Better surfaces baseline expected SKUs |
| Brake Drum | 6 | 5 | Slightly better relevance, fewer SKU-coincidence matches |
| Wheel nut | 8 | 7 | Better precision, fewer irrelevant results |
| Vent, Axle... | 3 | 2 | Both fail, but PERF marginally closer |

---

## Shared Issues (Both Environments)

These issues affect both PROD and PERF and should be addressed separately:

1. **trucklite** returns 0 results in both environments — normalization of "trucklite" to "truck-lite" is not working
2. **gladhand seal/seals** returns 23K-27K results vs expected 85-92 — massive over-matching
3. **Expected baseline SKUs outdated** — some expected SKUs from the doc may no longer exist in the catalog (e.g., TC16010 vs TQ16010 naming)
4. **Irrelevant ranking from partial SKU matches** — products like TB1140 (Timken Seal) outranking GUAS1140 (Gunite Slack Adjuster) for "gunite 1140"

---

## Appendix: Full Results Matrix

| # | Search Term | Type | PERF Score | PROD Score | Winner | PROD Count | PERF Count | Count Diff |
|---|------------|------|-----------|-----------|--------|-----------|-----------|-----------|
| 1 | 4707Q | part_number | 6 | 5 | PERF | 461 | 399 | -62 |
| 2 | BK4707 | part_number | 7 | 9 | PROD | 48 | 36 | -12 |
| 3 | B7177 | part_number | 3 | 9 | PROD | 5 | 1 | -4 |
| 4 | BK4515 | part_number | 6 | 7 | PROD | 65 | 50 | -15 |
| 5 | VS17573T | part_number | 10 | 10 | TIE | 1 | 1 | 0 |
| 6 | TQ16010 | part_number | 10 | 10 | TIE | 1 | 1 | 0 |
| 7 | HFK-3539 | part_number | 10 | 10 | TIE | 1 | 1 | 0 |
| 8 | K-2924 | part_number | 8 | 8 | PERF | 18 | 15 | -3 |
| 9 | K2924 | part_number | 8 | 9 | PROD | 18 | 15 | -3 |
| 10 | 308925-25 | part_number | 5 | 9 | PROD | 6 | 2 | -4 |
| 11 | 3529900C98 | part_number | 1 | 6 | PROD | 1 | 0 | -1 |
| 12 | armada 4707q | multiple_terms | 7 | 8 | PROD | 42 | 27 | -15 |
| 13 | gunite 1140 | multiple_terms | 3 | 6 | PROD | 14 | 3 | -11 |
| 14 | Armada Battery | multiple_terms | 6 | 5 | PERF | 11,135 | 10,393 | -742 |
| 15 | truck-lite | english_word | 7 | 8 | PROD | 3,497 | 2,855 | -642 |
| 16 | trucklite | english_word | 1 | 1 | TIE | 0 | 0 | 0 |
| 17 | air drier | english_word | 8 | 5 | PERF | 20,923 | 20,277 | -646 |
| 18 | air dryer | english_word | 9 | 6 | PERF | 20,923 | 20,277 | -646 |
| 19 | gladhand seal | english_word | 7 | 8 | PROD | 26,899 | 23,399 | -3,500 |
| 20 | gladhand seals | english_word | 7 | 8 | PROD | 26,899 | 23,399 | -3,500 |
| 21 | glad hand seal | english_word | 8 | 7 | PERF | 33,291 | 29,722 | -3,569 |
| 22 | Brake Drum | english_word | 6 | 5 | PERF | 32,700 | 30,682 | -2,018 |
| 23 | brake chamber | english_word | 8 | 8 | PROD | 47,130 | 44,501 | -2,629 |
| 24 | Wheel nut | english_word | 8 | 7 | PERF | 15,101 | 13,966 | -1,135 |
| 25 | air spring | english_word | 3 | 5 | PROD | 34,637 | 33,188 | -1,449 |
| 26 | Vent, Axle... | english_word | 3 | 2 | PERF | 13,760 | 12,831 | -929 |
