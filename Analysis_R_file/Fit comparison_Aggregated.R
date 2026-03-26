###############################################################################
# evaluate_fit_v5_10runs.R
# Output: summary_df — one dataframe comparing TRACE-Q, TSQE, and Expert
###############################################################################

library(GDINA)
library(NPCDTools)
set.seed(1)

data      <- GDINA::realdata_Tatsuoka1990$dat
Q_expert  <- GDINA::realdata_Tatsuoka1990$Q
BASE_DIR  <- "/Users/weixuan/Desktop/Agent-Qmatrix/prompt_experiment/v5_guided_fixedseed"
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

read_Q <- function(fpath, drop_cols) {
  if (!file.exists(fpath)) return(NULL)
  Q <- read.csv(fpath)
  Q <- Q[, -drop_cols]
  Q[] <- lapply(Q, function(x) as.numeric(gsub("[^01]", "", as.character(x))))
  as.data.frame(Q)
}

is_complete <- function(Q) {
  res <- Q.completeness(Q)
  if (is.list(res)) return(isTRUE(res[[1]]))
  isTRUE(res)
}

# ---- Collect TRACE-Q runs ---------------------------------------------------
results_K4 <- data.frame()
results_K6 <- data.frame()
complete_K4 <- logical(0)
complete_K6 <- logical(0)

for (r in 1:N_RUNS) {
  run_dir <- file.path(BASE_DIR, paste0("run", r))
  
  Q6 <- read_Q(file.path(run_dir, "step8_auditor_Q_matrix_K6_reviewed.csv"), c(1, 8))
  if (!is.null(Q6)) {
    complete_K6 <- c(complete_K6, is_complete(Q6))
    results_K6 <- rbind(results_K6, extract_fit(data, Q6))
  }
  
  Q4 <- read_Q(file.path(run_dir, "step8_auditor_Q_matrix_K4_reviewed.csv"), c(1, 6))
  if (!is.null(Q4)) {
    complete_K4 <- c(complete_K4, is_complete(Q4))
    results_K4 <- rbind(results_K4, extract_fit(data, Q4))
  }
}

# ---- TSQE baselines ---------------------------------------------------------
Q_TSQE4 <- NPCDTools::TSQE(data, K = 4, ref.method = "GDI", GDI.model = "GDINA")
rownames(Q_TSQE4) <- paste0("Item", 1:nrow(Q_TSQE4))
fit_tsqe4  <- extract_fit(data, Q_TSQE4)
comp_tsqe4 <- is_complete(Q_TSQE4)

Q_TSQE6 <- NPCDTools::TSQE(data, K = 6, ref.method = "GDI", GDI.model = "GDINA")
rownames(Q_TSQE6) <- paste0("Item", 1:nrow(Q_TSQE6))
fit_tsqe6  <- extract_fit(data, Q_TSQE6)
comp_tsqe6 <- is_complete(Q_TSQE6)

# ---- Expert baseline ---------------------------------------------------------
fit_expert  <- extract_fit(data, Q_expert)
comp_expert <- is_complete(Q_expert)

# ---- Build summary dataframe -------------------------------------------------
metrics <- c("AIC", "BIC", "CAIC", "SABIC", "RMSEA2", "SRMSR")

mean_K4 <- colMeans(results_K4[, metrics], na.rm = TRUE)
sd_K4   <- apply(results_K4[, metrics], 2, sd, na.rm = TRUE)
mean_K6 <- colMeans(results_K6[, metrics], na.rm = TRUE)
sd_K6   <- apply(results_K6[, metrics], 2, sd, na.rm = TRUE)

fmt <- function(m, s) {
  ifelse(is.na(m) | is.nan(m), NA_character_,
         sprintf("%.2f (%.2f)", m, s))
}

summary_df <- data.frame(
  Q_Matrix = c(
    sprintf("TRACE-Q K=4 (n=%d)", nrow(results_K4)),
    "TSQE K=4",
    sprintf("TRACE-Q K=6 (n=%d)", nrow(results_K6)),
    "TSQE K=6",
    "Expert K=8"
  ),
  AIC = c(fmt(mean_K4["AIC"], sd_K4["AIC"]),
          sprintf("%.2f", fit_tsqe4$AIC),
          fmt(mean_K6["AIC"], sd_K6["AIC"]),
          sprintf("%.2f", fit_tsqe6$AIC),
          sprintf("%.2f", fit_expert$AIC)),
  BIC = c(fmt(mean_K4["BIC"], sd_K4["BIC"]),
          sprintf("%.2f", fit_tsqe4$BIC),
          fmt(mean_K6["BIC"], sd_K6["BIC"]),
          sprintf("%.2f", fit_tsqe6$BIC),
          sprintf("%.2f", fit_expert$BIC)),
  CAIC = c(fmt(mean_K4["CAIC"], sd_K4["CAIC"]),
           sprintf("%.2f", fit_tsqe4$CAIC),
           fmt(mean_K6["CAIC"], sd_K6["CAIC"]),
           sprintf("%.2f", fit_tsqe6$CAIC),
           sprintf("%.2f", fit_expert$CAIC)),
  SABIC = c(fmt(mean_K4["SABIC"], sd_K4["SABIC"]),
            sprintf("%.2f", fit_tsqe4$SABIC),
            fmt(mean_K6["SABIC"], sd_K6["SABIC"]),
            sprintf("%.2f", fit_tsqe6$SABIC),
            sprintf("%.2f", fit_expert$SABIC)),
  RMSEA2 = c(fmt(mean_K4["RMSEA2"], sd_K4["RMSEA2"]),
             sprintf("%.4f", fit_tsqe4$RMSEA2),
             fmt(mean_K6["RMSEA2"], sd_K6["RMSEA2"]),
             sprintf("%.4f", fit_tsqe6$RMSEA2),
             ifelse(is.na(fit_expert$RMSEA2), NA_character_,
                    sprintf("%.4f", fit_expert$RMSEA2))),
  SRMSR = c(fmt(mean_K4["SRMSR"], sd_K4["SRMSR"]),
            sprintf("%.4f", fit_tsqe4$SRMSR),
            fmt(mean_K6["SRMSR"], sd_K6["SRMSR"]),
            sprintf("%.4f", fit_tsqe6$SRMSR),
            sprintf("%.4f", fit_expert$SRMSR)),
  Complete = c(sprintf("%d/%d", sum(complete_K4), nrow(results_K4)),
               ifelse(comp_tsqe4, "Yes", "No"),
               sprintf("%d/%d", sum(complete_K6), nrow(results_K6)),
               ifelse(comp_tsqe6, "Yes", "No"),
               ifelse(comp_expert, "Yes", "No")),
  stringsAsFactors = FALSE
)

summary_df

