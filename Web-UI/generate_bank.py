import os
import json
from pathlib import Path

# Config
PARSED_JSON_DIR = "/home/aifa/5G-World/Parsed-JSON"
BANK_DIR = "/home/aifa/5G-World/Bank"
INDEX_JSON_PATH = "/home/aifa/5G-World/index.json"

# Ensure Bank folder exists
os.makedirs(BANK_DIR, exist_ok=True)

# NF mapping
api_group_to_nf = {
    "Namf": "AMF",
    "Nsmf": "SMF",
    "Nudm": "UDM",
    "Nausf": "AUSF",
    "Nnrf": "NRF",
    "Npcf": "PCF",
    "Nchf": "CHF",
    "Nnef": "NEF",
    "Nbsf": "BSF",
    "Nlmf": "LMF",
    "Nnssf": "NSSF",
    "Nudr": "UDR",
    "Nsmsf": "SMSF",
    "N5g-eir": "EIR",
    "Nsepp": "SEPP",
    "Nmnpf": "MNPF",
    "Nucmf": "UCMF"
}

http_methods = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}
# Build index
index_dict = {}

# Walk all Parsed-JSON files
parsed_json_files = [f for f in os.listdir(PARSED_JSON_DIR) if f.endswith(".json")]
print(f"Processing {len(parsed_json_files)} Parsed-JSON files...")

for json_filename in parsed_json_files:
    json_path = Path(PARSED_JSON_DIR) / json_filename
    try:
        with open(json_path, "r") as f:
            swagger_json = json.load(f)

        api_group = swagger_json.get("info", {}).get("title", "UNKNOWN")
        nf_name = api_group_to_nf.get(api_group.split("_")[0], "UNKNOWN")
        source_file = json_filename.replace(".json", ".yaml")

        messages = []

        for path, path_item in swagger_json.get("paths", {}).items():
            for method_name, op in path_item.items():
                if method_name.lower() not in http_methods:
                    continue

                # Extract parameters
                params = []
                for param in op.get("parameters", []):
                    params.append({
                        "name": param.get("name", ""),
                        "in": param.get("in", ""),
                        "required": param.get("required", False)
                    })

                # Extract request body required fields
                request_body_required_fields = []
                if "requestBody" in op:
                    content = op["requestBody"].get("content", {})
                    for media_type, media_obj in content.items():
                        schema = media_obj.get("schema", {})
                        required_fields = schema.get("required", [])
                        request_body_required_fields.extend(required_fields)

                # Extract responses
                responses = []
                for status_code, response_obj in op.get("responses", {}).items():
                    description = response_obj.get("description", "")
                    responses.append({
                        "status_code": status_code,
                        "description": description
                    })

                messages.append({
                    "Path": path,
                    "Method": method_name.upper(),
                    "OperationId": op.get("OperationId", ""),
                    "Parameters": params,
                    "RequestBodyRequiredFields": request_body_required_fields,
                    "Responses": responses
                })
                
        # Build Bank object
        bank_obj = {
            "NF": nf_name,
            "Service": api_group,
            "SourceFile": source_file,
            "Messages": messages
        }

        # Save Bank JSON per file
        bank_filename = source_file.replace(".yaml", "_Bank.json")
        bank_path = Path(BANK_DIR) / bank_filename

        with open(bank_path, "w") as f:
            json.dump(bank_obj, f, indent=2)
        
        # ✅ After all methods for this file are parsed
        if nf_name not in index_dict:
            index_dict[nf_name] = []

        existing_services = [entry["service"] for entry in index_dict[nf_name]]
        if api_group not in existing_services:
            index_dict[nf_name].append({
                "service": api_group,
                "source_file": source_file
            })
            print(f"✅ Added to index: {nf_name} → {api_group} ({source_file})")
        else:
            print(  f"⚠️ Skipped duplicate in index: {nf_name} → {api_group}")

        print(f"✅ Bank generated for {source_file} → {bank_filename}")
        print(f"✅ {nf_name} → {api_group} ({source_file})")

    except Exception as e:
        print(f"💥 Failed to process {json_filename} → {e}")
    

print("✅ All Banks generated.")
# Save index.json
with open(INDEX_JSON_PATH, "w") as f:
    json.dump(index_dict, f, indent=2)

print(f"✅ index.json generated at {INDEX_JSON_PATH}")