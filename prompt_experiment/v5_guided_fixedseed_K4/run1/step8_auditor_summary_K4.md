# Q-Matrix Audit Summary Report

Generated: 2026-03-26T21:00:02.096916+00:00

## Overview

- Total items audited: 20
- Correct: 16 (80.0%)
- Errors (corrected): 0 (0.0%)
- Controversial: 4 (20.0%)

## Items Requiring Attention

| Item ID | Verdict | Add Skills | Remove Skills | Reasoning |
|---------|---------|------------|---------------|-----------|
| FS09 | controversial | S04 | - | Step 1 explicitly rewrites the whole number 2 as 2 + 0/8, which matches S01 (normalize operands). St... |
| FS11 | controversial | S04 | - | Step1 explicitly normalizes the mixed number with an improper fractional part (2 4/3 = 3 1/3), so S0... |
| FS14 | controversial | S04 | - | The solution explicitly uses S03: it subtracts the whole parts separately (3 - 3 = 0) and the fracti... |
| FS16 | controversial | S04 | - | S03 is clearly required because the solution explicitly subtracts the whole parts and the fractional... |

## Skill Codebook Reference

| Skill ID | Name | Definition |
|----------|------|------------|
| S01 | Normalize operands | Rewrite a whole number or mixed number into an equivalent subtraction-ready form... |
| S02 | Align denominators | Find a common denominator and convert one or more fractional parts to equivalent... |
| S03 | Subtract aligned parts | Subtract fractions with like denominators and/or subtract the whole-number and f... |
| S04 | Regroup and simplify | Borrow one whole into fractional units when needed to continue subtraction, and ... |
