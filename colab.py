import json, glob, torch
from unsloth import FastLanguageModel
from datasets import Dataset
from trl import SFTTrainer, SFTConfig

SYSTEMS = {
    "requirements": "You are a senior requirements engineer for loan and credit software. Write clear, testable requirements, each followed by a Reasoning line.",
    "sdlc": "You are a software process consultant. Recommend exactly one SDLC model and justify it using the characteristics of the requirements.",
}

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
    max_seq_length=2048,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=16, lora_dropout=0, bias="none",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    use_gradient_checkpointing="unsloth", random_state=3407,
)

data = json.load(open("training_data.json", encoding="utf-8"))

def to_text(ex):
    msgs = [
        {"role": "system", "content": SYSTEMS[ex["agent"]]},
        {"role": "user", "content": f"{ex['instruction']}\n\nContext:\n{ex['input']}"},
        {"role": "assistant", "content": ex["output"]},
    ]
    return {"text": tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)}

dataset = Dataset.from_list(data).map(to_text)

trainer = SFTTrainer(
    model=model, tokenizer=tokenizer, train_dataset=dataset,
    args=SFTConfig(
        dataset_text_field="text", max_seq_length=2048,
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        warmup_steps=5, num_train_epochs=4, learning_rate=2e-4,
        logging_steps=1, optim="adamw_8bit", output_dir="outputs", report_to="none",
        fp16=not torch.cuda.is_bf16_supported(), bf16=torch.cuda.is_bf16_supported(),
    ),
)
trainer.train()

model.save_pretrained_gguf("loan_llm", tokenizer, quantization_method="q4_k_m")

from google.colab import files
for f in glob.glob("loan_llm*/**/*.gguf", recursive=True) + glob.glob("loan_llm*/**/Modelfile", recursive=True):
    print("downloading", f)
    files.download(f)