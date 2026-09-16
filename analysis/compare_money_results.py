import pandas as pd

from inspect_election_results import get_senate_results
from inspect_fec_api import get_candidate_finance

ELECTION_YEAR = 2022
STATE = "PA"


# ---------------------------------------------------------
# ELECTION RESULT DATA
# ---------------------------------------------------------

results_df = get_senate_results(STATE)

# Keep only the Democratic and Republican candidates
# for the major-party comparison.
major_party_results = results_df[results_df["party"].isin(["D", "R"])].copy()


# ---------------------------------------------------------
# CAMPAIGN FINANCE DATA
# ---------------------------------------------------------

# The election-results dataset already contains the FEC candidate IDs,
# so we can use those IDs directly instead of searching by candidate name.
finance_records = [
    get_candidate_finance(candidate_id, ELECTION_YEAR)
    for candidate_id in major_party_results["fec_candidate_id"]
]

# Each returned dictionary becomes one row in the DataFrame.
finance_df = pd.DataFrame(finance_records)


# ---------------------------------------------------------
# MERGE MONEY + RESULT DATA
# ---------------------------------------------------------

# Keep the candidate identity and election-result fields that we need.
result_fields = major_party_results[
    [
        "fec_candidate_id",
        "name",
        "party",
        "state",
        "votes",
        "vote_share",
        "won",
        "incumbent",
        "year",
    ]
].rename(
    columns={
        "party": "party_code",
    }
)

comparison_df = result_fields.merge(
    finance_df,
    on="fec_candidate_id",
    how="inner",
    validate="one_to_one",
)  # Ensure each candidate appears exactly once in both datasets.


# ---------------------------------------------------------
# DERIVED ANALYTICAL VARIABLES
# ---------------------------------------------------------

# Share of the two major candidates' combined spending.
comparison_df["spending_share"] = (
    comparison_df["total_disbursements"] / comparison_df["total_disbursements"].sum()
)

# Share of the votes received by the two major-party candidates only.
# We keep the official vote_share separately because it includes
# votes cast for minor-party candidates in its denominator.
comparison_df["two_party_vote_share"] = (
    comparison_df["votes"] / comparison_df["votes"].sum()
)


# ---------------------------------------------------------
# CREATE ONE RACE-LEVEL OBSERVATION
# ---------------------------------------------------------

# First filter the DataFrame to the Democratic candidate.
# The result is still a DataFrame, even if it contains only one row.
#
# .iloc[0] then selects the row at position 0 — the first row
# in that filtered DataFrame.
democrat = comparison_df[comparison_df["party_code"] == "D"].iloc[0]

# Do the same for the Republican candidate:
# filter to party_code == "R", then take the first matching row.
republican = comparison_df[comparison_df["party_code"] == "R"].iloc[0]

# Find the actual winner from the complete election-results dataset.
winner = results_df[results_df["won"]].iloc[0]


race_summary = {
    "year": democrat["year"],
    "state": democrat["state"],
    # Store each major-party candidate's total campaign spending.
    "dem_spending": democrat["total_disbursements"],
    "rep_spending": republican["total_disbursements"],
    # Combined spending by the two major-party candidates.
    "total_spending": (
        democrat["total_disbursements"] + republican["total_disbursements"]
    ),
    # Democratic candidate's share of major-party spending.
    "dem_spending_share": democrat["spending_share"],
    # Define spending margin consistently as:
    # Democratic spending share - Republican spending share.
    #
    # Positive value -> Democratic spending advantage
    # Negative value -> Republican spending advantage
    "spending_margin": (democrat["spending_share"] - republican["spending_share"]),
    # Democratic share of the two-party vote.
    "dem_two_party_vote_share": democrat["two_party_vote_share"],
    # Define vote margin in the same direction:
    # Democratic two-party vote share - Republican two-party vote share.
    #
    # Positive value -> Democratic vote advantage
    # Negative value -> Republican vote advantage
    "vote_margin": (
        democrat["two_party_vote_share"] - republican["two_party_vote_share"]
    ),
    # Record the actual winner's party from the complete result dataset.
    "winner_party": winner["party"],
}


# A dictionary represents one race.
# Wrapping it in a list lets pandas interpret it as one DataFrame row.
race_df = pd.DataFrame([race_summary])


# ---------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------

print("\nRace-level observation:")
print(race_df.to_string(index=False))

# Select the fields needed for a concise candidate-level output.
columns_to_show = [
    "fec_candidate_id",
    "name",
    "party_code",
    "total_disbursements",
    "spending_share",
    "votes",
    "vote_share",
    "two_party_vote_share",
    "won",
]

print("\n2022 Pennsylvania Senate — money and results:")
print(comparison_df[columns_to_show].to_string(index=False))
