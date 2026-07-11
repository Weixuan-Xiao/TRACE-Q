# Estimate a data-driven Q-matrix via NPCDTools::TSQE and write it in
# canonical contract format (item_id + binary skill cols T1..Tk).
# Usage: Rscript eval/tsqe.R --dataset <name|csv> --k <int> --output <path>

suppressMessages(library(NPCDTools))
suppressMessages(library(GDINA))

args <- commandArgs(trailingOnly = TRUE)
dataset <- "tatsuoka"
k <- NULL
output_path <- NULL

i <- 1
while (i <= length(args)) {
  if (args[i] == "--dataset") { dataset <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--k") { k <- as.integer(args[i + 1]); i <- i + 2 }
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

Q <- NPCDTools::TSQE(data, K = k, ref.method = "GDI", GDI.model = "GDINA")

df <- data.frame(item_id = sprintf("FS%02d", seq_len(nrow(Q))))
for (j in seq_len(ncol(Q))) {
  df[[sprintf("T%d", j)]] <- as.integer(Q[, j])
}
write.csv(df, output_path, row.names = FALSE, quote = FALSE)
cat("TSQE Q (", nrow(Q), "x", ncol(Q), ") written to:", output_path, "\n")
