# Q-Matrix Audit Summary Report

Generated: 2026-03-26T14:45:05.438013+00:00

## Overview

- Total items audited: 20
- Correct: 17 (85.0%)
- Errors (corrected): 0 (0.0%)
- Controversial: 3 (15.0%)

## Items Requiring Attention

| Item ID | Verdict | Add Skills | Remove Skills | Reasoning |
|---------|---------|------------|---------------|-----------|
| FS06 | controversial | S06 | - | The solution explicitly performs same-denominator fraction subtraction by subtracting numerators ove... |
| FS11 | controversial | S06 | - | Step 1 explicitly converts the nonstandard mixed number 2 4/3 into the standard mixed number 3 1/3, ... |
| FS12 | controversial | S06 | - | Step 2 explicitly subtracts aligned parts: whole 1 − 0 = 1 and fraction 1/8 − 1/8 = 0/8, so S03 is r... |

## Skill Codebook Reference

| Skill ID | Name | Definition |
|----------|------|------------|
| S01 | Match denominators | Find a common denominator and rewrite fraction parts as equivalent fractions bef... |
| S02 | Normalize operands | Rewrite a whole number or nonstandard mixed number into a subtraction-ready whol... |
| S03 | Subtract aligned parts | Subtract fractions with a common denominator and/or subtract whole-number and fr... |
| S04 | Regroup whole to fraction | Borrow one whole and convert it into fractional units when the minuend’s fractio... |
| S05 | Simplify result | Reduce the computed result to lowest terms or remove zero-valued fractional part... |
| S06 | Compose final answer | Assemble the computed whole and fractional parts and state the answer in final m... |
