# Export the published expert Q-matrix for the Tatsuoka (1990) fraction
# subtraction data to the canonical contract format (item_id + binary skill cols).
# Usage: Rscript eval/export_expert_q.R [output_csv]

args <- commandArgs(trailingOnly = TRUE)
output_path <- if (length(args) >= 1) args[1] else "data/expert_q_tatsuoka.csv"

Q <- GDINA::realdata_Tatsuoka1990$Q
n_items <- nrow(Q)
n_skills <- ncol(Q)

df <- data.frame(item_id = sprintf("FS%02d", seq_len(n_items)))
for (j in seq_len(n_skills)) {
  df[[sprintf("A%d", j)]] <- as.integer(Q[, j])
}

write.csv(df, output_path, row.names = FALSE, quote = FALSE)
cat("Expert Q (", n_items, "x", n_skills, ") written to:", output_path, "\n")
