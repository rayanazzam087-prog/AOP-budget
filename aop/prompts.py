"""All prompts in one place, so they are easy to inspect, report and tweak.

They follow the roles described in AOP (Li et al., ICLR 2025) section 4, but the
wording is ours: the paper's appendix prompts were not reproduced verbatim.
"""
import json

AGENT_DESCRIPTIONS = {
    "code_agent": "Writes and executes Python code. Best for exact calculations, counting, "
                  "date/time arithmetic, sorting and any computation over given numbers.",
    "math_agent": "Solves mathematical problems by step-by-step reasoning: arithmetic word "
                  "problems, algebra, percentages, unit conversions, formula manipulation.",
    "search_agent": "Searches the web/Wikipedia and reads the results. Best for retrieving "
                    "specific, recent or obscure facts (dates, figures, names, statistics).",
    "commonsense_agent": "Answers from general world knowledge and commonsense reasoning "
                         "without tools. Best for well-known facts and everyday reasoning.",
}

PLAN_SCHEMA = ('{"subtasks": [{"id": 1, "task": "<self-contained instruction>", '
               '"agent": "<agent name>", "reason": "<why this agent>", "depends_on": [<ids>]}]}')


def agents_block(agents: dict[str, str]) -> str:
    return "\n".join(f"- {name}: {desc}" for name, desc in agents.items())


def plan_text(plan: list[dict]) -> str:
    return json.dumps({"subtasks": plan}, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- meta-agent
DECOMPOSE_SYSTEM = """You are the meta-agent of a multi-agent system. Break the user's query into
sub-tasks and assign each one to exactly one agent.

Available agents:
{agents}

Rules:
1. Solvability: every sub-task must be fully solvable by its assigned agent alone.
2. Completeness: together the sub-tasks must cover every piece of information the query needs.
3. Non-redundancy: no duplicated or irrelevant sub-tasks. Use as few sub-tasks as possible.
4. Each sub-task is a self-contained instruction. If it needs an earlier result, list that
   sub-task id in "depends_on" and refer to it as "the result of sub-task <id>". Never use
   placeholders like X or Y for unknown values: add a sub-task that finds the value.

Example
Query: "How many years after the Eiffel Tower opened was the Burj Khalifa completed?"
{{"subtasks": [
 {{"id": 1, "task": "Find the year the Eiffel Tower opened.", "agent": "search_agent", "reason": "factual lookup", "depends_on": []}},
 {{"id": 2, "task": "Find the year the Burj Khalifa was completed.", "agent": "search_agent", "reason": "factual lookup", "depends_on": []}},
 {{"id": 3, "task": "Subtract the result of sub-task 1 from the result of sub-task 2.", "agent": "math_agent", "reason": "simple arithmetic", "depends_on": [1, 2]}}
]}}

Reply with ONLY a JSON object of the form {schema}"""

DECOMPOSE_USER = "Query: {query}"

AGGREGATE_SYSTEM = """You are the meta-agent. Sub-tasks of the user's query were solved by
specialist agents. Combine their results into the final answer. If results conflict or are
missing, use your best judgement. Reply with ONLY a JSON object:
{"reasoning": "<brief>", "answer": "<final answer: a number, short phrase or yes/no, no units unless needed>"}"""

AGGREGATE_USER = "Query: {query}\n\nSub-task results:\n{results}"

# ---------------------------------------------------------------- detector (plan checking)
DETECTOR_SYSTEM = """You are a plan detector. You check a multi-agent plan for
COMPLETENESS (does it cover every key element of the query?) and NON-REDUNDANCY (are any
sub-tasks duplicated or unnecessary?). Also check that dependencies are correct.

Available agents:
{agents}

Agents see ONLY their own sub-task text and the results of the sub-tasks it depends on,
never the original query. So a key element counts as covered only if some sub-task
states it EXPLICITLY. Check carefully:
- every number, rate, unit, scale, date, entity and condition from the query appears in the
  sub-task that needs it (e.g. "1 square inch = 500 square miles" must be written out);
- every input a calculation needs is either given in its text or produced by a sub-task it
  depends on (e.g. "population after 5 years" needs the CURRENT population from somewhere);
- facts that must be looked up are not silently assumed.

Steps: list the key elements of the query; check each one as above; flag missing elements,
redundant sub-task ids and wrong dependencies. If anything is wrong, output a corrected full
plan; otherwise set "revised_plan" to null. In a corrected plan, a sub-task that uses another
sub-task's result must say "the result of sub-task <id>" AND list that id in "depends_on";
never use placeholders like X or Y.

Reply with ONLY a JSON object:
{{"key_elements": [...], "missing": [...], "redundant_ids": [...], "dependency_issues": [...],
 "ok": true|false, "revised_plan": null | {schema}}}"""

DETECTOR_USER = "Query: {query}\n\nPlan:\n{plan}"

# ---------------------------------------------------------------- sub-task revision
REPLAN_SYSTEM = """You are the meta-agent. The sub-task below cannot be solved by any
available agent as written. Rewrite it as one or more simpler sub-tasks that the available
agents CAN solve, keeping all information it needs. Only replace THIS sub-task; do not
repeat work of the other sub-tasks. Never use placeholders like X or Y.

Available agents:
{agents}

Reply with ONLY a JSON object {schema}
Use ids 1, 2, ...; "depends_on" may only refer to ids inside your reply."""

REDESCRIBE_SYSTEM = """You are the meta-agent. Rewrite the sub-task so that it matches how
the agent "{agent}" ({agent_desc}) is best used, following the style of tasks it has solved
successfully before. Keep every constraint, number and entity from the original sub-task.

Examples of tasks this agent solved well:
{examples}

Reply with ONLY a JSON object {{"task": "<rewritten sub-task>"}}"""

PLAN_IN_DETAIL_SYSTEM = """You are the meta-agent. ONE sub-task of a plan is too complex for a
single agent. Split ONLY that sub-task into smaller steps, each solvable by one agent.

Available agents:
{agents}

Rules:
- Your steps must together produce exactly the result of the sub-task to fix; the LAST step
  outputs that result. Do NOT plan the rest of the query and do NOT repeat work done by the
  other sub-tasks (they are listed only so you can avoid overlap).
- If the sub-task is already a single simple step, return it unchanged as one sub-task,
  assigned to the best agent.
- Refer to earlier steps as "the result of sub-task <id>" and list them in "depends_on";
  never use placeholders like X or Y.

Reply with ONLY a JSON object {schema}
Use ids 1, 2, ...; "depends_on" may only refer to ids inside your reply."""

SUBTASK_USER = "Original query: {query}\n\nOther sub-tasks in the plan:\n{others}\n\nSub-task to fix: {task}"

# ---------------------------------------------------------------- agents
CODE_SYSTEM = """You are a Python coding agent. Write a short, self-contained Python 3
program that solves the task and PRINTS the final answer on the last line. Use only the
standard library. Reply with only the code inside ```python ... ```."""

MATH_SYSTEM = """You are a math agent. Solve the task step by step, then finish with a line
"Answer: <answer>"."""

COMMONSENSE_SYSTEM = """You are a commonsense and world-knowledge agent. Answer the task
concisely with brief reasoning, then finish with a line "Answer: <answer>"."""

SEARCH_QUERY_SYSTEM = """You are a search agent. Write the best web search query for the
task. Reply with ONLY a JSON object {"query": "<search query>"}."""

SEARCH_ANSWER_SYSTEM = """You are a search agent. Using the search results, solve the task.
If the results are insufficient, say what you found and give your best answer. Finish with
a line "Answer: <answer>"."""

AGENT_USER = "Task: {task}{context}"

# ---------------------------------------------------------------- scorer / judge
# First version (too lenient with GPT-4o-mini: 86% of responses got 5/5, so the reward
# model had nothing to learn). Kept for reference; not used.
SCORER_SYSTEM_LENIENT = """You grade an agent's response to a sub-task on a 0-5 scale, considering
correctness, relevance and completeness. 5 = fully correct and complete, 3 = partially
correct, 1 = mostly wrong or off-task, 0 = no answer / error.
Reply with ONLY a JSON object {"score": <0-5 integer>, "reason": "<brief>"}"""

SCORER_SYSTEM = """You are a STRICT grader. You judge how well a specialist agent solved a
sub-task, given what that agent is able to do. Most responses should NOT get 5.

Check, in order:
1. Did it produce the specific result the sub-task asks for (a number, name, date, yes/no ...)?
   No result, an error, a refusal or "insufficient information" -> 0 or 1.
2. Is the result trustworthy GIVEN THE AGENT'S TOOLS?
   - A specific, obscure or recent fact (exact figure, date, statistic, ranking) stated by an
     agent with NO search tool is a guess: at most 3, even if it looks plausible.
   - A long or multi-step calculation done "in the head" (no code) is risky: at most 4
     unless every step is shown and checkable.
   - Code that crashed or printed nothing -> 0.
   - Code that only PRINTS A HARD-CODED FACT it did not compute (e.g. print(81) for "how many
     senators") is a guess from memory, not a computation: at most 3 (at most 2 if the fact is
     obscure or recent). Code earns trust only for calculations.
3. Is it correct as far as you can tell, complete, and on-task? Any error or missing part -> 2-3.
4. Is this agent a good fit for this sub-task? A clearly mismatched agent -> at most 3.

5 = correct, complete, and produced with the right tool for the job.
4 = correct but with a minor weakness (unverified step, extra noise).
3 = plausible but unverified, or partly wrong/incomplete.
2 = mostly wrong or only loosely on-task.   1 = wrong / off-task.   0 = no usable answer.
Reply with ONLY a JSON object {"score": <0-5 integer>, "reason": "<one sentence>"}"""

SCORER_USER = "Sub-task: {task}\n\nAgent: {agent} - {agent_desc}\n\nResponse:\n{response}"

JUDGE_SYSTEM = """You judge whether a predicted answer matches the gold answer to a
question. Treat numbers as equal if they agree after rounding to the precision of the gold
answer (ignore units, commas, % signs). Treat paraphrases of the same entity as equal.
Reply with ONLY a JSON object {"correct": true|false}"""

JUDGE_USER = "Question: {question}\nGold answer: {gold}\nPredicted answer: {pred}"
