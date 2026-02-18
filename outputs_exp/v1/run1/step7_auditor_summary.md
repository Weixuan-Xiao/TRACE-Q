# Q-Matrix Audit Summary Report

Generated: 2026-01-17T00:55:37.033626+00:00

## Overview

- Total items audited: 20
- Correct: 15 (75.0%)
- Errors (corrected): 3 (15.0%)
- Controversial: 2 (10.0%)

## Items Requiring Attention

| Item ID | Verdict | Add Skills | Remove Skills | Reasoning |
|---------|---------|------------|---------------|-----------|
| FS05 | error | S05, S06 | - | Step1 converts mixed numbers to improper fractions (S01) and also simplifies 4/10 to 2/5, which is e... |
| FS10 | error | S06 | S04 | Step1 explicitly uses mixed-number subtraction by separating whole and fractional parts: (4−2) + (4/... |
| FS18 | controversial | S06 | - | Step1 explicitly converts mixed numbers to improper fractions (S01). Step2 subtracts fractions with ... |
| FS19 | error | S06 | - | Step1 explicitly converts the mixed number 1 4/3 into an improper fraction 7/3 (S01). Step2 rewrites... |
| FS20 | controversial | S06 | - | Step1 explicitly converts mixed numbers to improper fractions (S01). Step2 subtracts fractions with ... |

## Skill Codebook Reference

| Skill ID | Name | Definition |
|----------|------|------------|
| S01 | Convert mixed numbers to improper fractions | Rewrite a mixed number as an equivalent improper fraction by converting the whol... |
| S02 | Rewrite whole numbers as equivalent fractions with a specified denominator | Express an integer as an equivalent fraction with a target denominator (often to... |
| S03 | Find and use a common denominator (create equivalent fractions) | Determine a common denominator (often via LCM) and convert each fraction to an e... |
| S04 | Subtract fractions once denominators match | Compute the difference of two fractions with the same denominator by subtracting... |
| S05 | Simplify/reduce fractions to lowest terms | Reduce a fraction by dividing numerator and denominator by a common factor and/o... |
| S06 | Convert improper fractions to mixed numbers or whole numbers | Rewrite an improper fraction as a mixed number or integer by division (quotient ... |
| S07 | Subtract mixed numbers by separating whole and fractional parts | Compute a mixed-number difference by subtracting whole-number parts and fraction... |
