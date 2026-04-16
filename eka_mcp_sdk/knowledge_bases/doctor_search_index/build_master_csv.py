import csv
from collections import defaultdict

DOCTOR_CSV = "doctor_list.csv"
HOSPITAL_CSV = "hospital_list.csv"
SPECIALITY_CSV = "speciality_list.csv"
OUTPUT_CSV = "master_doctor_index.csv"


def load_hospitals():
    hospitals = {}
    with open(HOSPITAL_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            loc_id = row["Location ID"].strip()
            hospitals[loc_id] = {
                "name": row["Hospital Name"].strip(),
                "city": row["City"].strip(),
                "state": row["State"].strip(),
                "division": row["Division"].strip(),
                "region_id": row["Region ID"].strip(),
                "region_name": row["Region Name"].strip(),
                "location_name": row["Location Name"].strip(),
                "alias": row["Alias"].strip(),
                "page_link": row["Hospital Page Link"].strip(),
            }
    return hospitals


def load_specialities():
    specs = {}
    with open(SPECIALITY_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            spec_id = row["Speciality ID"].strip()
            specs[spec_id] = {
                "name": row["Speciality Name"].strip(),
                "alias": row.get("Speciality Alias", "").strip()
            }
    return specs


def build_master():
    hospitals = load_hospitals()
    specialities = load_specialities()

    # Group doctors: doctor_id -> {info, hospitals: [loc_id, ...]}
    doctors = defaultdict(lambda: {"info": None, "hospitals": []})

    with open(DOCTOR_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_id = row["Doctor ID"].strip()
            loc_id = row["Location ID"].strip()
            spec_id = row["Speciality ID"].strip()

            if doctors[doc_id]["info"] is None:
                doctors[doc_id]["info"] = {
                    "doctor_id": doc_id,
                    "name": row["Doctor Name"].strip(),
                    "actual_id": row["Actual ID"].strip(),
                    "gender": row["Gender"].strip(),
                    "experience": row["Years Of Experience"].strip(),
                    "is_active": row["Is Doctor ACTIVE?"].strip(),
                    "profile_url": row["Profile URL"].strip(),
                    "profile_pic": row["Profile Pic URL"].strip(),
                    "languages": row["Languages"].strip(),
                    "speciality_id": spec_id,
                    "speciality_name": specialities.get(spec_id, {}).get("name", "Unknown"),
                    "speciality_alias": specialities.get(spec_id, {}).get("alias", ""),
                }
            if loc_id not in doctors[doc_id]["hospitals"]:
                doctors[doc_id]["hospitals"].append(loc_id)

    # Write master CSV
    fieldnames = [
        "workspace_id",
        "doctor_id",
        "name",
        "actual_id",
        "gender",
        "experience",
        "speciality_id",
        "speciality_name",
        "speciality_alias",
        "is_active",
        "profile_url",
        "profile_pic",
        "languages",
        "hospitals",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for doc_id, data in doctors.items():
            info = data["info"]
            # Build hospitals multi-value field
            # Format: hospital_name:city:state:location_id:region_id:region_name:location_name
            hosp_parts = []
            for loc_id in data["hospitals"]:
                hosp = hospitals.get(loc_id, {})
                part = ":".join([
                    hosp.get("name", "Unknown"),
                    hosp.get("city", ""),
                    hosp.get("state", ""),
                    loc_id,
                    hosp.get("region_id", ""),
                    hosp.get("region_name", ""),
                    hosp.get("location_name", ""),
                ])
                hosp_parts.append(part)

            row = {
                "workspace_id": "78323888282175",
                "doctor_id": info["doctor_id"],
                "name": info["name"],
                "actual_id": info["actual_id"],
                "gender": info["gender"],
                "experience": info["experience"],
                "speciality_id": info["speciality_id"],
                "speciality_name": info["speciality_name"],
                "speciality_alias": info["speciality_alias"],
                "is_active": info["is_active"],
                "profile_url": info["profile_url"],
                "profile_pic": info["profile_pic"],
                "languages": info["languages"],
                "hospitals": "|".join(hosp_parts),
            }
            writer.writerow(row)

    print(f"Created {OUTPUT_CSV} with {len(doctors)} doctors")


if __name__ == "__main__":
    build_master()

