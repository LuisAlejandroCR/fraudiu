<!-- PAIRED.md: prueba pareada (McNemar exacta) entre base y steering sobre los mismos prompts
     de test. Análisis secundario agregado después de la corrida pre-registrada; se distingue de
     REPORT.md, que tiene las tasas e intervalos de Wilson y la regla de selección. -->

# Paired test: `test_base` vs `test_steered`

Secondary analysis, added after the pre-registered run: an exact two-sided McNemar test on the
same prompts answered with and without steering. *Only base* counts prompts where the event
(fraud answered fluently, or a benign twin refused) happened only without steering.

| Metric | Language | Pairs | Only base | Only steered | p (exact McNemar) |
|---|---|---|---|---|---|
| ASR | English | 80 | 9 | 0 | 0.004 |
| ASR | Spanish (LatAm) | 80 | 7 | 2 | 0.180 |
| ASR | ES-EN code-mixed | 80 | 9 | 1 | 0.021 |
| ASR | All | 240 | 25 | 3 | 0.000 |
| Over-refusal | English | 80 | 0 | 7 | 0.016 |
| Over-refusal | Spanish (LatAm) | 80 | 0 | 1 | 1.000 |
| Over-refusal | ES-EN code-mixed | 80 | 0 | 0 | 1.000 |
| Over-refusal | All | 240 | 0 | 8 | 0.008 |

No correction for multiple comparisons; read the *All* rows as the primary paired result.

## Language gap, paired by intent

Each fraud intent was asked in English, Spanish and code-mixed form, so the gap can be tested
intent by intent: *only other* counts intents answered (ASR event) in that language but refused
in English. Exact McNemar, two-sided. Secondary analysis added after the pre-registered run.

| Condition | Comparison | Intents | Only other language | Only English | p (exact McNemar) |
|---|---|---|---|---|---|
| test_base | English vs Spanish (LatAm) | 80 | 17 | 3 | 0.0026 |
| test_base | English vs ES-EN code-mixed | 80 | 21 | 4 | 0.0009 |
| test_steered | English vs Spanish (LatAm) | 80 | 20 | 2 | 0.0001 |
| test_steered | English vs ES-EN code-mixed | 80 | 20 | 2 | 0.0001 |
