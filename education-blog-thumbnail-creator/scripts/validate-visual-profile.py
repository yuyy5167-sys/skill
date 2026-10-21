#!/usr/bin/env python3
"""Resolve/validate image-profile contracts. Does not certify visual quality."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
KNOWN = {"cream-manga-mustard-v1": {"thumbnail", "section_image"},
         "bw-manga-thumbnail-v1": {"thumbnail"}}
SCOPES = {"thumbnail_only": ["thumbnail"], "h2_only": ["section_image"],
          "thumbnail_and_h2": ["thumbnail", "section_image"]}

def normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"

def digest(text):
    return hashlib.sha256(normalized(text).encode("utf-8")).hexdigest()

def load_profile(profile_id, root=ROOT, check_references=False):
    if profile_id not in KNOWN:
        raise ValueError("unknown profile ID: " + str(profile_id))
    base = Path(root) / "references"
    x = json.loads((base / (profile_id + ".json")).read_text(encoding="utf-8"))
    errors = []
    if x.get("profile_id") != profile_id or type(x.get("revision")) is not int or x["revision"] != 1:
        errors.append("invalid ID/revision")
    if set(x.get("assets", [])) != KNOWN[profile_id]:
        errors.append("unsupported asset declaration")
    for key in ["h2_direct_style_images_allowed", "trial_images_are_approved_examples"]:
        if x.get(key) is not False:
            errors.append(key + " must be false")
    fixed = normalized(x["fixed_prompt"])
    if digest(fixed) != x.get("fixed_prompt_sha256"):
        errors.append("JSON fixed_prompt SHA mismatch")
    md = (base / (profile_id + ".md")).read_text(encoding="utf-8")
    match = re.search(r"```text\n(.*?)```", md, re.S)
    if not match or match.group(1) != fixed:
        errors.append("Markdown fixed block differs from JSON")
    if x.get("fixed_prompt_sha256") not in md:
        errors.append("Markdown declared SHA missing")
    refs = x.get("approved_examples", []) + x.get("profile_character_references", [])
    ids = set()
    for e in refs:
        if e["id"] in ids:
            errors.append("duplicate reference ID " + e["id"])
        ids.add(e["id"])
        if e["role"] not in ["character_sheet", "style_example", "composition_guide", "comparison_image"]:
            errors.append("unknown reference role " + e["role"])
        if not re.fullmatch(r"[0-9a-f]{64}", e["sha256"]):
            errors.append("invalid SHA " + e["id"])
        if check_references:
            p = Path(e["path"])
            if not p.is_file():
                errors.append("missing reference " + str(p))
            elif hashlib.sha256(p.read_bytes()).hexdigest() != e["sha256"]:
                errors.append("changed reference " + str(p))
    if profile_id == "bw-manga-thumbnail-v1":
        if x.get("default_character_mode") != "personless" or x.get("person_requires_explicit_user_instruction") is not True:
            errors.append("invalid personless default/override contract")
        if x.get("brand_name_size_policy") != "match_reference_not_minimum" or x.get("brand_name_reference_id") not in ids:
            errors.append("missing preferred typography reference")
        for mode in ["personless", "person"]:
            if digest(x["character_policy_prompts"][mode]) != x["character_policy_sha256"].get(mode):
                errors.append("character policy SHA mismatch: " + mode)
    if errors:
        raise ValueError("; ".join(errors))
    return x

def resolve_request(request, root=ROOT, check_references=False):
    scope = request.get("asset_scope", "thumbnail_only")
    if scope not in SCOPES:
        raise ValueError("unknown asset_scope")
    needed = SCOPES[scope]
    mapping = request.get("asset_visual_profiles")
    legacy = request.get("visual_profile")
    if mapping is not None:
        if not isinstance(mapping, dict) or set(mapping) - {"thumbnail", "section_image"}:
            raise ValueError("invalid asset_visual_profiles")
        if any(not mapping.get(a) for a in needed):
            raise ValueError("missing requested asset profile")
        if legacy and any(mapping[a] != legacy for a in needed):
            raise ValueError("conflicting old and per-asset profiles")
    else:
        mapping = {a: legacy for a in needed}
    resolved = {}
    for asset in needed:
        spec = mapping[asset]
        if spec is None:
            resolved[asset] = {"visual_profile": None, "mode": "legacy_unspecified"}
            continue
        if not isinstance(spec, dict) or set(spec) != {"id", "revision"}:
            raise ValueError("profile must contain only id/revision")
        x = load_profile(spec["id"], root, check_references)
        if type(spec["revision"]) is not int or spec["revision"] != x["revision"]:
            raise ValueError("unknown revision")
        if asset not in x["assets"]:
            raise ValueError("profile does not support " + asset)
        contract = {"profile_id": spec["id"], "revision": spec["revision"],
                    "sha256": x["fixed_prompt_sha256"]}
        declared = request.get("asset_style_contracts", {}).get(asset)
        if declared is None and len(needed) == 1:
            declared = request.get("section_style_contract")
        if declared is not None and any(declared.get(k) != v for k, v in contract.items()):
            raise ValueError("declared asset SHA/ID/revision mismatch")
        item = {"visual_profile": spec, "section_style_contract": contract}
        if asset == "thumbnail" and spec["id"] == "bw-manga-thumbnail-v1":
            explicit = request.get("thumbnail_character_mode")
            alias = request.get("character_mode")
            if explicit and alias and explicit != alias:
                raise ValueError("conflicting character modes")
            mode = explicit or alias or x["default_character_mode"]
            if mode not in ["person", "personless"]:
                raise ValueError("invalid thumbnail character mode")
            instruction = request.get("thumbnail_character_instruction")
            if mode == "person" and (not isinstance(instruction, dict)
                    or not instruction.get("user_instruction") or not instruction.get("source_ref")):
                raise ValueError("person requires explicit user instruction and source")
            item.update(character_mode=mode,
                        character_instruction=instruction if mode == "person" else None,
                        character_policy_sha256=x["character_policy_sha256"][mode])
        if asset == "section_image":
            same = mapping.get("thumbnail") == spec
            item["runtime_style_delta_source"] = "same_profile_thumbnail_allowed" if same else "base_profile_only"
        resolved[asset] = item
    return resolved

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="cream-manga-mustard-v1", choices=sorted(KNOWN))
    ap.add_argument("--request-json", type=Path)
    ap.add_argument("--check-references", action="store_true")
    args = ap.parse_args()
    try:
        if args.request_json:
            request = json.loads(args.request_json.read_text(encoding="utf-8"))
            out = {"result": "pass", "resolved_assets": resolve_request(request, check_references=args.check_references),
                   "references_checked": args.check_references, "errors": []}
        else:
            x = load_profile(args.profile, check_references=args.check_references)
            out = {"result": "pass", "profile_id": x["profile_id"], "revision": x["revision"],
                   "fixed_prompt_sha256": x["fixed_prompt_sha256"],
                   "references_checked": args.check_references, "errors": []}
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"result": "fail", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())

