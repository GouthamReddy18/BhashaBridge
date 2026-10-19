import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

try:
    import jsonschema
except ImportError:
    jsonschema = None

from app.services.dataset_validation import validate_dataset
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize
from scripts.validate_dataset import main

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "data" / "schema" / "annotation.schema.json"

def make_record(text="hello there", record_id="unit-001"):
    normalized = normalize_whitespace(text)
    return {"annotation_version":"1.0", "id":record_id, "text":text,
        "normalized_text":normalized, "source_type":"synthetic_illustrative",
        "annotation_status":"draft",
        "annotation_provenance":{"method":"test_fixture", "details":"Test-only fixture.", "origin":"human"},
        "tokens":[{"index":t.index,"surface":t.text,"start":t.start,"end":t.end,"language_label":"UNKNOWN"} for t in tokenize(normalized)],
        "romanized_interpretation":None,"telugu_script_equivalent":None,"ambiguity":None,"reference_translation":None}

def ambiguity(status="detected", selected=None):
    return {"status":status,"candidates":[
        {"candidate_id":"sense_a","meaning":"illustrative A","source":"test fixture"},
        {"candidate_id":"sense_b","meaning":"illustrative B","source":"test fixture"}],
        "selected_candidate":selected,"evidence":"test only","rule_id":"test.fixture"}

def record_with_ambiguity(status="detected", selected=None):
    record=make_record(); record["ambiguity"]=ambiguity(status,selected)
    record["annotation_provenance"]["fields"]={"ambiguity":{"origin":"machine","review_status":"not_reviewed","details":"test fixture"}}
    return record

class DatasetValidationTests(unittest.TestCase):
    def validate_records(self, *records):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"records.jsonl"
            path.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records),encoding="utf-8")
            return validate_dataset(path)

    def test_valid_illustrative_draft_warning_is_nonblocking(self):
        report=self.validate_records(make_record())
        self.assertTrue(report.valid); self.assertEqual(report.records_examined,1)
        self.assertEqual(report.errors,[]); self.assertEqual(len(report.warnings),1)

    def test_malformed_json_line_is_reported_and_later_lines_continue(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"bad.jsonl"
            path.write_text("\n{broken\n"+json.dumps(make_record(record_id="after"))+"\n",encoding="utf-8")
            report=validate_dataset(path)
        self.assertEqual(report.errors[0].line,2); self.assertIn("malformed JSON",report.errors[0].message)
        self.assertEqual(report.records_examined,2); self.assertEqual(len(report.warnings),1)

    def test_duplicate_top_level_json_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"dup.jsonl"
            path.write_text('{"id":"first","id":"second"}\n'+json.dumps(make_record(record_id="next"))+"\n",encoding="utf-8")
            report=validate_dataset(path)
        self.assertEqual(report.errors[0].line,1); self.assertIn("duplicate JSON object key 'id'",report.errors[0].message)
        self.assertEqual(report.records_examined,2); self.assertEqual(len(report.warnings),1)

    def test_duplicate_nested_json_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"dup.jsonl"
            path.write_text('{"id":"nested","meta":{"origin":"human","origin":"machine"}}\n',encoding="utf-8")
            report=validate_dataset(path)
        self.assertEqual(report.errors[0].line,1); self.assertIn("duplicate JSON object key 'origin'",report.errors[0].message)

    def test_required_fields_duplicate_ids_and_nonblank_strings(self):
        report=self.validate_records({"id":"missing"},make_record(record_id="same"),make_record(record_id="same"))
        self.assertTrue(any("missing required field: text" in e.message for e in report.errors))
        self.assertTrue(any("duplicate record id" in e.message for e in report.errors))
        for field in ("id","text","normalized_text","source_type"):
            with self.subTest(field=field):
                record=make_record(); record[field]="   "
                self.assertTrue(any(f"{field} must be a nonblank string" in e.message for e in self.validate_records(record).errors))

    def test_invalid_language_label_index_offset_surface_and_overlap(self):
        record=make_record(); record["tokens"][0]["language_label"]="MARS"; record["tokens"][1]["index"]=8
        errors=[e.message for e in self.validate_records(record).errors]
        self.assertTrue(any("unsupported language_label" in e for e in errors)); self.assertTrue(any("index must equal" in e for e in errors))
        record=make_record(); record["tokens"][0]["start"]=1
        self.assertTrue(any("normalized-text slice" in e.message for e in self.validate_records(record).errors))
        record=make_record("a b"); record["tokens"][1].update(start=0,end=1)
        self.assertTrue(any("overlaps or is out of order" in e.message for e in self.validate_records(record).errors))

    def test_empty_text_and_inconsistent_normalization(self):
        record=make_record("hello"); record["text"]="  "; record["normalized_text"]=""
        self.assertFalse(self.validate_records(record).valid)
        record=make_record(); record["normalized_text"]="different"
        self.assertTrue(any("does not match project whitespace normalization" in e.message for e in self.validate_records(record).errors))

    def test_status_version_notes_and_nested_extra_properties(self):
        record=make_record(); record.update(annotation_status=["draft"],annotation_version="9.9",annotation_notes=4)
        errors=[e.message for e in self.validate_records(record).errors]
        self.assertTrue(any("annotation_status" in e for e in errors)); self.assertTrue(any("unsupported annotation_version" in e for e in errors)); self.assertTrue(any("annotation_notes" in e for e in errors))
        cases=[]
        record=make_record(); record["tokens"][0]["kind"]="word"; cases.append((record,"tokens[0] has unsupported property"))
        record=make_record(); record["ambiguity"]=ambiguity(); record["ambiguity"]["extra"]=True; cases.append((record,"ambiguity has unsupported property"))
        record=make_record(); record["review"]={"status":"not_reviewed","extra":True}; cases.append((record,"review has unsupported property"))
        for item,message in cases:
            with self.subTest(message=message): self.assertTrue(any(message in e.message for e in self.validate_records(item).errors))

    def test_ambiguity_detected_resolved_abstained_contract(self):
        for status,selected in (("detected",None),("resolved","sense_a"),("abstained",None)):
            with self.subTest(valid_status=status):
                self.assertTrue(self.validate_records(record_with_ambiguity(status,selected)).valid)

        invalid_cases=(
            ("resolved",None,"resolved ambiguity must select a listed candidate_id"),
            ("resolved","unknown","resolved ambiguity must select a listed candidate_id"),
            ("abstained","sense_a","abstained ambiguity must have selected_candidate null"),
            ("detected","sense_a","detected ambiguity must have selected_candidate null"),
            ("unknown",None,"ambiguity.status must be detected, resolved, or abstained"),
        )
        for status,selected,expected_error in invalid_cases:
            with self.subTest(invalid_status=status,selected=selected):
                report=self.validate_records(record_with_ambiguity(status,selected))
                self.assertIn(expected_error,[issue.message for issue in report.errors])

    def test_detected_ambiguity_with_null_selection_is_valid(self):
        report=self.validate_records(record_with_ambiguity("detected",None))
        self.assertTrue(report.valid,report.errors)

    def test_abstained_ambiguity_with_null_selection_is_valid(self):
        report=self.validate_records(record_with_ambiguity("abstained",None))
        self.assertTrue(report.valid,report.errors)

    def test_reviewed_status_conflicts_with_draft_record_status(self):
        record=make_record()
        record["review"]={"status":"reviewed","reviewer_id":"test-fixture-pseudonym","reviewed_at":"2026-01-10"}
        report=self.validate_records(record)
        self.assertIn("review.status reviewed requires annotation_status reviewed",[issue.message for issue in report.errors])

        record["annotation_status"]="reviewed"
        corrected=self.validate_records(record)
        self.assertTrue(corrected.valid,corrected.errors)

    def test_duplicate_candidate_ids_are_rejected(self):
        record=make_record(); value=ambiguity(); value["candidates"][1]["candidate_id"]="sense_a"; record["ambiguity"]=value
        self.assertTrue(any("duplicate ambiguity candidate_id" in e.message for e in self.validate_records(record).errors))

    def test_review_states_and_canonical_calendar_dates(self):
        record=make_record(); record["annotation_status"]="reviewed"; record["review"]={"status":"reviewed","reviewer_id":"test-only-pseudonym","reviewed_at":"2026-01-10"}
        self.assertTrue(self.validate_records(record).valid)
        for value in ("20260110","2026-02-30","2026-1-10"):
            record=make_record(); record["annotation_status"]="reviewed"; record["review"]={"status":"reviewed","reviewer_id":"test-only","reviewed_at":value}
            with self.subTest(date=value): self.assertFalse(self.validate_records(record).valid)
        record=make_record(); record["annotation_status"]="reviewed"; record["review"]={"status":"disputed","reviewer_id":"test-only","reviewed_at":"2026-01-10"}
        self.assertFalse(self.validate_records(record).valid)

    def test_machine_suggestions_are_distinct_from_reviewed_fields(self):
        record=make_record(); record["romanized_interpretation"]="suggestion"
        record["annotation_provenance"]["fields"]={"romanized_interpretation":{"origin":"machine","review_status":"not_reviewed","details":"synthetic test suggestion"}}
        self.assertTrue(self.validate_records(record).valid)
        record["annotation_provenance"]["fields"]["romanized_interpretation"]["review_status"]="reviewed"
        self.assertFalse(self.validate_records(record).valid)

    def test_reference_translation_requires_review_human_origin_and_source(self):
        record=make_record(); record["reference_translation"]="test translation"
        self.assertFalse(self.validate_records(record).valid)
        record["annotation_provenance"]["fields"]={"reference_translation":{"origin":"machine","review_status":"not_reviewed","details":"test only","source_reference":"fixture"}}
        self.assertFalse(self.validate_records(record).valid)
        record=make_record(); record["annotation_status"]="reviewed"; record["review"]={"status":"reviewed","reviewer_id":"test-only-pseudonym","reviewed_at":"2026-01-10"}; record["reference_translation"]="test translation"
        record["annotation_provenance"]["fields"]={"reference_translation":{"origin":"human","review_status":"reviewed","details":"test fixture only","source_reference":"test-source-id"}}
        self.assertTrue(self.validate_records(record).valid)

    def test_invalid_translation_type_and_optional_fields_can_be_absent(self):
        record=make_record(); record["reference_translation"]={"bad":True}
        self.assertTrue(any("reference_translation must be a nonblank string" in e.message for e in self.validate_records(record).errors))
        self.assertTrue(self.validate_records(make_record()).valid)

    def test_astral_unicode_offsets_are_python_code_points(self):
        record=make_record(chr(0x1f600)+" hello"); report=self.validate_records(record)
        self.assertTrue(report.valid,report.errors); self.assertEqual(record["tokens"][1]["start"],2)
        self.assertEqual(record["normalized_text"][2:7],"hello")

    def test_cli_exit_codes_for_valid_invalid_malformed_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory); valid=directory/"valid.jsonl"; valid.write_text(json.dumps(make_record())+"\n",encoding="utf-8")
            invalid=directory/"invalid.jsonl"; invalid.write_text(json.dumps({"id":"bad"})+"\n",encoding="utf-8")
            malformed=directory/"malformed.jsonl"; malformed.write_text("{broken\n",encoding="utf-8")
            for path,expected,phrase in ((valid,0,"Warnings: 1"),(invalid,1,"Errors:"),(malformed,1,"malformed JSON"),(directory/"missing.jsonl",1,"cannot read dataset")):
                output=StringIO()
                with redirect_stdout(output): result=main([str(path)])
                with self.subTest(path=path.name): self.assertEqual(result,expected); self.assertIn(phrase,output.getvalue())

    def test_malformed_nested_types_report_errors_without_raising(self):
        record=make_record(); record["tokens"][0]["language_label"]=[]
        record["ambiguity"]={"status":[],"candidates":[],"selected_candidate":[],"evidence":"x","rule_id":"x"}
        record["review"]={"status":[],"reviewer_id":None,"reviewed_at":None}
        report=self.validate_records(record)
        self.assertFalse(report.valid)
        self.assertGreaterEqual(len(report.errors),3)

    def test_optional_linguistic_fields_may_be_omitted(self):
        record=make_record()
        for field in ("romanized_interpretation","telugu_script_equivalent","ambiguity","reference_translation"):
            record.pop(field)
        self.assertTrue(self.validate_records(record).valid)

    def test_draft_without_review_metadata_does_not_require_reviewer(self):
        record=make_record()
        self.assertNotIn("review",record)
        self.assertTrue(self.validate_records(record).valid)

    def test_not_reviewed_metadata_must_not_claim_reviewer_or_date(self):
        record=make_record(); record["review"]={"status":"not_reviewed","reviewer_id":"invented","reviewed_at":"2026-01-10"}
        errors=[issue.message for issue in self.validate_records(record).errors]
        self.assertTrue(any("cannot contain reviewer_id or reviewed_at" in message for message in errors))

    def test_reviewed_record_requires_matching_field_review_provenance(self):
        record=make_record(); record["annotation_status"]="reviewed"
        record["review"]={"status":"reviewed","reviewer_id":"test-only","reviewed_at":"2026-01-10"}
        record["romanized_interpretation"]="test gloss"
        record["annotation_provenance"]["fields"]={"romanized_interpretation":{"origin":"human","review_status":"not_reviewed","details":"test"}}
        self.assertTrue(any("reviewed record requires romanized_interpretation provenance review_status reviewed" in issue.message for issue in self.validate_records(record).errors))

    @unittest.skipIf(jsonschema is None,"jsonschema is optional and not a runtime dependency")
    def test_schema_python_parity_on_overlapping_constraints(self):
        schema=json.loads(SCHEMA_PATH.read_text(encoding="utf-8")); validator=jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
        cases=[make_record()]
        item=make_record(); item["id"]="   "; cases.append(item)
        item=make_record(); item["annotation_notes"]=1; cases.append(item)
        item=make_record(); item["tokens"][0]["extra"]=1; cases.append(item)
        item=make_record(); item["ambiguity"]=ambiguity("detected","sense_a"); cases.append(item)
        item=make_record(); item["annotation_status"]="reviewed"; item["review"]={"status":"reviewed","reviewer_id":"test-only","reviewed_at":"20260110"}; cases.append(item)
        item=make_record(); item["romanized_interpretation"]="suggestion"; item["annotation_provenance"]["fields"]={"romanized_interpretation":{"origin":"machine","review_status":"not_reviewed","details":"test fixture"}}; cases.append(item)
        item=make_record(); item["annotation_notes"]="translation fixture remains absent"; cases.append(item)
        for index,record in enumerate(cases):
            with self.subTest(case=index): self.assertEqual(validator.is_valid(record),self.validate_records(record).valid)

if __name__ == "__main__": unittest.main()
