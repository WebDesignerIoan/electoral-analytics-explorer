import pandas as pd

from inspect_election_results import get_senate_results
from inspect_fec_api import get_candidate_record

# ---------------------------------------------------------
# CAMPAIGN FINANCE DATA
# ---------------------------------------------------------

fetterman = get_candidate_record("Fetterman", 2022, "PA")
oz = get_candidate_record("Mehmet Oz", 2022, "PA")

finance_df = pd.DataFrame([fetterman, oz])


# ---------------------------------------------------------
# ELECTION RESULT DATA
# ---------------------------------------------------------

results_df = get_senate_results("PA")

# Keep only the major-party candidates for this comparison.
major_party_results = results_df[results_df["party"].isin(["D", "R"])].copy()


# ---------------------------------------------------------
# MERGE MONEY + RESULT DATA
# ---------------------------------------------------------

# Keep only the election-result fields that add new information.
result_fields = major_party_results[
    [
        "fec_candidate_id",
        "votes",
        "vote_share",
        "won",
        "incumbent",
        "year",
    ]
]

comparison_df = finance_df.merge(
    result_fields,
    on="fec_candidate_id",
    how="inner",
    validate="one_to_one",
)  # one to one checks that each candidate ID should appear exactly once in the finance data and exactly once in the result data

print("\n2022 Pennsylvania Senate — money and results:")
print(comparison_df.to_string(index=False))
