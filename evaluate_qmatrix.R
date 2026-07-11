# evaluate_qmatrix.R
# Usage: Rscript evaluate_qmatrix.R --qmatrix <path> --dataset <name> --output <path>

library(GDINA)

# --- Parse arguments ---
args <- commandArgs(trailingOnly = TRUE)
qmatrix_path <- NULL
dataset <- "tatsuoka"
output_path <- "eval_result.json"

i <- 1
while (i <= length(args)) {
  if (args[i] == "--qmatrix") { qmatrix_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--dataset") { dataset <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--output") { output_path <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

if (is.null(qmatrix_path)) stop("--qmatrix is required")

# --- Load response data ---
if (dataset == "tatsuoka") {
  data <- GDINA::realdata_Tatsuoka1990$dat
} else {
  data <- read.csv(dataset)
}

# --- Load Q-matrix ---
Q_raw <- read.csv(qmatrix_path)
Q <- Q_raw[, -1]  # Drop item_id column
Q[] <- lapply(Q, function(x) as.integer(gsub("[^01]", "", as.character(x))))
Q <- as.matrix(Q)

N <- nrow(data)
n_items <- nrow(Q)
n_skills <- ncol(Q)

# --- Fit G-DINA and extract metrics ---
result_list <- list(
  qmatrix_path = qmatrix_path,
  dataset = dataset,
  n_items = n_items,
  n_skills = n_skills,
  AIC = NULL, BIC = NULL, CAIC = NULL, SABIC = NULL,
  RMSEA2 = NULL, SRMSR = NULL,
  log_likelihood = NULL, n_params = NULL,
  converged = NULL, error = NULL
)

tryCatch({
  set.seed(1)
  fit <- GDINA::GDINA(data, Q)

  ll <- as.numeric(logLik(fit))
  npar <- extract(fit, "npar")

  result_list$AIC <- AIC(fit)
  result_list$BIC <- BIC(fit)
  result_list$CAIC <- -2 * ll + npar * (log(N) + 1)
  result_list$SABIC <- -2 * ll + npar * log((N + 2) / 24)
  result_list$log_likelihood <- ll
  result_list$n_params <- npar
  result_list$converged <- TRUE

  tryCatch({
    mf <- GDINA::modelfit(fit)
    result_list$RMSEA2 <- mf$RMSEA2
    result_list$SRMSR <- mf$SRMSR
  }, error = function(e) {
    result_list$RMSEA2 <<- NULL
    result_list$SRMSR <<- NULL
  })

}, error = function(e) {
  result_list$converged <<- FALSE
  result_list$error <<- conditionMessage(e)
})

# --- Write JSON ---
library(jsonlite)
json_str <- toJSON(result_list, auto_unbox = TRUE, pretty = TRUE, null = "null")
writeLines(json_str, output_path)
cat("Evaluation written to:", output_path, "\n")
