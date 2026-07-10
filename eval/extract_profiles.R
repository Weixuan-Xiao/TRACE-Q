# Fit GDINA once for a Q-matrix and write per-person MAP attribute profiles.
# Full sample, no posterior filtering (per docs/evaluation_framework.md).
# Usage: Rscript eval/extract_profiles.R --qmatrix <Q.csv> --dataset <name|csv> --output <profiles.csv>

suppressMessages(library(GDINA))
suppressMessages(library(jsonlite))

args <- commandArgs(trailingOnly = TRUE)
qmatrix_path <- NULL
dataset <- "tatsuoka"
output_path <- NULL

i <- 1
while (i <= length(args)) {
  if (args[i] == "--qmatrix") { qmatrix_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--dataset") { dataset <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--output") { output_path <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

if (is.null(qmatrix_path)) stop("--qmatrix is required")
if (is.null(output_path)) stop("--output is required")

if (dataset == "tatsuoka") {
  data <- GDINA::realdata_Tatsuoka1990$dat
} else {
  data <- read.csv(dataset)
}

Q_raw <- read.csv(qmatrix_path)
Q <- Q_raw[, -1]
Q[] <- lapply(Q, function(x) as.integer(gsub("[^01]", "", as.character(x))))
Q <- as.matrix(Q)

meta <- list(qmatrix_path = qmatrix_path, dataset = dataset,
             k = ncol(Q), n_persons = nrow(data), converged = FALSE, error = NULL)

tryCatch({
  set.seed(1)
  fit <- GDINA::GDINA(data, Q, verbose = 0)
  mp <- GDINA::personparm(fit, what = "MAP")
  attr_cols <- setdiff(colnames(mp), "multimodes")
  profiles <- apply(mp[, attr_cols, drop = FALSE], 1, paste0, collapse = "")
  write.csv(data.frame(person = seq_along(profiles), profile = profiles),
            output_path, row.names = FALSE, quote = FALSE)
  meta$converged <- TRUE
}, error = function(e) {
  meta$error <<- conditionMessage(e)
})

writeLines(toJSON(meta, auto_unbox = TRUE, null = "null"),
           paste0(output_path, ".meta.json"))
if (!meta$converged) {
  cat("Profile extraction FAILED:", meta$error, "\n")
  quit(status = 1)
}
cat("Profiles written to:", output_path, "\n")
