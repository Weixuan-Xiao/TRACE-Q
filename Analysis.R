library(GDINA)
set.seed(1)
Q_Agent = read.csv("/Users/weixuan/Desktop/Agent-Qmatrix/outputs_exp/v2/run1/step8_auditor_Q_matrix_K4_reviewed.csv")
Q_Agent[] <- lapply(Q_Agent, function(x) as.numeric(gsub("[^01]", "", as.character(x))))
Q_Agent = Q_Agent[,-c(1,6)]
Q_Agent = as.data.frame(Q_Agent)
NPCDTools::Q.completeness(Q_Agent)
Q_expert = GDINA::realdata_Tatsuoka1990$Q
data = GDINA::realdata_Tatsuoka1990$dat
Q_TSQE = NPCDTools::TSQE(data,K=4)
rownames(Q_TSQE) <- paste0("Item", 1:nrow(Q_TSQE))

result_expert = GDINA(data,Q_expert)
result_agent = GDINA(data,Q_Agent)
result_TSQE = GDINA(data,Q_TSQE)


mf1 <- GDINA::modelfit(result_expert)
mf2 <- GDINA::modelfit(result_agent)
mf3 = GDINA::modelfit(result_TSQE)

mf1
mf2
mf3



