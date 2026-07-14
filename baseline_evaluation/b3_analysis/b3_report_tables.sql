CREATE TEMP TABLE stability_chart_data (
  model TEXT, metric TEXT, value REAL, runs_used INTEGER
);
INSERT INTO stability_chart_data VALUES
  ('Claude', 'Modal-K rate', 0.9, 10),
  ('Claude', 'Aligned Q kappa', 0.9476, 9),
  ('Claude', 'Mean ARI', 0.8578, 9),
  ('DeepSeek', 'Modal-K rate', 0.7, 10),
  ('DeepSeek', 'Aligned Q kappa', 0.8320, 7),
  ('DeepSeek', 'Mean ARI', 0.8175, 7),
  ('Gemini', 'Modal-K rate', 1.0, 10),
  ('Gemini', 'Aligned Q kappa', 0.8461, 10),
  ('Gemini', 'Mean ARI', 0.7328, 10),
  ('GPT', 'Modal-K rate', 1.0, 10),
  ('GPT', 'Aligned Q kappa', 0.8421, 10),
  ('GPT', 'Mean ARI', 0.6989, 10);

CREATE TEMP TABLE quality_summary (
  model TEXT, k_distribution TEXT, tsqe_mean REAL, tsqe_sd REAL,
  expert_mean REAL, structural_errors INTEGER, warnings_mean REAL,
  tokens_mean REAL
);
INSERT INTO quality_summary VALUES
  ('Claude Sonnet 5', 'K5:1, K6:9', 0.7375, 0.0246, 0.9198, 0, 4.9, 106928.7),
  ('DeepSeek V4 Flash', 'K4:1, K5:7, K6:2', 0.7217, 0.0254, 0.9276, 0, 3.6, 98045.9),
  ('Gemini 3.5 Flash', 'K5:10', 0.7100, 0.0211, 0.9230, 0, 3.6, 54153.8),
  ('GPT-5.5', 'K5:10', 0.6970, 0.0279, 0.9220, 0, 3.1, 36393.7);

CREATE TEMP TABLE stability_summary (
  model TEXT, modal_k INTEGER, modal_k_runs INTEGER, aligned_kappa REAL,
  element_agreement REAL, mean_ari REAL, min_ari REAL,
  aligned_unique_q INTEGER, modal_q_rate REAL
);
INSERT INTO stability_summary VALUES
  ('Claude Sonnet 5', 6, 9, 0.9476, 0.9870, 0.8578, 0.6345, 4, 0.6667),
  ('DeepSeek V4 Flash', 5, 7, 0.8320, 0.9571, 0.8175, 0.6063, 3, 0.7143),
  ('Gemini 3.5 Flash', 5, 10, 0.8461, 0.9520, 0.7328, 0.5546, 5, 0.6000),
  ('GPT-5.5', 5, 10, 0.8421, 0.9550, 0.6989, 0.5540, 6, 0.4000);

CREATE TEMP TABLE aggregation_summary (
  model TEXT, sample_k_distribution TEXT, samples_retained INTEGER,
  retained_rate REAL, tied_modal_k_runs INTEGER, even_vote_runs INTEGER,
  medoid_tie_runs INTEGER, medoid_tie_cells INTEGER, successful_calls INTEGER,
  temperature_fallbacks INTEGER, samples_excluded_structure INTEGER
);
INSERT INTO aggregation_summary VALUES
  ('Claude Sonnet 5', 'K5:7, K6:37, K7:6', 39, 0.78, 0, 3, 3, 8, 52, 0, 0),
  ('DeepSeek V4 Flash', 'K3:2, K4:4, K5:23, K6:15, K7:5, K8:1', 28, 0.56, 1, 6, 3, 32, 50, 0, 4),
  ('Gemini 3.5 Flash', 'K4:3, K5:47', 47, 0.94, 0, 3, 1, 4, 75, 0, 0),
  ('GPT-5.5', 'K4:7, K5:43', 43, 0.86, 0, 7, 5, 42, 50, 50, 0);

CREATE TEMP TABLE skill_summary (
  model TEXT, raw_skill_instances INTEGER, canonical_skills INTEGER,
  core_skills INTEGER, modal_set_runs INTEGER, modal_set_rate REAL,
  distinct_sets INTEGER
);
INSERT INTO skill_summary VALUES
  ('Claude Sonnet 5', 59, 6, 5, 9, 0.9, 2),
  ('DeepSeek V4 Flash', 51, 9, 3, 6, 0.6, 5),
  ('Gemini 3.5 Flash', 50, 5, 5, 10, 1.0, 1),
  ('GPT-5.5', 50, 7, 3, 9, 0.9, 2);

CREATE TEMP TABLE fit_k5 (
  model TEXT, runs INTEGER, aic REAL, bic REAL, rmsea2 REAL,
  rmsea_runs INTEGER, srmsr REAL
);
INSERT INTO fit_k5 VALUES
  ('Claude Sonnet 5', 1, 9147.5525, 9897.2759, 0.0449, 1, 0.0757),
  ('DeepSeek V4 Flash', 7, 9145.5829, 9827.9842, 0.0389, 7, 0.0787),
  ('Gemini 3.5 Flash', 10, 9130.7594, 9812.7935, 0.0498, 10, 0.0756),
  ('GPT-5.5', 10, 9067.6497, 9842.2211, 0.0377, 9, 0.0602);

SELECT * FROM stability_chart_data;
SELECT * FROM quality_summary;
SELECT * FROM stability_summary;
SELECT * FROM aggregation_summary;
SELECT * FROM skill_summary;
SELECT * FROM fit_k5;
