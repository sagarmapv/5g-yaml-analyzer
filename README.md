setup instructions:



```markdown
# 5G SBI YAML Viewer & Analyzer 🛰️

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A lightweight web tool to parse, inspect, and explore **5G SBI YAML API files** (from 3GPP specs).  
Built with **Python + Flask**, it dynamically lists **Network Functions → Services → SBI messages** with URI/method/params/response breakdown.

```

## 📁 Project Structure

```text

5G-World/
├── Yaml-Files/             # Raw 3GPP YAMLs (5GC\_APIs)
├── Parsed-JSON/            # Auto-generated swagger-compatible JSONs
├── Bank/                   # Parsed JSONs with method/URI/params/responses
├── Web-UI/                 # HTML frontend with collapsible NF → Services view
├── index.json              # Dynamic NF → Services mapping
├── app.py                  # Flask server with auto rebuild
├── generate\_bank.py        # Parses JSONs into Bank & Index
├── generate\_parsed\_json.sh # Converts YAML → Swagger JSON
└── requirements.txt

````



## 🚀 Features

- 🔄 **Auto Conversion**: YAML → Swagger JSON → Bank JSON → Index
- 📚 **API Bank**: Each service gets rich metadata for every SBI call
- 🌐 **Web Viewer**: Explore NFs and Services in collapsible UI
- 🛠️ **Flask Backend**: One-click refresh of entire data flow
- 📦 **Lightweight**: No external database or complex dependencies

## 📂 YAML File Setup

This repo **does not include 3GPP YAMLs** due to size and licensing.

To use the app:

1. Download the full set of OpenAPI YAML files (e.g., from the [5GC_APIs GitHub repo](https://github.com/jdegre/5GC_APIs))
2. Place them inside:


Yaml-Files/5GC_APIs/


## ⚙️ Setup Instructions

```bash
# Clone the repo
git clone https://github.com/your-username/5g-yaml-analyzer.git
cd 5g-yaml-analyzer

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
````



## ▶️ Run the App

```bash
python app.py
```

* 🌐 Access the tool at: `http://localhost:5000/`
* ✅ On launch:

  * Converts all YAMLs to Swagger JSON
  * Builds Bank JSONs
  * Generates index for NF → Services
* 🧭 Navigate through NF → Services
* 📄 Click to view YAML or parsed Swagger JSON



## 📄 License

This project is licensed under the **MIT License** — feel free to use and modify with credit.



## 🙏 Credits

Built with love by \[Aditya Madduri] and ChatGPT
Inspired by the need to **bring clarity to 5G SBI interfaces**.

🌼 *Jaya Guru Datta* 🚀



