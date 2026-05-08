# Model Card — PropensityModel

- **Model**: Logistic regression + Platt scaling + department rake
- **Output**: calibrated `participation_propensity` in [0, 1]
- **Primary gates**:
  - Brier score < 0.22 (A7)
  - Youth calibration within +/-0.5 pp (A8)
  - Gender calibration within +/-0.2 pp (A9)
  - Department calibration within +/-0.5 pp for exemplars (A10)
- **Known limitations**:
  - Target is synthetic and anchor-calibrated, not externally observed at entity level.
  - Department rake can mask within-department heterogeneity.
