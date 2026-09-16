import os

import httpx
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from the project's .env file
# This lets us use the FEC API key without hard-coding it into the source code
load_dotenv()

api_key = os.getenv("FEC_API_KEY")

# Stop immediately if the API key could not be loaded.
# This gives a clearer error than allowing an API request to fail later
if not api_key:
    raise RuntimeError("FEC_API_KEY was not found in the .env file.")

# Send the API key in an HTTP header rather than in the URL.
# This prevents the key from appearing in request URLs or error messages (has happend and i had to generate another api key)
headers = {
    "X-Api-Key": api_key,
}


def get_candidate_record(search_name, election_year, state):
    """
    Search OpenFEC for one Senate candidate and return a flat dictionary
    containing the candidate information and financial totals we need.
    """

    # ---------------------------------------------------------
    # 1. FIND THE CANDIDATE
    # ---------------------------------------------------------

    candidate_url = "https://api.open.fec.gov/v1/candidates/search/"

    candidate_params = {
        "q": search_name,
        "office": "S",
        "state": state,
        "election_year": election_year,
    }

    candidate_response = httpx.get(
        candidate_url,
        params=candidate_params,
        headers=headers,
        timeout=30,
    )

    if candidate_response.is_error:
        raise RuntimeError(
            f"FEC candidate search failed "
            f"({candidate_response.status_code}): "
            f"{candidate_response.text}"
        )

    candidate_data = candidate_response.json()

    # The search can potentially return more than one person.
    # Since we know the state of the race, we use it to select the relevant candidate from the results
    matching_candidates = [
        candidate
        for candidate in candidate_data["results"]
        if candidate["state"] == state
    ]

    if not matching_candidates:
        raise RuntimeError(
            f"No candidate found for {search_name} in {state}, {election_year}."
        )

    candidate = matching_candidates[0]

    # ---------------------------------------------------------
    # 2. GET FINANCIAL TOTALS
    # ---------------------------------------------------------

    candidate_id = candidate["candidate_id"]

    totals_url = f"https://api.open.fec.gov/v1/candidate/{candidate_id}/totals/"

    totals_params = {
        "cycle": election_year,
        "election_full": False,
    }

    totals_response = httpx.get(
        totals_url,
        params=totals_params,
        headers=headers,
        timeout=30,
    )

    if totals_response.is_error:
        raise RuntimeError(
            f"FEC financial totals request failed "
            f"({totals_response.status_code}): "
            f"{totals_response.text}"
        )

    totals_data = totals_response.json()

    if not totals_data["results"]:
        raise RuntimeError(f"No financial totals found for candidate {candidate_id}.")

    financial_record = totals_data["results"][0]

    # ---------------------------------------------------------
    # 3. CREATE ONE ANALYSIS-READY RECORD
    # ---------------------------------------------------------

    # We combine candidate and finance information into one flat
    # dictionary. Later, this dictionary becomes one row in a DataFrame.
    #
    # OpenFEC -> our internal names:
    # receipts                        -> total_receipts
    # disbursements                   -> total_disbursements
    # last_cash_on_hand_end_period    -> cash_on_hand
    # coverage_end_date               -> coverage_end_date

    # we will return one dictionary with all necessary information for the specified candidate
    return {
        "fec_candidate_id": candidate["candidate_id"],
        "name": candidate["name"],
        "party": candidate["party_full"],
        "state": candidate["state"],
        "total_receipts": financial_record["receipts"],
        "total_disbursements": financial_record["disbursements"],
        "cash_on_hand": financial_record["last_cash_on_hand_end_period"],
        "coverage_end_date": financial_record["coverage_end_date"],
    }


# ---------------------------------------------------------
# TEST THE FUNCTION WITH BOTH MAJOR CANDIDATES IN ONE RACE
# ---------------------------------------------------------

# this is very interesting: if we run the function from this file, we run the pennsylvania race, but if this function is imported in a different file it will not automatically run the Fetterman/Oz test code (python: all top-level executable code (example: get_candidate_record(...)) in a module runs when the module is imported, unless you protect it with the __main__ guard)
if __name__ == "__main__":
    fetterman = get_candidate_record("Fetterman", 2022, "PA")
    oz = get_candidate_record("Mehmet Oz", 2022, "PA")

    candidate_df = pd.DataFrame([fetterman, oz])

    print("\n2022 Pennsylvania Senate candidate finance data:")
    print(candidate_df.to_string(index=False))

# STRUCTURE
# Search for candidate
#        ↓
# Filter candidate by state
#        ↓
# Get candidate ID
#        ↓
# Request candidate financial totals
#        ↓
# Select relevant financial fields
#        ↓
# Return one flat dictionary
#        ↓
# Repeat for each candidate
#        ↓
# Combine records into a pandas DataFrame
