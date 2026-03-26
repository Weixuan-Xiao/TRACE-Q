# Run Summary

- **Prompt version**: v5_guided
- **Run index**: 2
- **Created**: 2026-03-26T00:18:08.215256+00:00
- **Command**: `all`

## Skill Codebook (K=4)

| ID | Skill Name | Definition |
|----|-----------|------------|
| S01 | Create common denominator | Find a common denominator and rewrite one or more fractional parts as equivalent fractions with matching denominators... |
| S02 | Rewrite operand form | Rewrite a whole number, mixed number, or nonstandard mixed number into a subtraction-ready form without performing th... |
| S03 | Subtract aligned parts | Carry out subtraction once the quantities are in compatible form, including subtracting like-fraction numerators and/... |
| S04 | Regroup and finalize | When needed, borrow one whole into fractional units and/or express the computed result in lowest terms or final whole... |

## Q-Matrix Overview

| Item | S01 | S02 | S03 | S04 | Audit |
|------|---|---|---|---|-------|
| FS01 | 1 | 0 | 1 | 0 | ok |
| FS02 | 1 | 0 | 1 | 0 | ok |
| FS03 | 1 | 0 | 1 | 0 | ok |
| FS04 | 0 | 1 | 1 | 1 | ok |
| FS05 | 1 | 0 | 1 | 1 | ok |
| FS06 | 0 | 0 | 1 | 0 | ok |
| FS07 | 0 | 1 | 1 | 1 | ok |
| FS08 | 0 | 0 | 1 | 1 | ok |
| FS09 | 0 | 1 | 1 | 1 | ok |
| FS10 | 0 | 0 | 1 | 1 | ok |
| FS11 | 0 | 1 | 1 | 1 | ok |
| FS12 | 0 | 1 | 1 | 1 | ok |
| FS13 | 1 | 0 | 1 | 1 | ok |
| FS14 | 0 | 0 | 1 | 1 | ok |
| FS15 | 0 | 1 | 1 | 1 | ok |
| FS16 | 0 | 0 | 1 | **1*** | CONTROV |
| FS17 | 0 | 1 | 1 | 1 | ok |
| FS18 | 0 | 0 | 1 | 1 | ok |
| FS19 | 0 | 1 | 1 | 1 | ok |
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

  T1: S01[Step1], S03[Step2]  optional: S04
  T2: S01[Step1], S03[Step2]
  T3: S01[Step1], S03[Step2]  optional: S04
  T4: S01[Step1], S03[Step2]  optional: S04
  T5: S01[Step1], S03[Step2]

**Vote tally**:

  S01 (Create common denominator): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Create common denominator) conf=1.0, S03 (Subtract aligned parts) conf=1.0
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

  T1: S01[Step2], S03[Step3]  optional: S04
  T2: S01[Step2], S03[Step3]
  T3: S01[Step2], S03[Step3]  optional: S04
  T4: S01[Step2], S03[Step3]
  T5: S01[Step2], S03[Step3]  optional: S04

**Vote tally**:

  S01 (Create common denominator): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Create common denominator) conf=1.0, S03 (Subtract aligned parts) conf=1.0
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

  T1: S01[Step1], S03[Step2]  optional: S04
  T2: S01[Step1], S03[Step2]
  T3: S01[Step1], S03[Step2]  optional: S04
  T4: S01[Step1], S03[Step2]
  T5: S01[Step1], S03[Step2]  optional: S04

**Vote tally**:

  S01 (Create common denominator): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Create common denominator) conf=1.0, S03 (Subtract aligned parts) conf=1.0
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
Step2: Subtract whole parts and fraction parts: 3 − 3 = 0, and 1/2 − 1/2 = 0.
Step3: Combine the results: 0 + 0 = 0. Final answer: 0
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S03[Step2], S04[Step3]
  T2: S02[Step1], S03[Step2], S04[Step3]
  T3: S02[Step1], S03[Step2], S04[Step3]
  T4: S02[Step1], S03[Step2], S04[Step3]
  T5: S02[Step1], S03[Step2], S04[Step3]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

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
Step6: Combine: 1 and 1/5 = 1 1/5. Final answer: 1 1/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step2], S03[Step3, Step4], S04[Step5, Step6]
  T2: S01[Step2], S03[Step3, Step4], S04[Step5, Step6]
  T3: S01[Step2], S03[Step3, Step4], S04[Step5, Step6]
  T4: S01[Step2], S03[Step3, Step4], S04[Step5, Step6]
  T5: S01[Step2], S03[Step3, Step4], S04[Step5, Step6]

**Vote tally**:

  S01 (Create common denominator): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Create common denominator) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
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

  T1: S03[Step1]  optional: S04
  T2: S03[Step1]  optional: S04
  T3: S03[Step1]  optional: S04
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
Step1: Rewrite 3 as 3 + 0/5. Whole: 3 − 2 = 1. Fraction: 0/5 − 1/5 = −1/5.
Step2: Borrow: whole 1 − 1 = 0. Fraction: 5/5 − 1/5 = 4/5.
Step3: Combine: 0 and 4/5 gives 4/5. Final answer: 4/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S03[Step1], S04[Step2, Step3]
  T2: S02[Step1], S03[Step1], S04[Step2, Step3]
  T3: S02[Step1], S03[Step1], S04[Step2, Step3]
  T4: S02[Step1], S03[Step1], S04[Step2, Step3]
  T5: S02[Step1], S03[Step1], S04[Step2, Step3]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

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
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
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
Step1: Classify the problem as Type E since it is a mixed number minus a whole number.
Step2: Rewrite 2 as 2 + 0/8.
Step3: Subtract whole parts: 3 − 2 = 1.
Step4: Subtract fraction parts: 7/8 − 0/8 = 7/8.
Step5: Combine the results: 1 7/8. Final answer: 1 7/8
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step2], S03[Step3, Step4], S04[Step5]
  T2: S02[Step2], S03[Step3, Step4], S04[Step5]
  T3: S02[Step2], S03[Step3, Step4], S04[Step5]
  T4: S02[Step2], S03[Step3, Step4], S04[Step5]
  T5: S02[Step2], S03[Step3, Step4], S04[Step5]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

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

  T1: S03[Step2, Step4], S04[Step3, Step5]  optional: S02
  T2: S03[Step2, Step4], S04[Step3, Step5]
  T3: S03[Step2, Step4], S04[Step3, Step5]
  T4: S03[Step2, Step4], S04[Step3, Step5]
  T5: S03[Step2, Step4], S04[Step3, Step5]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
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
Step4: Combine the result: 1 + 0 = 1. Final answer: 1
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S03[Step2, Step3], S04[Step4]
  T2: S02[Step1], S03[Step2, Step3], S04[Step4]
  T3: S02[Step1], S03[Step2, Step3], S04[Step4]
  T4: S02[Step1], S03[Step2, Step3], S04[Step4]
  T5: S02[Step1], S03[Step2, Step3], S04[Step4]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

---

### FS12

**Problem**: `1 1/8 - 1/8`

**Answer**: `1`

**Solution steps**:
```
Step1: Classify the problem as Type E since one number is a whole/mixed number and the other is a fraction.
Step2: Rewrite 1 1/8 as whole and fraction parts: 1 + 1/8.
Step3: Subtract the whole parts: 1 − 0 = 1.
Step4: Subtract the fraction parts: 1/8 − 1/8 = 0.
Step5: Combine the results: 1 + 0 = 1. Final answer: 1
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step2], S03[Step3, Step4], S04[Step5]
  T2: S02[Step2], S03[Step3, Step4], S04[Step5]
  T3: S02[Step2], S03[Step3, Step4], S04[Step5]
  T4: S02[Step2], S03[Step3, Step4], S04[Step5]
  T5: S02[Step2], S03[Step3, Step4], S04[Step5]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

---

### FS13

**Problem**: `3 3/8 - 2 5/6`

**Answer**: `13/24`

**Solution steps**:
```
Step1: Find LCD(8,6) = 24. Convert fractions: 3/8 = 9/24, 5/6 = 20/24.
Step2: Subtract whole parts: 3 − 2 = 1.
Step3: Subtract fraction parts: 9/24 − 20/24 = −11/24.
Step4: Borrow 1 from the whole: 1 − 1 = 0.
Step5: Add the borrowed 1 to the fraction: 24/24 + 9/24 = 33/24.
Step6: Subtract the fractions: 33/24 − 20/24 = 13/24.
Step7: Combine: 0 and 13/24 gives 13/24. Final answer: 13/24
```

**Verifier**: ok

**Tagger votes**:

  T1: S01[Step1], S03[Step2, Step3, Step6], S04[Step4, Step5, Step7]  optional: S02
  T2: S01[Step1], S03[Step2, Step3, Step6], S04[Step4, Step5, Step7]
  T3: S01[Step1], S03[Step2, Step3, Step6], S04[Step4, Step5, Step7]
  T4: S01[Step1], S03[Step2, Step3, Step6], S04[Step4, Step5, Step7]
  T5: S01[Step1], S03[Step2, Step3, Step6], S04[Step4, Step5, Step7]

**Vote tally**:

  S01 (Create common denominator): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S01 (Create common denominator) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
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
Step4: Combine the results: 0 + 2/5 = 2/5. Final answer: 2/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step2, Step3]  optional: S04
  T2: S03[Step2, Step3], S04[Step4]
  T3: S03[Step2, Step3], S04[Step4]
  T4: S03[Step2, Step3]  optional: S04
  T5: S03[Step2, Step3], S04[Step4]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 3/5 [T2, T3, T5] → DISPUTED

**Judge decision**: S03 (Subtract aligned parts) conf=0.99, S04 (Regroup and finalize) conf=0.78
  _S03 is strongly supported and auto-included: Step2 subtracts whole parts and Step3 subtracts like-fraction parts, matching the core computation. For disputed S04, I include it because Step4 explicitly performs a finalize action covered by the codebook: combining 0 + 2/5 and expressing the final answer as 2/5. Under Rule A, this explicit finalization step should be tagged unless fully covered by another chosen skill; S03 excludes expressing the final answer, so S04 is not redundant here. No evidence supports S01 or S02 because denominators were already the same and no operand rewriting occurred._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, S04=1

---

### FS15

**Problem**: `2 - 1/3`

**Answer**: `1 2/3`

**Solution steps**:
```
Step1: Rewrite 2 as 1 + 3/3.
Step2: Subtract the fraction parts: 3/3 − 1/3 = 2/3.
Step3: Combine with the whole part: 1 2/3. Final answer: 1 2/3
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1], S03[Step2], S04[Step3]
  T2: S02[Step1], S03[Step2], S04[Step3]
  T3: S02[Step1], S03[Step2], S04[Step3]
  T4: S02[Step1], S03[Step2], S04[Step3]
  T5: S02[Step1], S03[Step2], S04[Step3]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

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

  T1: S03[Step2, Step3]  optional: S04
  T2: S03[Step2, Step3]  optional: S04
  T3: S03[Step2, Step3]  optional: S04
  T4: S03[Step2, Step3], S04[Step4]
  T5: S03[Step2, Step3], S04[Step4]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 2/5 [T4, T5] → DISPUTED

**Judge decision**: S03 (Subtract aligned parts) conf=0.99
  _S03 is strongly supported and auto-included: Step2 subtracts whole parts and Step3 subtracts like-fraction parts, matching the definition exactly. I excluded disputed S04 despite Step4 because the item does not require regrouping or simplification; Step4 only combines already-computed parts into the stated answer form. Under minimality, that final expression is not necessary as a separate skill here, since the essential operations are fully captured by S03 and no Rule B precondition/finalization dependency is triggered beyond the completed subtraction._

**Audit verdict**: **CONTROVERSIAL**
  - Add: S04 (Regroup and finalize)
  - Reason: The solution explicitly performs subtraction of the whole parts and fractional parts separately, so S03 is clearly required. In Step4, the results are combined into the final mixed-number answer '3 1/7,' which matches S04's inclusion criterion for combining whole and fractional parts into the final answer. S01 is not needed because the denominators are already the same, and S02 is not evidenced because no operand rewriting is performed. Since the current annotation omits S04 and taggers had disagreement, the item should be marked controversial rather than error.

**Q-vector (pre-audit)**: S01=0, S02=0, S03=1, S04=0
**Q-vector (post-audit)**: S01=0, S02=0, S03=1, **S04=1***

---

### FS17

**Problem**: `7 3/5 - 4/5`

**Answer**: `6 4/5`

**Solution steps**:
```
Step1: Classify the problem as Type E because a mixed number is being subtracted by a fraction.
Step2: Rewrite 7 3/5 as 7 + 3/5. Whole: 7 − 0 = 7. Fraction: 3/5 − 4/5 = -1/5.
Step3: Borrow 1 from the whole: 7 − 1 = 6. Fraction: 5/5 + 3/5 = 8/5, and 8/5 − 4/5 = 4/5.
Step4: Combine: 6 4/5. Final answer: 6 4/5
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step2], S03[Step2, Step3], S04[Step3, Step4]
  T2: S02[Step2], S03[Step2, Step3], S04[Step3, Step4]
  T3: S02[Step2], S03[Step2, Step3], S04[Step3, Step4]
  T4: S03[Step2, Step3], S04[Step3, Step4]  optional: S02
  T5: S02[Step2], S03[Step2, Step3], S04[Step3, Step4]

**Vote tally**:

  S02 (Rewrite operand form): 4/5 [T1, T2, T3, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

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
Step5: Combine the whole and fraction parts: 1 3/10. Final answer: 1 3/10
```

**Verifier**: ok

**Tagger votes**:

  T1: S03[Step2, Step4], S04[Step3, Step5]
  T2: S03[Step2, Step4], S04[Step3, Step5]
  T3: S03[Step2, Step4], S04[Step3, Step5]
  T4: S03[Step2, Step4], S04[Step3, Step5]
  T5: S03[Step2, Step4], S04[Step3, Step5]

**Vote tally**:

  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
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
Step2: Rewrite the whole number as 4 + 0/3.
Step3: Subtract whole parts and fraction parts: 4 − 2 = 2, and 0/3 − 1/3 = −1/3.
Step4: Borrow 1 from the whole part: 2 − 1 = 1, and 3/3 − 1/3 = 2/3.
Step5: Combine: 1 2/3. Final answer: 1 2/3
```

**Verifier**: ok

**Tagger votes**:

  T1: S02[Step1, Step2], S03[Step3], S04[Step4, Step5]
  T2: S02[Step1, Step2], S03[Step3], S04[Step4, Step5]
  T3: S02[Step1, Step2], S03[Step3], S04[Step4, Step5]
  T4: S02[Step1, Step2], S03[Step3], S04[Step4, Step5]
  T5: S02[Step1, Step2], S03[Step3], S04[Step4, Step5]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

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

  T1: S02[Step1], S03[Step2, Step3], S04[Step4, Step5]
  T2: S02[Step1], S03[Step2, Step3], S04[Step4, Step5]
  T3: S02[Step1], S03[Step2, Step3], S04[Step4, Step5]
  T4: S02[Step1], S03[Step2, Step3], S04[Step4, Step5]
  T5: S02[Step1], S03[Step2, Step3], S04[Step4, Step5]

**Vote tally**:

  S02 (Rewrite operand form): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S03 (Subtract aligned parts): 5/5 [T1, T2, T3, T4, T5] → auto-include
  S04 (Regroup and finalize): 5/5 [T1, T2, T3, T4, T5] → auto-include

**Judge decision**: S02 (Rewrite operand form) conf=1.0, S03 (Subtract aligned parts) conf=1.0, S04 (Regroup and finalize) conf=1.0
  _Skill-level voting: no disputed skills. Auto-included (>=4/5): ['S02', 'S03', 'S04']. Auto-excluded (<=1/5): []._

**Audit verdict**: **CORRECT**

**Q-vector (pre-audit)**: S01=0, S02=1, S03=1, S04=1
**Q-vector (post-audit)**: S01=0, S02=1, S03=1, S04=1

---
