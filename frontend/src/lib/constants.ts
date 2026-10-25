export const SHAP_DISCLAIMER =
  'SHAP feature attributions describe model input contributions for this sample; features V1–V28 are anonymized PCA components and do not indicate specific real-world identity, location, or customer attributes.'

export const MODEL_ESTIMATE_NOTICE =
  'This is a machine learning model risk estimate, not a human determination of fraud.'

export const V_FEATURE_COUNT = 28
export const PCA_FEATURES: string[] = Array.from({ length: 28 }, (_, i) => `V${i + 1}`)

export const DEFAULT_PAGE_SIZE = 20

export const APP_NAME = 'FraudShield'
export const APP_TAGLINE = 'Financial Risk Operations'
