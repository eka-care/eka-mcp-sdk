from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

import tantivy
from tantivy import Tokenizer, TextAnalyzerBuilder, Query, Occur

logger = logging.getLogger(__name__)

class DoctorSearchEngine:
    """Search engine for doctor index with multi-valued hospitals"""

    def __init__(self, index_path: str):
        self.index_path = Path(index_path)

        if not self.index_path.exists():
            raise FileNotFoundError(f"Index not found at {self.index_path}")

        self.index = tantivy.Index.open(str(self.index_path))
        self._register_custom_analyzers()
        self.searcher = self.index.searcher()
        self.schema = self.index.schema

    def _register_custom_analyzers(self):
        """Register custom analyzers for ngram search"""
        ngram_tokenizer = Tokenizer.ngram(min_gram=2, max_gram=4, prefix_only=False)
        ngram_analyzer = TextAnalyzerBuilder(tokenizer=ngram_tokenizer).build()

        edge_ngram_tokenizer = Tokenizer.ngram(min_gram=1, max_gram=4, prefix_only=True)
        edge_ngram_analyzer = TextAnalyzerBuilder(tokenizer=edge_ngram_tokenizer).build()

        self.index.register_tokenizer("ngram_analyzer", ngram_analyzer)
        self.index.register_tokenizer("edge_ngram_analyzer", edge_ngram_analyzer)

    def _parse_hospitals(self, hospitals_str: str) -> List[Dict[str, str]]:
        """Parse hospitals multi-value field"""
        hospitals = []
        if not hospitals_str:
            return hospitals
        for part in hospitals_str.split("|"):
            fields = part.split(":")
            if len(fields) >= 5:
                hospitals.append({
                    "name": fields[0],
                    "city": fields[1],
                    "state": fields[2],
                    "location_id": fields[3],
                    "region_id": fields[4],
                })
        return hospitals

    def _build_query(
        self,
        workspace_id: str,
        doctor_id: str = None,
        doctor_name: str = None,
        specialization: str = None,
        hospital_name: str = None,
        city: str = None,
        state: str = None,
        gender: str = None,
        language: str = None,
        min_experience: int = None,
        max_experience: int = None,
        experience: int = None,
        is_active: bool = True,
    ) -> Query:
        """Build compound query with all filters"""
        query_parts = []

        # Exact match: workspace_id (mandatory)
        if not workspace_id:
            raise ValueError("workspace_id is required for doctor search")
        safe_workspace_id = str(workspace_id).replace('"', '\\"')
        q = self.index.parse_query(f"\"{safe_workspace_id}\"", ["workspace_id"])
        query_parts.append((Occur.Must, q))

        # Exact match: doctor_id
        if doctor_id:
            q = self.index.parse_query(doctor_id, ["doctor_id"])
            query_parts.append((Occur.Must, q))

        # Fuzzy: doctor_name
        if doctor_name:
            q = self.index.parse_query(
                doctor_name.strip().lower(),
                ["doctor_name", "doctor_name_ngram"],
                fuzzy_fields={"doctor_name_ngram": (True, 2, True)},
                field_boosts={"doctor_name": 5.0, "doctor_name_ngram": 2.0},
            )
            query_parts.append((Occur.Should, q))

        # Fuzzy: specialization
        if specialization:
            q = self.index.parse_query(
                specialization.strip().lower(),
                ["speciality", "speciality_ngram"],
                fuzzy_fields={"speciality_ngram": (True, 2, True)},
                field_boosts={"speciality": 5.0, "speciality_ngram": 2.0},
            )
            query_parts.append((Occur.Should, q))

        # Fuzzy: hospital_name
        if hospital_name:
            q = self.index.parse_query(
                hospital_name.strip().lower(),
                ["hospital", "hospital_ngram"],
                fuzzy_fields={"hospital_ngram": (True, 2, True)},
                field_boosts={"hospital": 5.0, "hospital_ngram": 2.0},
            )
            query_parts.append((Occur.Should, q))

        # Exact: city
        if city:
            q = self.index.parse_query(city, ["city"])
            query_parts.append((Occur.Must, q))

        # Exact: state
        if state:
            q = self.index.parse_query(state, ["state"])
            query_parts.append((Occur.Must, q))

        # Exact: gender
        if gender:
            q = self.index.parse_query(gender, ["gender"])
            query_parts.append((Occur.Must, q))

        # Multi-value: language
        if language:
            q = self.index.parse_query(language, ["languages"])
            query_parts.append((Occur.Must, q))

        # Boolean: is_active (default True)
        if is_active:
            q = self.index.parse_query("Yes", ["is_active"])
            query_parts.append((Occur.Must, q))

        # Range: experience - use parsed query with range syntax
        if experience is not None:
            q = self.index.parse_query(f"experience:{experience}", default_field_names=["experience"])
            query_parts.append((Occur.Must, q))
        elif min_experience is not None or max_experience is not None:
            min_exp = min_experience if min_experience is not None else 0
            max_exp = max_experience if max_experience is not None else 100
            q = self.index.parse_query(f"experience:[{min_exp} TO {max_exp}]", default_field_names=["experience"])
            query_parts.append((Occur.Must, q))

        # Default query if no search terms
        if not query_parts:
            q = self.index.parse_query("Yes", ["is_active"])
            query_parts.append((Occur.Should, q))

        if len(query_parts) == 1:
            return query_parts[0][1]
        return Query.boolean_query(query_parts)

    def search_doctor_by_id(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        """Search for a specific doctor by ID"""
        try:
            query = self.index.parse_query(doctor_id, ["doctor_id"])
            result = self.searcher.search(query, 1)

            if not result.hits:
                return None

            score, doc_address = result.hits[0]
            return self._doc_to_dict(self.searcher.doc(doc_address), score)
        except Exception as e:
            logger.error(f"Error searching doctor by id {doctor_id}: {e}")
            return None

    def search_doctors(
        self,
        workspace_id: str,
        doctor_id: str = None,
        doctor_name: str = None,
        specialization: str = None,
        hospital_name: str = None,
        city: str = None,
        state: str = None,
        gender: str = None,
        language: str = None,
        min_experience: int = None,
        max_experience: int = None,
        experience: int = None,
        is_active: bool = True,
        limit: int = 15,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search doctors with all filter combinations.
        """
        try:
            query = self._build_query(
                workspace_id=workspace_id,
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                specialization=specialization,
                hospital_name=hospital_name,
                city=city,
                state=state,
                gender=gender,
                language=language,
                min_experience=min_experience,
                max_experience=max_experience,
                experience=experience,
                is_active=is_active,
            )

            # Fetch more than needed for offset
            search_result = self.searcher.search(query, limit + offset)

            results = []
            for i, (score, doc_address) in enumerate(search_result.hits):
                if i < offset:
                    continue
                if len(results) >= limit:
                    break
                doc = self.searcher.doc(doc_address)
                results.append(self._doc_to_dict(doc, score))

            return results
        except Exception as e:
            logger.error(f"Error searching doctors: {e}")
            return []

    def _doc_to_dict(self, doc, score: float) -> Dict[str, Any]:
        """Convert tantivy document to response dict"""
        hospitals_str = doc.get_first("hospitals_stored") or ""
        hospitals = self._parse_hospitals(hospitals_str)

        return {
            "score": score,
            "doctor_id": doc.get_first("doctor_id"),
            "doctor_name": doc.get_first("doctor_name_stored"),
            "specialization": doc.get_first("speciality_stored"),
            "specialty_id": doc.get_first("speciality_id"),
            "gender": doc.get_first("gender_stored"),
            "years_experience": doc.get_first("experience"),
            "languages": doc.get_first("languages_stored"),
            "hospitals": hospitals,
            # Empty for API compatibility
            "working_weekdays": "",
            "working_hours": "",
            # Profile
            "profile_image_url": doc.get_first("profile_pic"),
            "profile_link_url": doc.get_first("profile_url"),
            # Added for compat
            "city": hospitals[0]['city'] if hospitals else None,
        }
