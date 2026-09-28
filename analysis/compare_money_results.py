from pathlib import Path

import pandas as pd

from inspect_election_results import (
    get_senate_results,
    get_senate_races,
    aggregate_candidate_results,
)
from inspect_fec_api import (
    get_candidate_finance,
    FinanceDataUnavailableError,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "senate_2022.json"

EXCLUSIONS_FILE = (
    PROJECT_ROOT / "data" / "processed" / "senate_2022_exclusions.json"
)  # for the races that were excluded from various reasons

ELECTION_YEAR = 2022


class AnalysisExclusion(RuntimeError):
    """
    Raised when a valid Senate race does not fit the current
    one-Democratic-versus-one-Republican analytical model.
    """


def build_race_summary(state, district):
    """
    Build one race-level observation for a 2022 Senate election.
    """

    # ---------------------------------------------------------
    # ELECTION RESULT DATA
    # ---------------------------------------------------------

    # Load the raw ballot-line results for this race.
    results_df = get_senate_results(state, district)

    # Combine multiple ballot lines belonging to the same candidate
    # into one candidate-level record.
    results_df = aggregate_candidate_results(results_df)

    # Keep the Democratic and Republican candidates for the
    # major-party money-versus-vote comparison.
    major_party_results = results_df[results_df["major_party"].isin(["D", "R"])].copy()

    # Our current analysis assumes exactly one Democratic and
    # one Republican general-election candidate in each race.
    democratic_count = (major_party_results["major_party"] == "D").sum()
    republican_count = (major_party_results["major_party"] == "R").sum()

    if democratic_count != 1 or republican_count != 1:
        raise AnalysisExclusion(
            f"Expected exactly one Democratic and one Republican "
            f"candidate in {state} ({district}), but found "
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
            "major_party",
            "state",
            "votes",
            "vote_share",
            "won",
            "incumbent",
            "year",
        ]
    ].rename(
        columns={
            "major_party": "party_code",
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
            f"Expected exactly one winner in {state} ({district}), "
            f"but found {len(winners)}."
        )

    winner = winners.iloc[0]

    # ---------------------------------------------------------
    # CREATE ONE RACE-LEVEL OBSERVATION
    # ---------------------------------------------------------

    race_summary = {
        "year": ELECTION_YEAR,
        "state": state,
        "district": district,
        "dem_candidate_id": democrat["fec_candidate_id"],
        "rep_candidate_id": republican["fec_candidate_id"],
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
        "winner_party": winner["major_party"],
    }

    return race_summary


if __name__ == "__main__":
    races = get_senate_races()

    race_records = []
    excluded_races = []
    unavailable_finance_races = []
    failed_races = []

    # We try to build one race summary for each Senate race
    for state, district in races:
        try:
            race = build_race_summary(state, district)

            race_records.append(race)
            print(f"Processed {state} ({district})")

        # The race data are valid, but the contest does not fit
        # the current one-D-versus-one-R analytical definition.
        except AnalysisExclusion as error:
            excluded_races.append((state, district, str(error)))
            print(f"Excluded {state} ({district}): {error}")

        # The race fits the analytical model, but comparable
        # OpenFEC finance totals are unavailable.
        except FinanceDataUnavailableError as error:
            unavailable_finance_races.append((state, district, str(error)))
            print(f"Finance unavailable {state} ({district}): {error}")

        # Keep other expected runtime failures separate so that
        # they are not confused with analytical exclusions or
        # known missing finance data.
        except RuntimeError as error:
            failed_races.append((state, district, str(error)))
            print(f"Failed {state} ({district}): {error}")

    # Convert the successfully processed races into a DataFrame so that
    # we can apply analytical eligibility checks across races.
    processed_df = pd.DataFrame(race_records)

    # Identify cases where the same Democratic and Republican candidates
    # appear in more than one race in the same state and year.
    duplicate_candidate_pair = processed_df.duplicated(
        subset=[
            "year",
            "state",
            "dem_candidate_id",
            "rep_candidate_id",
        ],
        keep=False,
    )

    # When the same candidate pair appears in both a full-term and an
    # unexpired-term election, the candidate-level finance totals cannot
    # be uniquely attributed to the two contests.
    #
    # Keep the full-term election in the analytical dataset and exclude
    # the duplicate unexpired-term observation.
    duplicate_unexpired = duplicate_candidate_pair & processed_df["district"].eq(
        "S-Unexpired Term"
    )

    duplicate_exclusions = processed_df[duplicate_unexpired].copy()

    races_df = processed_df[~duplicate_unexpired].copy()

    for _, race in duplicate_exclusions.iterrows():
        excluded_races.append(
            (
                race["state"],
                race["district"],
                "Same D/R candidate pair also contested the full-term election; "
                "candidate-level finance totals cannot be attributed separately "
                "to the two contests.",
            )
        )

    # Build structured records explaining why races were omitted
    # from the final analytical dataset.
    exclusion_records = []

    for state, district, reason in excluded_races:
        exclusion_records.append(
            {
                "year": ELECTION_YEAR,
                "state": state,
                "district": district,
                "category": "analytical_exclusion",
                "reason": reason,
            }
        )

    for state, district, reason in unavailable_finance_races:
        exclusion_records.append(
            {
                "year": ELECTION_YEAR,
                "state": state,
                "district": district,
                "category": "finance_unavailable",
                "reason": reason,
            }
        )

    for state, district, reason in failed_races:
        exclusion_records.append(
            {
                "year": ELECTION_YEAR,
                "state": state,
                "district": district,
                "category": "processing_failure",
                "reason": reason,
            }
        )

    print("\n2022 Senate race-level observations:")
    print(races_df.to_string(index=False))

    print(
        f"\nSuccessfully built " f"{len(race_records)} of {len(races)} race summaries."
    )

    print(f"Final analytical dataset: " f"{len(races_df)} races.")

    if excluded_races:
        print("\nAnalytically excluded races:")

        for state, district, reason in excluded_races:
            print(f"{state} ({district}): {reason}")

    if unavailable_finance_races:
        print("\nRaces with unavailable finance data:")

        for state, district, reason in unavailable_finance_races:
            print(f"{state} ({district}): {reason}")

    if failed_races:
        print("\nOther processing failures:")

        for state, district, reason in failed_races:
            print(f"{state} ({district}): {reason}")

    # Create a separate copy for export so that rounding does not affect
    # the full-precision values used during the analysis
    export_df = races_df.copy()

    # Currency values only need cents
    currency_columns = [
        "dem_spending",
        "rep_spending",
        "total_spending",
    ]

    export_df[currency_columns] = export_df[currency_columns].round(2)

    # Shares and margins are proportions between -1 and 1
    # Six decimal places are enough for the web visualization
    proportion_columns = [
        "dem_spending_share",
        "spending_margin",
        "dem_two_party_vote_share",
        "vote_margin",
    ]

    export_df[proportion_columns] = export_df[proportion_columns].round(6)

    # Create the processed-data directory if it does not already exist
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save the processed race-level data as a JSON array
    export_df.to_json(
        OUTPUT_FILE,
        orient="records",
        indent=2,
        double_precision=6,
    )

    # Save the races that were omitted from the final analytical dataset,
    # together with the reason for each exclusion.
    exclusions_df = pd.DataFrame(exclusion_records)

    exclusions_df.to_json(
        EXCLUSIONS_FILE,
        orient="records",
        indent=2,
    )

    print(f"\nSaved processed data to: {OUTPUT_FILE}")
    print(f"Saved exclusions to: {EXCLUSIONS_FILE}")


# STRUCTURE
# Load one Senate race
#        >
# Aggregate multiple ballot lines into candidate-level records
#        >
# Classify candidates into D/R analytical groups
#        >
# Validate that the race contains exactly one D and one R candidate
#        >
# Retrieve candidate finance data using FEC candidate IDs
#        >
# Merge election results with finance data
#        >
# Calculate spending shares and two-party vote shares
#        >
# Convert the candidate data into one race-level observation
#        >
# Process all Senate races
#        >
# Apply cross-race analytical exclusions
#        >
# Export the final analytical dataset and exclusion records
