# build_dataset.py
import ollama, json, re, glob

def chunk_text(text, max_chars=1500):
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) > max_chars:
            if current:
                chunks.append(current)
            current = p
        else:
            current += "\n" + p
    if current:
        chunks.append(current)
    return chunks

def generate_pair(chunk, domain="Banking"):
    prompt = f"""You are creating training data for fine-tuning a requirements-engineering model.

Below is a chunk from a real {domain} software project/requirements document:

---
{chunk}
---

Based ONLY on this chunk, produce ONE training example in this exact JSON format:
{{
  "instruction": "Given this banking system context, generate functional and non-functional requirements for <specific functionality mentioned in the chunk>.",
  "input": "<a short 1-2 sentence paraphrase of the chunk as context>",
  "output": "FR-01: <requirement statement>\\nReasoning: <why this requirement matters>\\nFR-02: ...\\n(3-5 requirements total, mix of functional/non-functional)"
}}

Return ONLY valid JSON, no other text, no markdown fences.
"""
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.4},
    )
    raw = response["message"]["content"].strip()
    raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("⚠️ Skipped one bad chunk (invalid JSON)")
        return None

def load_docs(folder="docs"):
    texts = []
    for path in glob.glob(f"{folder}/*.txt"):
        with open(path, encoding="utf-8") as f:
            texts.append(f.read())
    return texts

if __name__ == "__main__":
    all_chunks = []
    for doc in load_docs():
        all_chunks.extend(chunk_text(doc))

    print(f"Found {len(all_chunks)} chunks. Generating training pairs...")
    dataset = []
    for i, chunk in enumerate(all_chunks):
        pair = generate_pair(chunk)
        if pair:
            dataset.append(pair)
            print(f"[{i+1}/{len(all_chunks)}] ✓ generated")

    with open("training_data.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"\nDone. {len(dataset)} examples saved to training_data.json")