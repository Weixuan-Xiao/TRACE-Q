# Run Summary

- **Prompt version**: v5_guided
- **Run index**: 1
- **Created**: 2026-03-26T00:18:08.215256+00:00
- **Command**: `all`

## Skill Codebook (K=4)

| ID | Skill Name | Definition |
|----|-----------|------------|
| S01 | Align fractional forms | Rewrite quantities so their fractional parts are compatible for subtraction by finding a common denominator, converti... |
| S02 | Normalize mixed numbers | Convert a nonstandard mixed number with an improper fractional part into an equivalent standard mixed number before s... |
| S03 | Subtract aligned parts | Subtract fractions with like denominators and/or subtract the whole-number and fractional parts of mixed numbers once... |
| S04 | Regroup and simplify | Regroup one whole into fractional units when needed to complete subtraction, and simplify the resulting fraction, mix... |

## Q-Matrix Overview

| Item | S01 | S02 | S03 | S04 | Audit |
|------|---|---|---|---|-------|
| FS01 | 1 | 0 | 1 | 0 | ok |
| FS02 | 1 | 0 | 1 | 0 | ok |
| FS03 | 1 | 0 | 1 | 0 | ok |
| FS04 | 0 | 1 | 1 | **1*** | CONTROV |
| FS05 | 1 | 0 | 1 | 1 | ok |
| FS06 | 0 | 0 | 1 | 0 | ok |
| FS07 | 1 | 0 | 1 | 1 | ok |
| FS08 | 0 | 0 | 1 | 1 | ok |
| FS09 | 1 | 0 | 1 | 0 | ok |
| FS10 | 0 | 0 | 1 | 1 | ok |
| FS11 | 0 | 1 | 1 | 0 | ok |
| FS12 | 0 | 0 | 1 | 1 | ok |
| FS13 | 1 | 0 | 1 | 1 | ok |
| FS14 | 0 | 0 | 1 | 0 | ok |
| FS15 | 1 | 0 | 0 | 1 | ok |
| FS16 | 0 | 0 | 1 | 0 | ok |
| FS17 | 1 | 0 | 1 | 1 | ok |
| FS18 | 0 | 0 | 1 | 1 | ok |
| FS19 | 1 | 1 | 1 | 1 | ok |
| FS20 | 0 | 1 | 1 | 1 | ok |

## Pipeline Statistics

- **Verifier corrections**: 0/20 items
- **Full tagger agreement (5/5)**: 0/20 items
- **Supermajority (≥4/5)**: 0/20 items
- **Auditor verdicts**: controversial: 1, correct: 19

---

## Per-Item Trace

### FS01

**Problem**: `5/3 - 3/4`

**Answer**: `11/12`

**Solution steps**:
```
Step1: Find LCD(3,4) = 12. Convert: 5/3 = 20/12, 3/4 = 9/12.
Step2: Subtract: 20/12 − 9/12 = 11/12. Final answer: 11/12
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step1], S03[Step2]
  T2: S01[Step1], S03[Step2]
  T3: S01[Step1], S03[Step2]
  T4: S01[Step1], S03[Step2]
  T5: S01[Step1], S03[Step2]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=0

---

### FS02

**Problem**: `3/4 - 3/8`

**Answer**: `3/8`

**Solution steps**:
```
Step1: This is Type B: pure fractions with unlike denominators.
Step2: Find LCD(4,8) = 8. Convert: 3/4 = 6/8, 3/8 = 3/8.
Step3: Subtract: 6/8 − 3/8 = 3/8. Final answer: 3/8
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step2], S03[Step3]
  T2: S01[Step2], S03[Step3]
  T3: S01[Step2], S03[Step3]
  T4: S01[Step2], S03[Step3]
  T5: S01[Step2], S03[Step3]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=0

---

### FS03

**Problem**: `5/6 - 1/9`

**Answer**: `13/18`

**Solution steps**:
```
Step1: Find LCD(6,9) = 18. Convert: 5/6 = 15/18, 1/9 = 2/18.
Step2: Subtract: 15/18 − 2/18 = 13/18. Final answer: 13/18
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step1], S03[Step2]
  T2: S01[Step1], S03[Step2]
  T3: S01[Step1], S03[Step2]
  T4: S01[Step1], S03[Step2]
  T5: S01[Step1], S03[Step2]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=0

---

### FS04

**Problem**: `3 1/2 - 2 3/2`

**Answer**: `0`

**Solution steps**:
```
Step1: Normalize the mixed number with an improper fraction part: 2 3/2 = 3 1/2.
Step2: Subtract whole parts: 3 − 3 = 0.
Step3: Subtract fraction parts: 1/2 − 1/2 = 0.
Step4: Combine: 0 + 0 = 0. Final answer: 0
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S03[Step2, Step3, Step4]
  T2: S02[Step1], S03[Step2, Step3, Step4]
  T3: S02[Step1], S03[Step2, Step3, Step4]
  T4: S02[Step1], S03[Step2, Step3, Step4]
  T5: S02[Step1], S03[Step2, Step3, Step4]

**Vote tally**:

  S02 (Normalize mixed numbers): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Normalize mixed numbers) conf=1.0, S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CONTROVERSIAL**
  - Add: S04 (Regroup and simplify)
  - Reason: Step1 explicitly normalizes the nonstandard mixed number 2 3/2 into 3 1/2, so S02 is required. Steps2–4 subtract the aligned whole and fractional parts and combine the results, so S03 is required. Step4 explicitly gives the final answer as 0 after combining 0 + 0, and the S04 inclusion criteria state that simplification to a whole number or zero should be tagged when such reduction is shown. Because the current annotation omits S04, I disagree with it. Since taggers also disagreed, this should be marked controversial rather than error.

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=0
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, **S04=1***

---

### FS05

**Problem**: `4 3/5 - 3 4/10`

**Answer**: `1 1/5`

**Solution steps**:
```
Step1: This is Type D: mixed numbers with unlike denominators.
Step2: Find LCD(5,10) = 10. Convert fractions: 3/5 = 6/10, 4/10 = 4/10.
Step3: Subtract whole parts: 4 − 3 = 1.
Step4: Subtract fraction parts: 6/10 − 4/10 = 2/10.
Step5: Simplify: 2/10 = 1/5.
Step6: Combine: 1 1/5. Final answer: 1 1/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step2], S03[Step3, Step4, Step6], S04[Step5]
  T2: S01[Step2], S03[Step3, Step4, Step6], S04[Step5]
  T3: S01[Step2], S03[Step3, Step4, Step6], S04[Step5]
  T4: S01[Step2], S03[Step3, Step4, Step6], S04[Step5]
  T5: S01[Step2], S03[Step3, Step4, Step6], S04[Step5]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=1

---

### FS06

**Problem**: `6/7 - 4/7`

**Answer**: `2/7`

**Solution steps**:
```
Step1: Subtract numerators: (6−4)/7 = 2/7. Final answer: 2/7
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step1]
  T2: S03[Step1]
  T3: S03[Step1]
  T4: S03[Step1]
  T5: S03[Step1]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=0

---

### FS07

**Problem**: `3 - 2 1/5`

**Answer**: `4/5`

**Solution steps**:
```
Step1: Rewrite 3 as 3 + 0/5.
Step2: Subtract whole parts and fraction parts: 3 − 2 = 1, and 0/5 − 1/5 = -1/5.
Step3: Borrow 1 from the whole: 1 − 1 = 0, and 5/5 − 1/5 = 4/5.
Step4: Combine: 0 + 4/5 = 4/5. Final answer: 4/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step1], S03[Step2, Step4], S04[Step3]
  T2: S01[Step1], S03[Step2, Step4], S04[Step3, Step4]
  T3: S01[Step1], S03[Step2], S04[Step3, Step4]
  T4: S01[Step1], S03[Step2, Step4], S04[Step3, Step4]
  T5: S01[Step1], S03[Step2, Step4], S04[Step3, Step4]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=1

---

### FS08

**Problem**: `2/3 - 2/3`

**Answer**: `0`

**Solution steps**:
```
Step1: Subtract numerators: (2−2)/3 = 0/3.
Step2: Simplify: 0/3 = 0. Final answer: 0
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step1], S04[Step2]
  T2: S03[Step1], S04[Step2]
  T3: S03[Step1], S04[Step2]
  T4: S03[Step1], S04[Step2]
  T5: S03[Step1], S04[Step2]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=1

---

### FS09

**Problem**: `3 7/8 - 2`

**Answer**: `1 7/8`

**Solution steps**:
```
Step1: Classify the problem as Type E because it is a mixed number minus a whole number.
Step2: Rewrite 2 as 2 + 0/8.
Step3: Subtract whole parts: 3 − 2 = 1.
Step4: Subtract fraction parts: 7/8 − 0/8 = 7/8.
Step5: Combine: 1 7/8. Final answer: 1 7/8
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step2], S03[Step3, Step4, Step5]
  T2: S01[Step2], S03[Step3, Step4, Step5]
  T3: S01[Step2], S03[Step3, Step4, Step5]
  T4: S01[Step2], S03[Step3, Step4, Step5]
  T5: S01[Step2], S03[Step3, Step4, Step5]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=0

---

### FS10

**Problem**: `4 4/12 - 2 7/12`

**Answer**: `1 3/4`

**Solution steps**:
```
Step1: This is Type C: mixed numbers with the same denominator.
Step2: Subtract whole parts and fraction parts: 4 − 2 = 2, and 4/12 − 7/12 = -3/12.
Step3: Borrow 1 from the whole part: 2 − 1 = 1.
Step4: Add 12/12 to 4/12 and subtract: 16/12 − 7/12 = 9/12.
Step5: Combine and simplify: 1 9/12 = 1 3/4. Final answer: 1 3/4
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step2], S04[Step3, Step4, Step5]
  T2: S03[Step2], S04[Step3, Step4, Step5]
  T3: S03[Step2], S04[Step3, Step4, Step5]
  T4: S03[Step2], S04[Step3, Step4, Step5]
  T5: S03[Step2], S04[Step3, Step4, Step5]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=1

---

### FS11

**Problem**: `4 1/3 - 2 4/3`

**Answer**: `1`

**Solution steps**:
```
Step1: Normalize the mixed number with an improper fraction part: 2 4/3 = 3 1/3.
Step2: Subtract whole parts: 4 − 3 = 1.
Step3: Subtract fraction parts: 1/3 − 1/3 = 0.
Step4: Combine: 1 + 0 = 1. Final answer: 1
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S03[Step2, Step3, Step4]
  T2: S02[Step1], S03[Step2, Step3, Step4]
  T3: S02[Step1], S03[Step2, Step3, Step4]
  T4: S02[Step1], S03[Step2, Step3, Step4]
  T5: S02[Step1], S03[Step2, Step3, Step4]

**Vote tally**:

  S02 (Normalize mixed numbers): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Normalize mixed numbers) conf=1.0, S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=0
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=0

---

### FS12

**Problem**: `1 1/8 - 1/8`

**Answer**: `1`

**Solution steps**:
```
Step1: Classify the problem as Type E since one number is a whole/mixed number and the other is a fraction.
Step2: Rewrite 1 1/8 as 1 + 1/8. Subtract whole parts and fraction parts: 1 − 0 = 1, and 1/8 − 1/8 = 0/8.
Step3: Combine: 1 + 0/8 = 1. Final answer: 1
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step2, Step3], S04[Step3]  optional: S01
  T2: S03[Step2, Step3], S04[Step3]
  T3: S03[Step2, Step3], S04[Step3]  optional: S01
  T4: S03[Step2, Step3], S04[Step3]  optional: S01
  T5: S03[Step2, Step3], S04[Step3]  optional: S01

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=1

---

### FS13

**Problem**: `3 3/8 - 2 5/6`

**Answer**: `13/24`

**Solution steps**:
```
Step1: This is Type D: mixed numbers with unlike denominators.
Step2: Find LCD(8,6) = 24. Convert fractions: 3/8 = 9/24, 5/6 = 20/24.
Step3: Subtract whole parts: 3 − 2 = 1.
Step4: Subtract fraction parts: 9/24 − 20/24 = -11/24.
Step5: Borrow 1 from the whole: 1 − 1 = 0.
Step6: Add 24/24 to the fraction part and subtract: (24/24 + 9/24) − 20/24 = 13/24.
Step7: Combine: 0 13/24 = 13/24. Final answer: 13/24
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step2], S03[Step3, Step4], S04[Step5, Step6, Step7]
  T2: S01[Step2], S03[Step3, Step4], S04[Step5, Step6, Step7]
  T3: S01[Step2], S03[Step3, Step4], S04[Step5, Step6, Step7]
  T4: S01[Step2], S03[Step3, Step4], S04[Step5, Step6, Step7]
  T5: S01[Step2], S03[Step3, Step4], S04[Step5, Step6, Step7]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=1

---

### FS14

**Problem**: `3 4/5 - 3 2/5`

**Answer**: `2/5`

**Solution steps**:
```
Step1: This is Type C: mixed numbers with the same denominator.
Step2: Subtract whole parts: 3 − 3 = 0.
Step3: Subtract fraction parts: 4/5 − 2/5 = 2/5.
Step4: Combine: 0 and 2/5 gives 2/5. Final answer: 2/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step2, Step3, Step4]
  T2: S03[Step2, Step3, Step4]
  T3: S03[Step2, Step3, Step4]
  T4: S03[Step2, Step3, Step4]
  T5: S03[Step2, Step3, Step4]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=0

---

### FS15

**Problem**: `2 - 1/3`

**Answer**: `1 2/3`

**Solution steps**:
```
Step1: Rewrite 2 as 2 + 0/3. Whole: 2 − 0 = 2. Fraction: 0/3 − 1/3 = −1/3.
Step2: Borrow: whole 2 − 1 = 1. Fraction: 3/3 − 1/3 = 2/3.
Step3: Combine: 1 2/3. Final answer: 1 2/3
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step1], S04[Step2]  optional: S03
  T2: S01[Step1], S03[Step1, Step3], S04[Step2]
  T3: S01[Step1], S04[Step2]  optional: S03
  T4: S01[Step1], S04[Step2]  optional: S03
  T5: S01[Step1], S03[Step1, Step3], S04[Step2]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 2/5 [T2, T5] → DISPUTED
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=0.99, S04 (Regroup and simplify) conf=0.99
  _Included S01 and S04 because they have explicit, distinct step evidence: Step1 rewrites 2 as 2 + 0/3 (S01), and Step2 borrows 1 whole and converts it to 3/3 to resolve the negative fractional difference (S04). Excluded disputed S03 despite some direct subtraction appearing in Steps 1 and 3, because those operations are embedded within the alignment and regrouping steps rather than functioning as a separate necessary skill for this item. This satisfies minimality while preserving Rule B completeness: the operator-like work is supported by the explicitly shown precondition/setup (S01) and regrouping step (S04)._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=0, S04=1
**Q-vector (post-audit)**: S01=1, S02=0, S03=0, S04=1

---

### FS16

**Problem**: `4 5/7 - 1 4/7`

**Answer**: `3 1/7`

**Solution steps**:
```
Step1: This is Type C: mixed numbers with the same denominator.
Step2: Subtract whole parts: 4 − 1 = 3.
Step3: Subtract fraction parts: 5/7 − 4/7 = 1/7.
Step4: Combine the results: 3 1/7. Final answer: 3 1/7
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step2, Step3, Step4]
  T2: S03[Step2, Step3, Step4]
  T3: S03[Step2, Step3, Step4]
  T4: S03[Step2, Step3, Step4]
  T5: S03[Step2, Step3, Step4]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S03']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=0

---

### FS17

**Problem**: `7 3/5 - 4/5`

**Answer**: `6 4/5`

**Solution steps**:
```
Step1: Classify the problem as Type E because one number is a whole or mixed number and the other is a fraction.
Step2: Rewrite 7 3/5 as whole and fraction parts, and 4/5 as 0 and 4/5. Whole: 7 − 0 = 7.
Step3: Subtract the fraction parts: 3/5 − 4/5 = -1/5.
Step4: Borrow 1 from the whole: 7 − 1 = 6, and add 5/5 to the fraction part: 5/5 + 3/5 = 8/5.
Step5: Subtract the fraction parts again: 8/5 − 4/5 = 4/5.
Step6: Combine the whole and fraction parts: 6 4/5. Final answer: 6 4/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step2], S03[Step2, Step3, Step5, Step6], S04[Step4]
  T2: S01[Step2], S03[Step2, Step3, Step5, Step6], S04[Step4]
  T3: S01[Step2], S03[Step2, Step3, Step5, Step6], S04[Step4]
  T4: S01[Step2], S03[Step2, Step3, Step5, Step6], S04[Step4]
  T5: S01[Step2], S03[Step2, Step3, Step5, Step6], S04[Step4]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=1, S02=0, S03=1, S04=1

---

### FS18

**Problem**: `4 1/10 - 2 8/10`

**Answer**: `1 3/10`

**Solution steps**:
```
Step1: This is Type C: mixed numbers with the same denominator.
Step2: Subtract whole parts and fraction parts: 4 − 2 = 2, and 1/10 − 8/10 = -7/10.
Step3: Borrow 1 from the whole part: 2 − 1 = 1, and 10/10 + 1/10 = 11/10.
Step4: Subtract the fractions: 11/10 − 8/10 = 3/10.
Step5: Combine the result: 1 3/10. Final answer: 1 3/10
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step2, Step4, Step5], S04[Step3]
  T2: S03[Step2, Step4, Step5], S04[Step3]
  T3: S03[Step2, Step4, Step5], S04[Step3]
  T4: S03[Step2, Step4, Step5], S04[Step3]
  T5: S03[Step2, Step4, Step5], S04[Step3]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=1

---

### FS19

**Problem**: `4 - 1 4/3`

**Answer**: `1 2/3`

**Solution steps**:
```
Step1: Normalize the mixed number: 1 4/3 = 2 1/3.
Step2: Rewrite 4 as 4 + 0/3. Whole: 4 − 2 = 2. Fraction: 0/3 − 1/3 = −1/3.
Step3: Borrow: whole 2 − 1 = 1. Fraction: 3/3 − 1/3 = 2/3.
Step4: Combine: 1 2/3. Final answer: 1 2/3
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S01[Step2], S03[Step2, Step4], S04[Step3]
  T2: S02[Step1], S01[Step2], S03[Step2, Step4], S04[Step3]
  T3: S02[Step1], S01[Step2], S03[Step2, Step4], S04[Step3]
  T4: S02[Step1], S01[Step2], S03[Step2, Step4], S04[Step3]
  T5: S02[Step1], S01[Step2], S03[Step2, Step4], S04[Step3]

**Vote tally**:

  S01 (Align fractional forms): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S02 (Normalize mixed numbers): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Align fractional forms) conf=1.0, S02 (Normalize mixed numbers) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S01', 'S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=1, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=1, S02=1, S03=1, S04=1

---

### FS20

**Problem**: `4 1/3 - 1 5/3`

**Answer**: `1 2/3`

**Solution steps**:
```
Step1: Normalize the mixed number with an improper fraction part: 1 5/3 = 2 2/3.
Step2: Whole: 4 − 2 = 2.
Step3: Fraction: 1/3 − 2/3 = -1/3.
Step4: Borrow: whole 2 − 1 = 1. Fraction: (3/3 + 1/3) − 2/3 = 4/3 − 2/3 = 2/3.
Step5: Combine: 1 2/3. Final answer: 1 2/3
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S03[Step2, Step3, Step5], S04[Step4, Step5]
  T2: S02[Step1], S03[Step2, Step3, Step5], S04[Step4, Step5]
  T3: S02[Step1], S03[Step2, Step3, Step5], S04[Step4]
  T4: S02[Step1], S03[Step2, Step3, Step5], S04[Step4]
  T5: S02[Step1], S03[Step2, Step3, Step5], S04[Step4]

**Vote tally**:

  S02 (Normalize mixed numbers): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and simplify): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Normalize mixed numbers) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and simplify) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

---
