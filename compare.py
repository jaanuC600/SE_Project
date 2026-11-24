import ollama, os
from pipeline import SYSTEMS

PROMPTS = {
    "requirements": "Given this loan and credit system context, generate functional and non-functional requirements for loan eligibility check and credit scoring.\n\nContext:\nThe lender evaluates credit score, income and obligations to decide eligibility.",
    "sdlc": "Given these software requirements, identify the most appropriate SDLC model with a software engineering justification.\n\nContext:\nA mobile loan app with evolving UX, small team, frequent customer feedback and known compliance rules.",
}
MODELS = ["llama3.2:3b", "loan-llm"]

os.makedirs("outputs", exist_ok=True)
with open("outputs/comparison.md", "w", encoding="utf-8") as f:
    for kind, prompt in PROMPTS.items():
        for m in MODELS:
            out = ollama.chat(
                model=m,
                messages=[{"role": "system", "content": SYSTEMS[kind]},
                          {"role": "user", "content": prompt}],
                options={"temperature": 0.3},
            )["message"]["content"]
            f.write(f"## {kind} - {m}\n\n{out}\n\n")
            print(f"done: {kind} / {m}")
print("Saved outputs/comparison.md")
