import glob, os, re, sys, time, ollama

MODEL_REQ  = os.getenv("MODEL_REQ",  "loan-llm")
MODEL_SDLC = os.getenv("MODEL_SDLC", "loan-llm")

SYSTEMS = {
    "requirements": "You are a senior requirements engineer for loan and credit software in India. Write clear, testable requirements, each followed by a Reasoning line. Consider RBI guidelines and Indian data protection law.",
    "sdlc": "You are a software process consultant. Recommend exactly one SDLC model and justify it using the characteristics of the requirements.",
}

# Format example uses an UNRELATED functionality so the model cannot copy it.
REQ_EXAMPLE = """Format example (for a different functionality, loan statements; do NOT reuse its content):
FR-01 [Functional]: The system shall generate a loan account statement for any date range showing instalments, interest, charges and balance.
Reasoning: Borrowers need a clear record of what they have paid and owe.
FR-02 [Functional]: The system shall deliver statements as password-protected PDF files by email or in the app.
Reasoning: Statements contain sensitive financial data.
NFR-01 [Non-functional]: The system shall generate a statement within 10 seconds for up to 5 years of history.
Reasoning: Slow document generation frustrates customers."""

SDLC_EXAMPLES = """Example 1
Requirements: A KYC module with fixed regulatory rules, mandatory identity checks, full audit logging, zero tolerance for defects, stable scope.
Recommended SDLC: V-Model
Characteristics identified:
- Requirements are stable because they come from fixed regulation.
- Defects have legal and financial consequences.
- Every requirement must be traceable to a test for audit.
Justification: The V-Model pairs each development phase with a matching test phase, so every regulatory requirement gets a verification step and a traceability record.
Why not Agile: Frequent change and light documentation do not suit a module that auditors will inspect against fixed rules.

Example 2
Requirements: A customer-facing mobile loan app with UX that will change after user feedback, fast-moving competitors, a small team and a product owner available daily.
Recommended SDLC: Agile (Scrum)
Characteristics identified:
- Requirements are expected to evolve with user feedback.
- Fast time to market matters.
- Stakeholders are available for frequent review.
Justification: Scrum delivers working increments in short sprints, so feedback can reshape the backlog every few weeks.
Why not Waterfall: Locking all requirements upfront would delay feedback and make late UX changes expensive."""


class Agent:
    def __init__(self, name, system, model):
        self.name, self.system, self.model = name, system, model

    def run(self, prompt, label=""):
        print(f"\n>>> {self.name} is working ({self.model}) {label}...")
        r = ollama.chat(
            model=self.model,
            messages=[{"role": "system", "content": self.system},
                      {"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_ctx": 4096},
        )
        return r["message"]["content"].strip()


def load_chunks(folder="docs", max_chars=1200):
    chunks = []
    for path in glob.glob(f"{folder}/*.txt"):
        text = open(path, encoding="utf-8", errors="ignore").read()
        text = re.sub(r"https?://\S+|!\[.*?\]\(.*?\)", "", text)
        cur = ""
        for line in (l.strip() for l in text.split("\n") if l.strip()):
            if len(cur) + len(line) > max_chars:
                chunks.append(cur)
                cur = line
            else:
                cur += "\n" + line
        if cur:
            chunks.append(cur)
    return chunks


def top_chunks(chunks, query, k=4):
    q = set(re.findall(r"[a-z]{4,}", query.lower())) | {"loan", "credit", "customer"}
    scored = sorted(chunks, key=lambda c: len(q & set(re.findall(r"[a-z]{4,}", c.lower()))), reverse=True)
    return scored[:k]


if __name__ == "__main__":
    functionality = sys.argv[1] if len(sys.argv) > 1 else "Loan Eligibility Check and Credit Scoring"
    chunks = load_chunks()

    req_agent = Agent("Agent 1: Requirements Engineer", SYSTEMS["requirements"], MODEL_REQ)
    sdlc_agent = Agent("Agent 2: SDLC Consultant", SYSTEMS["sdlc"], MODEL_SDLC)

    # Part 1: documents -> requirements + reasoning (one call per sub-functionality)
    parts = [p.strip() for p in re.split(r",| and ", functionality) if p.strip()]
    all_reqs = []
    for p in parts:
        ctx = "\n".join(c[:500] for c in top_chunks(chunks, p, k=2))
        out = req_agent.run(
            f"Given this loan and credit system context, generate functional and "
            f"non-functional requirements ONLY for: {p}. Write 4 to 6 requirements "
            f"that are specific to {p}. Follow the format example exactly.\n\n"
            f"{REQ_EXAMPLE}\n\nContext:\n{ctx}",
            label=f"[{p}] ")
        out = "\n".join(l for l in out.split("\n") if not l.lower().startswith("here are"))
        all_reqs.append(f"===== Requirements for: {p} =====\n{out.strip()}")
    reqs = "\n\n".join(all_reqs)
    print("\n" + reqs)

    # Part 2: requirements -> SDLC + justification (hand-off from Agent 1 to Agent 2)
    sdlc = sdlc_agent.run(
        "Given these software requirements, identify the most appropriate SDLC model "
        "with a software engineering justification. Choose the model from the "
        "characteristics of the requirements (stability, risk, regulation, need for "
        "feedback), not from the examples. Follow the example format exactly, "
        "including the 'Why not' line.\n\n"
        f"{SDLC_EXAMPLES}\n\nNow the real task.\nRequirements:\n{reqs[:2500]}")
    print("\n===== SDLC RECOMMENDATION =====\n" + sdlc)

    os.makedirs("outputs", exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    open(f"outputs/{stamp}_requirements.txt", "w", encoding="utf-8").write(reqs)
    open(f"outputs/{stamp}_sdlc.txt", "w", encoding="utf-8").write(sdlc)
    print(f"\nSaved to outputs/{stamp}_*.txt")
