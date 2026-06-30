"""
Darbo paieskos automatizacija - Arbeitsagentur API
100% nemokama, be jokiu API rakto registraciju.

Renka AI/Automation pozicijas:
- Miunchenas
- Augsburgas
- Homeoffice (visoje Vokietijoje)

Rezultatai issaugomi i CSV faila, kuri gali atidaryti Excel/Google Sheets.
"""

import requests
import csv
import urllib3
from datetime import datetime

# API blokuoja TLS tikrinima, todel isjungiame warning pranesimus
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
HEADERS = {
    "X-API-Key": "jobboerse-jobsuche",
    "User-Agent": "Jobsuche/2.9.2 (de.arbeitsagentur.jobboerse; build:1077; iOS 15.1.0) Alamofire/5.4.4",
}

# Raktazodziai, kurie rodo, kad pozicija tau tinkama (be grieztu diplomo reikalavimu)
GOOD_KEYWORDS = [
    "n8n", "automation", "automatisierung", "rpa", "prompt", "no-code",
    "low-code", "zapier", "make.com", "api integration", "workflow",
    "chatbot", "ki-tool", "ki tool", "generative ki", "llm",
]

# Raktazodziai, kurie rodo, kad reikalaujamas formalus issilavinimas
# (galima nustebti, bet vis tiek parodysim - tu nuspresi, ar verta bandyti)
DEGREE_KEYWORDS = [
    "abgeschlossenes studium", "master", "bachelor of science",
    "promotion", "phd", "informatik studium", "diplom",
]

SEARCH_LOCATIONS = [
    {"wo": "München", "umkreis": 30},
    {"wo": "Augsburg", "umkreis": 30},
]

SEARCH_TERMS = [
    "KI Automatisierung",
    "AI Automation",
    "Prozessautomatisierung",
    "RPA",
    "Generative KI",
]


def search_jobs(was, wo=None, umkreis=25, homeoffice_only=False, size=50):
    """Vienas paieskos uzklausimas i Arbeitsagentur API."""
    params = {
        "was": was,
        "size": size,
        "page": 1,
    }
    if wo:
        params["wo"] = wo
        params["umkreis"] = umkreis
    if homeoffice_only:
        params["arbeitszeit"] = "ho"  # ho = Homeoffice

    try:
        resp = requests.get(API_URL, headers=HEADERS, params=params, verify=False, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("stellenangebote", [])
    except Exception as e:
        print(f"  ! Klaida ieskant '{was}' ({wo or 'Homeoffice'}): {e}")
        return []


def classify_job(title, description):
    """Paprastas raktazodziu filtras - be jokio AI/mokamo API."""
    text = f"{title} {description}".lower()

    matched_good = [kw for kw in GOOD_KEYWORDS if kw in text]
    matched_degree = [kw for kw in DEGREE_KEYWORDS if kw in text]

    return {
        "relevantu_raktazodziu": ", ".join(matched_good) if matched_good else "-",
        "reikalauja_studiju": "TAIP" if matched_degree else "Neaisku/Ne",
    }


def main():
    all_jobs = []
    seen_refnr = set()

    print("Renkame skelbimus is Arbeitsagentur API...\n")

    # 1. Paieska pagal miestus
    for loc in SEARCH_LOCATIONS:
        for term in SEARCH_TERMS:
            print(f"-> {term} | {loc['wo']} ({loc['umkreis']}km)")
            jobs = search_jobs(was=term, wo=loc["wo"], umkreis=loc["umkreis"])
            for job in jobs:
                refnr = job.get("refnr")
                if refnr and refnr not in seen_refnr:
                    seen_refnr.add(refnr)
                    job["_paieskos_vieta"] = loc["wo"]
                    all_jobs.append(job)

    # 2. Paieska Homeoffice (visa Vokietija)
    for term in SEARCH_TERMS:
        print(f"-> {term} | Homeoffice (visa Vokietija)")
        jobs = search_jobs(was=term, homeoffice_only=True)
        for job in jobs:
            refnr = job.get("refnr")
            if refnr and refnr not in seen_refnr:
                seen_refnr.add(refnr)
                job["_paieskos_vieta"] = "Homeoffice"
                all_jobs.append(job)

    print(f"\nIs viso rasta unikaliu skelbimu: {len(all_jobs)}\n")

    # Apdorojam ir issaugom
    rows = []
    for job in all_jobs:
        title = job.get("titel", "")
        employer = job.get("arbeitgeber", "")
        location = job.get("arbeitsort", {}).get("ort", "")
        published = job.get("aktuelleVeroeffentlichungsdatum", "")
        description = job.get("beruf", "")  # trumpas aprasymas, jei yra
        refnr = job.get("refnr", "")

        classification = classify_job(title, description)

        rows.append({
            "Pavadinimas": title,
            "Imone": employer,
            "Vieta": location,
            "Paieskos_kategorija": job.get("_paieskos_vieta", ""),
            "Paskelbta": published,
            "Atitinkami_raktazodziai": classification["relevantu_raktazodziu"],
            "Reikalauja_studiju": classification["reikalauja_studiju"],
            "Nuoroda": f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}",
        })

    # Rikiuojam - pirma tie, kur rasta atitinkamu raktazodziu
    rows.sort(key=lambda r: r["Atitinkami_raktazodziai"] == "-")

    filename = f"darbo_skelbimai_{datetime.now().strftime('%Y%m%d')}.csv"
    filepath = f"/mnt/user-data/outputs/{filename}"

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Issaugota: {filepath}")
    print(f"Su atitinkamais raktazodziais: {sum(1 for r in rows if r['Atitinkami_raktazodziai'] != '-')}")


if __name__ == "__main__":
    main()
