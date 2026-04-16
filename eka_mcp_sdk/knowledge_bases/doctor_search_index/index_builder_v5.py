#!/usr/bin/env python3
"""
Tantivy Index Builder v5 - Single doctor per record with multi-valued hospitals
"""

import csv
import json
from pathlib import Path
from typing import List, Set, Dict, Any

import tantivy
from tantivy import TextAnalyzerBuilder, Tokenizer


class DoctorIndexBuilderV5:
    """
    Build Tantivy index for v5 schema:
    - One record per doctor
    - Multi-valued hospitals field
    - Fuzzy search on name, speciality, hospital
    - Exact match on gender, city, state, is_active
    - Range queries on experience
    - Multi-value match on languages
    """

    def __init__(self, index_path: str = "search_index_v5"):
        self.index_path = Path(index_path)
        self.schema = None
        self.index = None
        self.analyzers = {}

    def create_custom_analyzers(self):
        """Create custom text analyzers"""
        # Ngram analyzer for fuzzy/partial matching (2-4 character ngrams)
        ngram_tokenizer = Tokenizer.ngram(min_gram=2, max_gram=4, prefix_only=False)
        self.analyzers["ngram"] = TextAnalyzerBuilder(tokenizer=ngram_tokenizer).build()

        # Edge ngram analyzer for autocomplete
        edge_ngram_tokenizer = Tokenizer.ngram(min_gram=1, max_gram=4, prefix_only=True)
        self.analyzers["edge_ngram"] = TextAnalyzerBuilder(
            tokenizer=edge_ngram_tokenizer
        ).build()

    def create_schema(self) -> tantivy.Schema:
        """Create optimized schema for v5"""
        self.create_custom_analyzers()
        schema_builder = tantivy.SchemaBuilder()

        # === STORED FIELDS ===
        schema_builder.add_text_field("workspace_id", stored=True, tokenizer_name="raw")
        schema_builder.add_text_field("doctor_id", stored=True)
        schema_builder.add_text_field("doctor_name_stored", stored=True)
        schema_builder.add_text_field("actual_id", stored=True)
        schema_builder.add_text_field("gender_stored", stored=True)
        schema_builder.add_text_field("speciality_id", stored=True)
        schema_builder.add_text_field("speciality_stored", stored=True)
        schema_builder.add_text_field("is_active", stored=True, tokenizer_name="raw")
        schema_builder.add_text_field("profile_url", stored=True)
        schema_builder.add_text_field("profile_pic", stored=True)
        schema_builder.add_text_field("languages_stored", stored=True)
        schema_builder.add_text_field("hospitals_stored", stored=True)  # Full multi-value string
        # Empty fields for API compatibility
        schema_builder.add_text_field("working_weekdays", stored=True)
        schema_builder.add_text_field("working_hours", stored=True)

        # === SEARCHABLE TEXT FIELDS ===
        # Doctor name - fuzzy search
        schema_builder.add_text_field("doctor_name", stored=False, tokenizer_name="en_stem")
        schema_builder.add_text_field("doctor_name_ngram", stored=False, tokenizer_name="ngram_analyzer")
        schema_builder.add_text_field("doctor_name_edge", stored=False, tokenizer_name="edge_ngram_analyzer")

        # Speciality - fuzzy search
        schema_builder.add_text_field("speciality", stored=False, tokenizer_name="en_stem")
        schema_builder.add_text_field("speciality_ngram", stored=False, tokenizer_name="ngram_analyzer")

        # Hospital names - fuzzy search (aggregated from all hospitals)
        schema_builder.add_text_field("hospital", stored=False, tokenizer_name="en_stem")
        schema_builder.add_text_field("hospital_ngram", stored=False, tokenizer_name="ngram_analyzer")

        # City - for text search (exact handled via facet)
        schema_builder.add_text_field("city", stored=False, tokenizer_name="default")

        # State - for text search
        schema_builder.add_text_field("state", stored=False, tokenizer_name="default")

        # Languages - for text search
        schema_builder.add_text_field("languages", stored=False, tokenizer_name="default")

        # Gender - for text search
        schema_builder.add_text_field("gender", stored=False, tokenizer_name="default")

        # Combined searchable field
        schema_builder.add_text_field("all_searchable", stored=False, tokenizer_name="en_stem")

        # === FACET FIELDS ===
        schema_builder.add_facet_field("gender_facet")
        schema_builder.add_facet_field("language_facet")  # Multi-value
        schema_builder.add_facet_field("city_facet")      # Multi-value (from hospitals)
        schema_builder.add_facet_field("state_facet")     # Multi-value (from hospitals)
        schema_builder.add_facet_field("is_active_facet")
        schema_builder.add_facet_field("speciality_facet")

        # === NUMERIC FIELDS ===
        schema_builder.add_integer_field("experience", stored=True, indexed=True, fast=True)

        self.schema = schema_builder.build()
        return self.schema

    def parse_hospitals(self, hospitals_str: str) -> List[Dict[str, str]]:
        """Parse hospitals multi-value field: hospital_name:city:state:location_id:region_id:region_name:location_name"""
        hospitals = []
        if not hospitals_str:
            return hospitals
        for part in hospitals_str.split("|"):
            fields = part.split(":")
            if len(fields) >= 5:
                hospital = {
                    "name": fields[0],
                    "city": fields[1],
                    "state": fields[2],
                    "location_id": fields[3],
                    "region_id": fields[4],
                }
                if len(fields) > 5:
                    hospital["region_name"] = fields[5]
                if len(fields) > 6:
                    hospital["location_name"] = fields[6]
                hospitals.append(hospital)
        return hospitals

    def parse_languages(self, lang_str: str) -> List[str]:
        """Parse comma-separated languages"""
        if not lang_str:
            return []
        return [lang.strip() for lang in lang_str.split(",") if lang.strip()]

    def sanitize_facet(self, value: str) -> str:
        """Sanitize string for facet (remove / and \\)"""
        return value.replace("/", "-").replace("\\", "-").strip()

    def load_data(self, csv_path: str = "master_doctor_index.csv") -> List[Dict[str, Any]]:
        """Load master CSV data"""
        data = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
        print(f"Loaded {len(data)} doctor records")
        return data

    def build_index(self, data: List[Dict[str, Any]]):
        """Build the index"""
        # Clean existing index files (keep CSV files)
        index_files = [
            f for f in self.index_path.iterdir()
            if f.suffix in [".fast", ".fieldnorm", ".idx", ".pos", ".store", ".term"]
            or f.name in ["meta.json", "metadata.json"]
        ]
        for f in index_files:
            f.unlink()
            print(f"Removed {f.name}")

        # Create index
        self.index = tantivy.Index(self.schema, path=str(self.index_path))

        # Register custom analyzers
        self.index.register_tokenizer("ngram_analyzer", self.analyzers["ngram"])
        self.index.register_tokenizer("edge_ngram_analyzer", self.analyzers["edge_ngram"])

        writer = self.index.writer(heap_size=150_000_000)

        # Track unique values
        unique_cities: Set[str] = set()
        unique_states: Set[str] = set()
        unique_languages: Set[str] = set()
        unique_genders: Set[str] = set()
        unique_specialities: Set[str] = set()

        print("Indexing documents...")
        for idx, row in enumerate(data):
            doc = tantivy.Document()

            # Parse hospitals
            hospitals = self.parse_hospitals(row.get("hospitals", ""))
            languages = self.parse_languages(row.get("languages", ""))

            # === STORED FIELDS ===
            doc.add_text("workspace_id", row.get("workspace_id", ""))
            doc.add_text("doctor_id", row.get("doctor_id", ""))
            doc.add_text("doctor_name_stored", row.get("name", ""))
            doc.add_text("actual_id", row.get("actual_id", ""))
            doc.add_text("gender_stored", row.get("gender", ""))
            doc.add_text("speciality_id", row.get("speciality_id", ""))
            doc.add_text("speciality_stored", row.get("speciality_name", ""))
            doc.add_text("is_active", row.get("is_active", ""))
            doc.add_text("profile_url", row.get("profile_url", ""))
            doc.add_text("profile_pic", row.get("profile_pic", ""))
            doc.add_text("languages_stored", row.get("languages", ""))
            doc.add_text("hospitals_stored", row.get("hospitals", ""))
            doc.add_text("working_weekdays", "")
            doc.add_text("working_hours", "")

            # === SEARCHABLE FIELDS ===
            name = row.get("name", "")
            speciality = row.get("speciality_name", "")
            gender = row.get("gender", "")

            # Name fields
            doc.add_text("doctor_name", name)
            doc.add_text("doctor_name_ngram", name.lower())
            doc.add_text("doctor_name_edge", name.lower())

            # Speciality fields
            speciality_alias = row.get("speciality_alias", "")
            spec_full = f"{speciality} {speciality_alias}".strip()
            doc.add_text("speciality", spec_full)
            doc.add_text("speciality_ngram", spec_full.lower())

            # Aggregate hospital names, cities, states
            hospital_names = " ".join([h["name"] for h in hospitals])
            cities = " ".join([h["city"] for h in hospitals])
            states = " ".join([h["state"] for h in hospitals])

            doc.add_text("hospital", hospital_names)
            doc.add_text("hospital_ngram", hospital_names.lower())
            doc.add_text("city", cities)
            doc.add_text("state", states)
            doc.add_text("languages", " ".join(languages))
            doc.add_text("gender", gender)

            # Combined searchable
            all_text = f"{name} {speciality} {hospital_names} {cities} {' '.join(languages)}"
            doc.add_text("all_searchable", all_text)

            # === FACET FIELDS ===
            if gender:
                doc.add_facet("gender_facet", tantivy.Facet.from_string(f"/gender/{self.sanitize_facet(gender)}"))
                unique_genders.add(gender)

            for lang in languages:
                doc.add_facet("language_facet", tantivy.Facet.from_string(f"/language/{self.sanitize_facet(lang)}"))
                unique_languages.add(lang)

            for h in hospitals:
                if h["city"]:
                    doc.add_facet("city_facet", tantivy.Facet.from_string(f"/city/{self.sanitize_facet(h['city'])}"))
                    unique_cities.add(h["city"])
                if h["state"]:
                    doc.add_facet("state_facet", tantivy.Facet.from_string(f"/state/{self.sanitize_facet(h['state'])}"))
                    unique_states.add(h["state"])

            is_active = row.get("is_active", "").lower()
            if is_active:
                doc.add_facet("is_active_facet", tantivy.Facet.from_string(f"/active/{is_active}"))

            if speciality:
                doc.add_facet("speciality_facet", tantivy.Facet.from_string(f"/speciality/{self.sanitize_facet(speciality)}"))
                unique_specialities.add(speciality)

            # === NUMERIC FIELDS ===
            try:
                exp = int(row.get("experience", 0) or 0)
            except ValueError:
                exp = 0
            doc.add_integer("experience", exp)

            writer.add_document(doc)

            if (idx + 1) % 500 == 0:
                print(f"  Indexed {idx + 1} documents...")

        print("Committing index...")
        writer.commit()
        writer.wait_merging_threads()

        # Save metadata
        metadata = {
            "total_documents": len(data),
            "unique_cities": sorted(list(unique_cities)),
            "unique_states": sorted(list(unique_states)),
            "unique_languages": sorted(list(unique_languages)),
            "unique_genders": sorted(list(unique_genders)),
            "unique_specialities": sorted(list(unique_specialities)),
            "schema_version": "v5",
            "schema_features": {
                "single_doc_per_doctor": True,
                "multi_value_hospitals": True,
                "fuzzy_search": ["name", "speciality", "hospital"],
                "exact_match": ["gender", "city", "state", "is_active"],
                "range_queries": ["experience"],
                "multi_value_match": ["languages", "city", "state"],
            },
        }

        with open(self.index_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"\nIndex built: {len(data)} docs")
        print(f"  Cities: {len(unique_cities)}, States: {len(unique_states)}")
        print(f"  Languages: {len(unique_languages)}, Specialities: {len(unique_specialities)}")


def main():
    import os
    os.chdir(Path(__file__).parent)

    builder = DoctorIndexBuilderV5(index_path=".")
    builder.create_schema()
    data = builder.load_data("master_doctor_index.csv")
    builder.build_index(data)


if __name__ == "__main__":
    main()


