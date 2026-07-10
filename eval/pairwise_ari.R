# Pairwise Adjusted Rand Index over profile CSVs written by extract_profiles.R.
# Usage: Rscript eval/pairwise_ari.R --output <out.json> --profiles f1.csv f2.csv [...]

suppressMessages(library(mclust))
suppressMessages(library(jsonlite))

args <- commandArgs(trailingOnly = TRUE)
output_path <- NULL
profile_paths <- character(0)

i <- 1
while (i <= length(args)) {
  if (args[i] == "--output") { output_path <- args[i + 1]; i <- i + 2 }
  else if (args[i] == "--profiles") {
    i <- i + 1
    while (i <= length(args) && !startsWith(args[i], "--")) {
      profile_paths <- c(profile_paths, args[i]); i <- i + 1
    }
  }
  else { i <- i + 1 }
}

if (is.null(output_path)) stop("--output is required")
if (length(profile_paths) < 2) stop("need at least 2 --profiles")

profiles <- lapply(profile_paths, function(p) as.character(read.csv(p)$profile))
labels <- basename(profile_paths)

n <- length(profiles)
ari_matrix <- diag(1, n)
pairs <- list()
for (a in seq_len(n - 1)) {
  for (b in seq((a + 1), n)) {
    ari <- mclust::adjustedRandIndex(profiles[[a]], profiles[[b]])
    ari_matrix[a, b] <- ari
    ari_matrix[b, a] <- ari
    pairs[[length(pairs) + 1]] <- list(a = labels[a], b = labels[b], ari = ari)
  }
}

result <- list(labels = labels, ari_matrix = ari_matrix, pairs = pairs)
writeLines(toJSON(result, auto_unbox = TRUE, digits = 6), output_path)
cat("Pairwise ARI written to:", output_path, "\n")
