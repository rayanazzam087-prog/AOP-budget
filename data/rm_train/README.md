# Reward-model training pool (stand-in for HuskyQA train)

The public HuskyQA release (huggingface.co/datasets/agent-husky/HuskyQA) contains only the
292-question **test** set. The 1,440 training queries AOP mentions are not released, so the
reward model is trained on a 1,440-question mix of multi-step QA with the same skill profile
(fact lookup + arithmetic + yes/no reasoning). None of these questions appear in HuskyQA test.

| source | n | skill | license |
|---|---|---|---|
| HotpotQA (Yang et al., 2018) | 515 | multi-hop fact lookup | CC BY-SA 4.0 |
| GSM8K (Cobbe et al., 2021) | 500 | arithmetic word problems | MIT |
| Bamboogle (Press et al., 2023) | 125 | compositional search questions | MIT |
| StrategyQA (Geva et al., 2021) | 300 | implicit yes/no reasoning | MIT |

Questions were sampled (seed 0) from the evaluation files shipped in the HUSKY repository
(github.com/agent-husky/Husky-v1, `husky/dataset/*/test.jsonl`). Report this as a deviation
from the paper.
