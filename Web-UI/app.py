from flask import Flask, send_from_directory, jsonify
import os
from pathlib import Path
import yaml
import json
import subprocess

app = Flask(__name__)

# Directory paths
YAML_DIR = "/home/aifa/5G-World/Yaml-Files/5GC_APIs"
PARSED_JSON_DIR = "/home/aifa/5G-World/Parsed-JSON"
http_methods = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}

print("🔄 Running generate_parsed_json.sh to refresh Parsed-JSON...")
subprocess.run(["/bin/bash", "generate_parsed_json.sh"], check=True)
print("✅ Parsed-JSON refreshed.")

# Refresh Bank
print("🔄 Running generate_bank.py to refresh Bank...")
subprocess.run(["python3", "generate_bank.py"], check=True)
print("✅ Bank refreshed.")


@app.route('/')
def serve_home():
    return send_from_directory(os.path.join(os.getcwd()), "viewer.html")

@app.route('/index')
def serve_index():
    with open("/home/aifa/5G-World/index.json", "r") as f:
        index_data = json.load(f)
    return jsonify(index_data)

@app.route('/list-yamls')
def list_yaml_files():
    files = [f for f in os.listdir(YAML_DIR) if f.endswith(".yaml")]
    return jsonify(files)

@app.route('/yaml/<filename>')
def serve_yaml(filename):
    return send_from_directory(YAML_DIR, filename)

@app.route('/parsed/<filename>')
def serve_parsed_json(filename):
    json_path = Path(PARSED_JSON_DIR) / filename.replace(".yaml", ".json")
    yaml_path = Path(YAML_DIR) / filename

    if not json_path.exists():
        try:
            print(f"ℹ️ JSON not found → running swagger-cli bundle for {filename}")
            subprocess.run([
                "swagger-cli", "bundle", str(yaml_path),
                "--outfile", str(json_path),
                "--type", "json"
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"💥 swagger-cli failed for {filename}: {e}")
            return jsonify({"error": f"swagger-cli failed: {e}"}), 500

    try:
        with open(json_path, "r") as f:
            swagger_json = json.load(f)

        parsed_summary = []
        
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
                # Extract request body fields
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
                    responses.append({"status_code": status_code, "description": description})

                # Append to parsed_summary
                parsed_summary.append({
                    "path": path,
                    "method": method_name.upper(),
                    "operationId": op.get("operationId", ""),
                    "parameters": params,
                    "request_body_required_fields": request_body_required_fields,
                    "responses": responses
                    })


        return jsonify(parsed_summary)

    except Exception as e:
        print(f"💥 Failed to parse {filename}: {e}")
        return jsonify({"error": str(e)}), 500


# from flask import Flask, send_from_directory, jsonify
# import os
# from pathlib import Path
# import yaml
# import json
# from prance import ResolvingParser
# from openapi_schema_pydantic import OpenAPI
# from openapi_schema_pydantic import (
#     OpenAPI,
#     Operation,
#     PathItem,
#     Reference,
#     RequestBody,
#     Response,
# )
# import traceback
# import sys
# sys.path.append("/home/aifa/5G-World/Yaml-Files/")
# # Use your existing parse_openapi_yaml function (import or define it here)
# #from parse_per_nf import parse_openapi_yaml  # Adjust if needed

# api_group_to_nf = {
#     "Namf": "AMF",
#     "Nsmf": "SMF",
#     "Nudm": "UDM",
#     "Nausf": "AUSF",
#     "Nnrf": "NRF",
#     "Npcf": "PCF",
#     "Nchf": "CHF",
#     "Nnef": "NEF",
#     "Nbsf": "BSF",
#     "Nlmf": "LMF",
#     "Nnssf": "NSSF",
#     "Nudr": "UDR",
#     "Nsmsf": "SMSF",
#     "N5g-eir": "EIR",
#     "Nsepp": "SEPP",
#     "Nmnpf": "MNPF",
#     "Nucmf": "UCMF"
# }
# def strip_callbacks(spec):
#     if "paths" in spec:
#         for _, path_obj in spec["paths"].items():
#             for method in path_obj:
#                 if isinstance(path_obj[method], dict) and "callbacks" in path_obj[method]:
#                     del path_obj[method]["callbacks"]

# def parse_yaml_with_prance(file_path, validate=False):
#     parser = ResolvingParser(str(file_path), lazy=True, strict=False,backend="openapi-spec-validator" if validate else None,recursion_limit=30)
#     parser.parse()  # Resolves all $ref and flattens spec

#     # This spec is fully resolved and clean for Pydantic
#     try:
#         openapi = OpenAPI.parse_obj(parser.specification)
#         return openapi
#     except Exception as e:
#     # Try fallback: remove callbacks and retry
#         print(f"⚠️ Parsing failed for {file_path} with callbacks. Retrying without callbacks...")
#         strip_callbacks(parser.specification)
#     try:
#         openapi = OpenAPI.parse_obj(parser.specification)
#         return openapi
#     except Exception as inner:
#         print(f"❌ Still failed after stripping callbacks: {file_path}")
#         raise inner


# def safe_attr(obj, attr, fallback=""):
#     #print("CAME HERE", attr)
#     try:
#         value = getattr(obj, attr)
#         if value is None:
#             return fallback
#         return value
#     except AttributeError:
#         fallback = attr
#         return fallback

# app = Flask(__name__)
# YAML_DIR = "/home/aifa/5G-World/Yaml-Files/5GC_APIs"

# @app.route('/')
# def serve_home():
#     #print(os.path.join(os.getcwd(), "Web-UI"))
#     return send_from_directory(os.path.join(os.getcwd()),  "viewer.html")

# @app.route('/list-yamls')
# def list_yaml_files():
#     files = [f for f in os.listdir(YAML_DIR) if f.endswith(".yaml")]
#     return jsonify(files)

# @app.route('/yaml/<filename>')
# def serve_yaml(filename):
#     #print(YAML_DIR, filename)
#     return send_from_directory(YAML_DIR, filename)

# @app.route('/parsed/<filename>')
# def serve_parsed_json(filename):
#     yaml_path = Path(YAML_DIR) / filename
#     json_path = Path("/home/aifa/5G-World/Parsed-JSON") / filename.replace(".yaml", ".json")

#     # ✅ If JSON already exists, return it directly
#     if json_path.exists():
#         with open(json_path, 'r') as f:
#             return jsonify(json.load(f))

#     try:
#         openapi = parse_yaml_with_prance(yaml_path, validate=True)

#         parsed_summary = []
#         ts_code = filename.split("_")[0]
#         api_group = openapi.info.title if openapi.info and openapi.info.title else "UNKNOWN"
#         nf_name = api_group_to_nf.get(api_group.split("_")[0], "UNKNOWN")

#         http_methods = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}

#         for path, path_item in openapi.paths.items():
#             for method_name in path_item.__fields_set__:
#                 if method_name not in http_methods:
#                     continue
#                 op = getattr(path_item, method_name)
#                 if not op or not op.operationId:
#                     continue

#                 parsed_summary.append({
#                     "path": path,
#                     "method": method_name.upper(),
#                     "operationId": op.operationId,
#                     "tags": op.tags or [],
#                     "summary": op.summary or "",
#                     "description": op.description or "",
#                     "ts": ts_code,
#                     "nf": nf_name,
#                     "source_file": filename
#                 })

#         # ✅ Save for future quick loads
#         with open(json_path, 'w') as f:
#             json.dump(parsed_summary, f, indent=2)

#         return jsonify(parsed_summary)

#     except Exception as e:
#         print(f"💥 Failed to parse {filename}: {e}")
#         return jsonify({"HERE error": str(e)}), 500


# # @app.route('/parsed/<filename>')
# # def serve_parsed_json(filename):
# #     yaml_path = Path(YAML_DIR) / filename
# #     try:
# #         openapi = parse_yaml_with_prance(yaml_path, validate=True)

# #         parsed_summary = []
# #         ts_code = filename.split("_")[0]
# #         api_group = openapi.info.title if openapi.info and openapi.info.title else "UNKNOWN"
# #         nf_name = api_group_to_nf.get(api_group.split("_")[0], "UNKNOWN")

# #         http_methods = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}

# #         for path, path_item in openapi.paths.items():
# #             for method_name in path_item.__fields_set__:
# #                 if method_name not in http_methods:
# #                     continue
# #                 op = getattr(path_item, method_name)
# #                 if not op or not op.operationId:
# #                     continue

# #                 parsed_summary.append({
# #                     "path": path,
# #                     "method": method_name.upper(),
# #                     "operationId": op.operationId,
# #                     "tags": op.tags or [],
# #                     "summary": op.summary or "",
# #                     "description": op.description or "",
# #                     "ts": ts_code,
# #                     "nf": nf_name,
# #                     "source_file": filename
# #                 })

# #         return jsonify(parsed_summary)

# #     except Exception as e:
# #         print(f"💥 Failed to parse {filename}: {e}")
# #         return jsonify({"HERE error": str(e)}), 500




#     # try:
#     #     data = parse_openapi_yaml(yaml_path, Path(YAML_DIR))
#     #     return jsonify(data)
#     # except Exception as e:
#     #     return jsonify({"error": str(e)}), 500
#     # try:
#     #     with open(yaml_path, "r") as f:
#     #         raw = yaml.safe_load(f)
#     #         print("🧾 Top-level keys in raw:", list(raw.keys()))
#     #         print("📄 Raw info.title:", raw.get("info", {}).get("title"))
#     #     openapi = OpenAPI.parse_obj(raw)
#         #OpenAPI.update_forward_refs()
#         #PathItem.update_forward_refs()
#         #Operation.update_forward_refs()
#         # RequestBody.update_forward_refs()
#         # Response.update_forward_refs()
#         # Reference.update_forward_refs()
#     #     print(type(openapi))
#     #     print(type(raw))


#     #     parsed_summary = []

#     #     for path, path_item in openapi.paths.items():
#     #         for method_name in path_item.__fields_set__:
#     #              op = getattr(path_item, method_name)
#     #              if not op or not op.operationId:
#     #                 continue
#     #              parsed_summary.append({
#     #                 "path": path,
#     #                 "method": method_name.upper(),
#     #                 "operationId": safe_attr(op, "operationId"),
#     #                 "tags": safe_attr(op, "tags", []),
#     #                 "summary": safe_attr(op, "summary"),
#     #                 "description": safe_attr(op, "description"),
#     #                 "source_file": filename
#     #                                     })

#     #     return jsonify(parsed_summary)
    
#     # except Exception as e:
#     #     print("💥 Exception during OpenAPI parsing:")
#     #     traceback.print_exc()
#     #     return jsonify({
#     #         "HERE error": str(e),
#     #         "trace": traceback.format_exc()
#     #         }), 500
if __name__ == '__main__':
     app.run(debug=True)
