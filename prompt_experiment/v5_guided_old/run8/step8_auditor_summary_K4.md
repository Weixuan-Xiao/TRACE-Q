# Q-Matrix Audit Summary Report

Generated: 2026-03-25T21:11:22.713571+00:00

## Overview

- Total items audited: 20
- Correct: 12 (60.0%)
- Errors (corrected): 0 (0.0%)
- Controversial: 8 (40.0%)

## Items Requiring Attention

| Item ID | Verdict | Add Skills | Remove Skills | Reasoning |
|---------|---------|------------|---------------|-----------|
| FS04 | controversial | - | S04 | The solution explicitly performs subtraction of fractional parts with like denominators: 1/2 − 3/2 =... |
| FS05 | controversial | - | S03 | Step3 explicitly subtracts like-denominator fractions (3/5 − 2/5), so S02 is required. Step1 simplif... |
| FS06 | controversial | - | S04 | The solution explicitly performs subtraction of fractions with a common denominator by subtracting n... |
| FS09 | controversial | - | S02 | The shown work does not actually perform a fraction subtraction of the form a/b − c/b by subtracting... |
| FS11 | controversial | - | S03 | The shown work subtracts fractional parts with a common denominator: 1/3 − 4/3 = (1−4)/3, which dire... |
| FS15 | controversial | S04 | S03 | Step1 explicitly says to "borrow 1" from the whole number and rewrite 2 as 1 3/3 to create a fractio... |
| FS17 | controversial | - | S03 | S02 is evidenced in Steps 2 and 4 where like-denominator fraction subtraction is performed by subtra... |
| FS18 | controversial | - | S03 | The solution explicitly subtracts fractional parts with like denominators (1/10 − 8/10 and 11/10 − 8... |

## Skill Codebook Reference

| Skill ID | Name | Definition |
|----------|------|------------|
| S01 | Common denominator conversion | Determine a least/common denominator (LCD/LCM) and rewrite one or both fractions... |
| S02 | Subtract fractions | Compute the difference of two fractions once they are expressed with the same de... |
| S03 | Rewrite mixed/whole forms | Rewrite numbers into equivalent mixed, improper, or whole-plus-fraction forms to... |
| S04 | Regroup and simplify | Regroup by borrowing 1 from the whole part to fix a negative fractional subtract... |
