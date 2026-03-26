# Q-Matrix Audit Summary Report

Generated: 2026-03-26T18:54:13.065275+00:00

## Overview

- Total items audited: 20
- Correct: 10 (50.0%)
- Errors (corrected): 0 (0.0%)
- Controversial: 10 (50.0%)

## Items Requiring Attention

| Item ID | Verdict | Add Skills | Remove Skills | Reasoning |
|---------|---------|------------|---------------|-----------|
| FS04 | controversial | S03 | - | Step1 explicitly normalizes the nonstandard mixed number 2 3/2 into 3 1/2, so S02 is required. Steps... |
| FS05 | controversial | S03 | - | The solution explicitly matches denominators in Step1, so S01 is required. It then performs componen... |
| FS07 | controversial | S03 | - | Step 1 explicitly rewrites the whole number as 3 + 0/5, which supports S02. The same step also perfo... |
| FS09 | controversial | S03 | - | Step 1 explicitly rewrites the whole number 2 as 2 + 0/8, which matches S02 (Normalize operands), no... |
| FS10 | controversial | S03 | - | The solution explicitly shows direct subtraction of like-denominator fractions in Step2 (4/12 - 7/12... |
| FS11 | controversial | S03 | - | Step 1 explicitly converts the nonstandard mixed number 2 4/3 into the standard mixed number 3 1/3, ... |
| FS12 | controversial | S03 | - | Step 2 explicitly decomposes the mixed number into whole and fractional parts, so S02 is supported. ... |
| FS15 | controversial | S03 | - | The solution explicitly includes normalization of the whole number as 2 + 0/3 (S02), componentwise s... |
| FS18 | controversial | S03 | - | The solution explicitly shows direct subtraction of like-denominator fractions: in Step1, 1/10 - 8/1... |
| FS19 | controversial | S03 | - | Step 1 explicitly normalizes the nonstandard mixed number 1 4/3 to 2 1/3, so S02 is required. Step 2... |

## Skill Codebook Reference

| Skill ID | Name | Definition |
|----------|------|------------|
| S01 | Match denominators | Determine a common denominator and rewrite fraction parts as equivalent fraction... |
| S02 | Normalize operands | Rewrite a whole number, fraction-bearing whole-number expression, or nonstandard... |
| S03 | Subtract aligned fractions | Subtract fractions once they share a denominator by subtracting numerators and k... |
| S04 | Subtract mixed parts | Subtract whole-number parts and fractional parts componentwise in mixed-number o... |
| S05 | Borrow across parts | Regroup one whole as an equivalent fraction and add it to the fractional part wh... |
| S06 | Simplify and express | Reduce the result to lowest terms and present it in an appropriate final form su... |
