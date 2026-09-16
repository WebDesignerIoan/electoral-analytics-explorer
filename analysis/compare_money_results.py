import pandas as pd

from inspect_election_results import get_senate_results
from inspect_fec_api import get_candidate_finance

ELECTION_YEAR = 2022


def build_race_summary(state):
    """
    Build one race-level observation for a 2022 Senate election.
    """

    # ---------------------------------------------------------
    # ELECTION RESULT DATA
    # ---------------------------------------------------------

    results_df = get_senate_results(state)

    # Keep the Democratic and Republican candidates for the
    # major-party money-versus-vote comparison.
    major_party_results = results_df[results_df["party"].isin(["D", "R"])].copy()

    # Our current analysis assumes exactly one Democratic and
    # one Republican general-election candidate in each race.
    democratic_count = (major_party_results["party"] == "D").sum()
    republican_count = (major_party_results["party"] == "R").sum()

    if democratic_count != 1 or republican_count != 1:
        raise RuntimeError(
            f"Expected exactly one Democratic and one Republican "
            f"candidate in {state}, but found "
            f"{democratic_count} D and {republican_count} R."
        )

    # ---------------------------------------------------------
    # CAMPAIGN FINANCE DATA
    # ---------------------------------------------------------

    # Use the FEC candidate IDs already present in the election
    # results rather than searching for candidates by name.
    finance_records = [
        get_candidate_finance(candidate_id, ELECTION_YEAR)
        for candidate_id in major_party_results["fec_candidate_id"]
    ]

    finance_df = pd.DataFrame(finance_records)

    # ---------------------------------------------------------
    # MERGE MONEY + RESULT DATA
    # ---------------------------------------------------------

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
    )

    # ---------------------------------------------------------
    # DERIVED CANDIDATE-LEVEL VARIABLES
    # ---------------------------------------------------------

    # Share of the two major candidates' combined spending.
    comparison_df["spending_share"] = (
        comparison_df["total_disbursements"]
        / comparison_df["total_disbursements"].sum()
    )

    # Share of votes received by the two major-party candidates only.
    comparison_df["two_party_vote_share"] = (
        comparison_df["votes"] / comparison_df["votes"].sum()
    )

    # Filter to each major-party candidate.
    #
    # .iloc[0] selects the first row from each filtered DataFrame.
    # The validation above ensures we expect exactly one candidate
    # from each party.
    democrat = comparison_df[comparison_df["party_code"] == "D"].iloc[0]

    republican = comparison_df[comparison_df["party_code"] == "R"].iloc[0]

    # Find the actual election winner from the complete result data,
    # rather than assuming that the winner must be D or R.
    winners = results_df[results_df["won"]]

    if len(winners) != 1:
        raise RuntimeError(
            f"Expected exactly one winner in {state}, " f"but found {len(winners)}."
        )

    winner = winners.iloc[0]

    # ---------------------------------------------------------
    # CREATE ONE RACE-LEVEL OBSERVATION
    # ---------------------------------------------------------

    race_summary = {
        "year": ELECTION_YEAR,
        "state": state,
        "dem_spending": democrat["total_disbursements"],
        "rep_spending": republican["total_disbursements"],
        "total_spending": (
            democrat["total_disbursements"] + republican["total_disbursements"]
        ),
        "dem_spending_share": democrat["spending_share"],
        # Democratic share - Republican share.
        #
        # Positive -> Democratic spending advantage
        # Negative -> Republican spending advantage
        "spending_margin": (democrat["spending_share"] - republican["spending_share"]),
        "dem_two_party_vote_share": democrat["two_party_vote_share"],
        # Democratic share - Republican share.
        #
        # Positive -> Democratic vote advantage
        # Negative -> Republican vote advantage
        "vote_margin": (
            democrat["two_party_vote_share"] - republican["two_party_vote_share"]
        ),
        "winner_party": winner["party"],
    }

    return race_summary


if __name__ == "__main__":
    states = ["PA", "AZ", "NV", "WI", "OH"]

    race_records = [build_race_summary(state) for state in states]

    races_df = pd.DataFrame(race_records)

    print("\n2022 Senate race-level observations:")
    print(races_df.to_string(index=False))


# load election results
#        ↓
# identify D/R candidates
#        ↓
# retrieve finance data
#        ↓
# merge
#        ↓
# calculate spending/vote shares
#        ↓
# convert candidates into one race
