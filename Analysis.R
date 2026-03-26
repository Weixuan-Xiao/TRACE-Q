library(GDINA)
set.seed(1)

Q_expert = GDINA::realdata_Tatsuoka1990$Q
data = GDINA::realdata_Tatsuoka1990$dat

# Audited K=6 1 run
Q_Agent = read.csv("/Users/weixuan/Desktop/Agent-Qmatrix/prompt_experiment/v5_guided_fixedseed/run1/step8_auditor_Q_matrix_K6_reviewed.csv")
Q_Agent = Q_Agent[,-c(1,8)]
Q_Agent[] <- lapply(Q_Agent, function(x) as.numeric(gsub("[^01]", "", as.character(x))))
Q_Agent = as.data.frame(Q_Agent)

Q.completeness(Q_Agent)

result_agent = GDINA(data,Q_Agent)
mf2 <- GDINA::modelfit(result_agent)
mf2


# Audited K=4 1 run
Q_Agent = read.csv("/Users/weixuan/Desktop/Agent-Qmatrix/prompt_experiment/v5_guided_fixedseed/run1/step8_auditor_Q_matrix_K4_reviewed.csv")
Q_Agent = Q_Agent[,-c(1,6)]
Q_Agent[] <- lapply(Q_Agent, function(x) as.numeric(gsub("[^01]", "", as.character(x))))
Q_Agent = as.data.frame(Q_Agent)

Q.completeness(Q_Agent)

result_agent = GDINA(data,Q_Agent)
mf2 <- GDINA::modelfit(result_agent)
mf2


# TSQE as baseline 1
Q_TSQE = NPCDTools::TSQE(data,K=6,ref.method = "GDI",GDI.model = "GDINA")
rownames(Q_TSQE) <- paste0("Item", 1:nrow(Q_TSQE))
result_TSQE = GDINA(data,Q_TSQE)
mf3 = GDINA::modelfit(result_TSQE)
mf3

Q_TSQE = NPCDTools::TSQE(data,K=4,ref.method = "GDI",GDI.model = "GDINA")
rownames(Q_TSQE) <- paste0("Item", 1:nrow(Q_TSQE))
result_TSQE = GDINA(data,Q_TSQE)
mf3 = GDINA::modelfit(result_TSQE)
mf3

# Expert as baseline 2
result_expert = GDINA(data,Q_expert)
mf1 <- GDINA::modelfit(result_expert)
mf1





