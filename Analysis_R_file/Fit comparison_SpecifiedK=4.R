###############################################################################
# evaluate_fit_v5_K4.R
# Evaluate TRACE-Q step6 and step8 across 20 runs for K=4 (fixed K=4 runs)
# Compare mean fit indices against TSQE and Expert baselines
###############################################################################

library(GDINA)
library(NPCDTools)
set.seed(1)

data      <- GDINA::realdata_Tatsuoka1990$dat
Q_expert  <- GDINA::realdata_Tatsuoka1990$Q
BASE_DIR  <- "/Users/weixuan/Desktop/Agent-Qmatrix/prompt_experiment/v5_guided_fixedseed_K4"
N_RUNS    <- 20

# ---- Helpers ----------------------------------------------------------------
safe_get <- function(mf, field) {
  val <- mf[[field]]
  if (is.null(val) || length(val) == 0) return(NA_real_)
  val[1]
}

extract_fit <- function(dat, Q) {
  mod <- GDINA(dat, Q, verbose = 0)
  mf  <- tryCatch(modelfit(mod), error = function(e) NULL)
  if (!is.null(mf)) {
    data.frame(AIC = safe_get(mf, "AIC"), BIC = safe_get(mf, "BIC"),
               CAIC = safe_get(mf, "CAIC"), SABIC = safe_get(mf, "SABIC"),
               RMSEA2 = safe_get(mf, "RMSEA2"), SRMSR = safe_get(mf, "SRMSR"))
  } else {
    data.frame(AIC = NA, BIC = NA, CAIC = NA, SABIC = NA, RMSEA2 = NA, SRMSR = NA)
  }
}

is_complete <- function(Q) {
  res <- Q.completeness(Q)
  if (is.list(res)) return(isTRUE(res[[1]]))
  isTRUE(res)
}

# ---- Collect TRACE-Q runs ---------------------------------------------------
results_step6 <- data.frame()
results_step8 <- data.frame()
complete_step6 <- logical(0)
complete_step8 <- logical(0)

for (r in 1:N_RUNS) {
  run_dir <- file.path(BASE_DIR, paste0("run", r))
  
  # --- step6 ---
  fpath_s6 <- file.path(run_dir, "step6_Q_matrix_K4.csv")
  if (file.exists(fpath_s6)) {
    Q6 <- read.csv(fpath_s6, row.names = 1)
    complete_step6 <- c(complete_step6, is_complete(Q6))
    results_step6 <- rbind(results_step6, extract_fit(data, Q6))
  }
  
  # --- step8 ---
  fpath_s8 <- file.path(run_dir, "step8_auditor_Q_matrix_K4_reviewed.csv")
  if (file.exists(fpath_s8)) {
    Q8 <- read.csv(fpath_s8)
    Q8 <- Q8[, -c(1, 6)]
    Q8[] <- lapply(Q8, function(x) as.numeric(gsub("[^01]", "", as.character(x))))
    Q8 <- as.data.frame(Q8)
    complete_step8 <- c(complete_step8, is_complete(Q8))
    results_step8 <- rbind(results_step8, extract_fit(data, Q8))
  }
}

# ---- TSQE baseline ----------------------------------------------------------
Q_TSQE4 <- NPCDTools::TSQE(data, K = 4, ref.method = "GDI", GDI.model = "GDINA")
rownames(Q_TSQE4) <- paste0("Item", 1:nrow(Q_TSQE4))
fit_tsqe4  <- extract_fit(data, Q_TSQE4)
comp_tsqe4 <- is_complete(Q_TSQE4)

# ---- Expert baseline ---------------------------------------------------------
fit_expert  <- extract_fit(data, Q_expert)
comp_expert <- is_complete(Q_expert)

# ---- Build summary dataframe -------------------------------------------------
metrics <- c("AIC", "BIC", "CAIC", "SABIC", "RMSEA2", "SRMSR")

mean_s6 <- colMeans(results_step6[, metrics], na.rm = TRUE)
sd_s6   <- apply(results_step6[, metrics], 2, sd, na.rm = TRUE)
mean_s8 <- colMeans(results_step8[, metrics], na.rm = TRUE)
sd_s8   <- apply(results_step8[, metrics], 2, sd, na.rm = TRUE)

fmt <- function(m, s) {
  ifelse(is.na(m) | is.nan(m), NA_character_,
         sprintf("%.2f (%.2f)", m, s))
}

summary_df <- data.frame(
  Q_Matrix = c(
    sprintf("TRACE-Q K=4 step6 (n=%d)", nrow(results_step6)),
    sprintf("TRACE-Q K=4 step8 (n=%d)", nrow(results_step8)),
    "TSQE K=4",
    "Expert K=8"
  ),
  AIC = c(fmt(mean_s6["AIC"], sd_s6["AIC"]),
          fmt(mean_s8["AIC"], sd_s8["AIC"]),
          sprintf("%.2f", fit_tsqe4$AIC),
          sprintf("%.2f", fit_expert$AIC)),
  BIC = c(fmt(mean_s6["BIC"], sd_s6["BIC"]),
          fmt(mean_s8["BIC"], sd_s8["BIC"]),
          sprintf("%.2f", fit_tsqe4$BIC),
          sprintf("%.2f", fit_expert$BIC)),
  CAIC = c(fmt(mean_s6["CAIC"], sd_s6["CAIC"]),
           fmt(mean_s8["CAIC"], sd_s8["CAIC"]),
           sprintf("%.2f", fit_tsqe4$CAIC),
           sprintf("%.2f", fit_expert$CAIC)),
  SABIC = c(fmt(mean_s6["SABIC"], sd_s6["SABIC"]),
            fmt(mean_s8["SABIC"], sd_s8["SABIC"]),
            sprintf("%.2f", fit_tsqe4$SABIC),
            sprintf("%.2f", fit_expert$SABIC)),
  RMSEA2 = c(fmt(mean_s6["RMSEA2"], sd_s6["RMSEA2"]),
             fmt(mean_s8["RMSEA2"], sd_s8["RMSEA2"]),
             sprintf("%.4f", fit_tsqe4$RMSEA2),
             ifelse(is.na(fit_expert$RMSEA2), NA_character_,
                    sprintf("%.4f", fit_expert$RMSEA2))),
  SRMSR = c(fmt(mean_s6["SRMSR"], sd_s6["SRMSR"]),
            fmt(mean_s8["SRMSR"], sd_s8["SRMSR"]),
            sprintf("%.4f", fit_tsqe4$SRMSR),
            sprintf("%.4f", fit_expert$SRMSR)),
  Complete = c(sprintf("%d/%d", sum(complete_step6), nrow(results_step6)),
               sprintf("%d/%d", sum(complete_step8), nrow(results_step8)),
               ifelse(comp_tsqe4, "Yes", "No"),
               ifelse(comp_expert, "Yes", "No")),
  stringsAsFactors = FALSE
)

summary_df