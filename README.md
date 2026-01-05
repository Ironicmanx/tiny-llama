# 🧠 Echo Local — Lightweight Offline AI Assistant

A fast, minimal local AI assistant using `llama.cpp` and Mistral 7B. No cloud, no nonsense.

---

## 🛠️ Requirements

- Python 3.9+
- Linux (tested on Fedora 42) or windows 10/11
- `llama.cpp` compiled (`make` or `cmake`)
- At least 16GB RAM recommended

---

## 🚀 Quick Start

Clone the repo, download a model, update local variables, build the runtime, and go:

```bash
# Clone this repo
git clone <thisrepo>
cd echo_local

# Download a quantized model
# (Mistral 7B Instruct v0.2 Q4_0 from TheBloke on HuggingFace)
mkdir -p models
wget -O models/mistral-7b-instruct-v0.2.Q4_0.gguf \
https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_0.gguf

# Build llama.cpp
cd llama.cpp
mkdir build && cd build
cmake ..
cmake --build . --config Release
cd ../../

# Run the assistant
python3 main.py
