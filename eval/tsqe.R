# Estimate a data-driven Q-matrix via NPCDTools::TSQE and write it in
# canonical contract format (item_id + binary skill cols T1..Tk).
# Usage: Rscript eval/tsqe.R --dataset <name|csv> --k <int|auto> --output <path>
# --k auto sweeps K=3..8 and keeps the Q whose GDINA fit minimizes BIC
# (the data-driven analogue of letting an LLM pick K within the 3-8 band).

suppressMessages(library(NPCDTools))
suppressMessages(library(GDINA))

args <- commandArgs(trailingOnly = TRUE)
dataset <- "tatsuoka"
k <- NULL
output_path <- NULL

i <- 1
while (i <= length(args)) {
  if (args[i] == "--dataset") { dataset <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--k") { k <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--output") { output_path <- args[i + 1]; i <- i + 2 }
  else { i <- i + 1 }
}

if (is.null(k)) stop("--k is required")
if (is.null(output_path)) stop("--output is required")

if (dataset == "tatsuoka") {
  data <- GDINA::realdata_Tatsuoka1990$dat
} else {
  data <- read.csv(dataset)
}

if (k == "auto") {
  best_bic <- Inf
  best_Q <- NULL
  bic_table <- list()
  for (kk in 3:8) {
    Qk <- NPCDTools::TSQE(data, K = kk, ref.method = "GDI", GDI.model = "GDINA")
    bic <- tryCatch({
      set.seed(1)
      fit <- GDINA::GDINA(data, Qk, verbose = 0)
      BIC(fit)
    }, error = function(e) NA)
    bic_table[[sprintf("K%d", kk)]] <- bic
    cat("K =", kk, " BIC =", bic, "\n")
    if (!is.na(bic) && bic < best_bic) {
      best_bic <- bic
      best_Q <- Qk
    }
  }
  if (is.null(best_Q)) stop("no K in 3..8 produced a fittable TSQE Q")
  Q <- best_Q
  suppressMessages(library(jsonlite))
  writeLines(toJSON(list(selected_k = ncol(Q), bic = bic_table),
                    auto_unbox = TRUE, null = "null"),
             paste0(output_path, ".meta.json"))
  cat("Selected K =", ncol(Q), "(min BIC =", best_bic, ")\n")
} else {
  Q <- NPCDTools::TSQE(data, K = as.integer(k), ref.method = "GDI", GDI.model = "GDINA")
}

df <- data.frame(item_id = sprintf("FS%02d", seq_len(nrow(Q))))
for (j in seq_len(ncol(Q))) {
  df[[sprintf("T%d", j)]] <- as.integer(Q[, j])
}
write.csv(df, output_path, row.names = FALSE, quote = FALSE)
cat("TSQE Q (", nrow(Q), "x", ncol(Q), ") written to:", output_path, "\n")
