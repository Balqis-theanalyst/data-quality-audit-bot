from io import BytesIO

import pandas as pd
import streamlit as st


st.set_page_config(page_title="DataTrust Audit", layout="wide")

st.title("DataTrust Audit")
st.write(
    "Audit uploaded CSV or Excel datasets for missing values, duplicates, invalid dates, "
    "invalid numbers, category issues, and overall data readiness."
)
st.caption("Upload a CSV or Excel file with clear column headers for the best results.")

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

VALID_STATUSES = ["Paid", "Pending", "Failed", "Reversed"]
MAX_AFFECTED_ROWS = 1000


def read_uploaded_file(file):
    file_name = file.name.lower()

    if file_name.endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(file), None
        except Exception as error:
            return None, f"I could not read this Excel file: {error}"

    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

    for encoding in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=encoding), None
        except UnicodeDecodeError:
            continue

    return None, (
        "I could not read this CSV file. Please open it in Excel, choose "
        "'Save As', and save it again as CSV UTF-8."
    )


def clean_column_name(column):
    return str(column).strip().lower().replace(" ", "_")


def is_blank(value):
    return pd.isna(value) or str(value).strip() == ""


def create_cleaned_dataset(
    df,
    text_fill_value="Not Available",
    numeric_fill_strategy="Mean",
    remove_duplicate_rows=True,
):
    cleaned_df = df.copy()
    cleaned_df.columns = [clean_column_name(column) for column in cleaned_df.columns]
    cleaning_steps = []

    duplicate_rows_removed = int(cleaned_df.duplicated().sum())

    text_columns = cleaned_df.select_dtypes(include=["object"]).columns
    for column in text_columns:
        cleaned_df[column] = cleaned_df[column].astype("string").str.strip()
        missing_count = int(cleaned_df[column].map(is_blank).sum())

        if missing_count > 0:
            cleaned_df[column] = cleaned_df[column].mask(
                cleaned_df[column].map(is_blank),
                text_fill_value,
            )
            cleaning_steps.append(
                {
                    "column": column,
                    "cleaning_action": "Filled missing text values",
                    "affected_rows": missing_count,
                    "replacement_value": text_fill_value,
                }
            )

    numeric_columns = cleaned_df.select_dtypes(include=["number"]).columns
    for column in numeric_columns:
        missing_count = int(cleaned_df[column].isna().sum())

        if missing_count > 0:
            if numeric_fill_strategy == "Median":
                replacement_value = cleaned_df[column].median()
            elif numeric_fill_strategy == "Zero":
                replacement_value = 0
            else:
                replacement_value = cleaned_df[column].mean()

            cleaned_df[column] = cleaned_df[column].fillna(replacement_value)
            cleaning_steps.append(
                {
                    "column": column,
                    "cleaning_action": f"Filled missing numeric values with {numeric_fill_strategy.lower()}",
                    "affected_rows": missing_count,
                    "replacement_value": round(replacement_value, 2),
                }
            )

    if remove_duplicate_rows:
        cleaned_df = cleaned_df.drop_duplicates()

    if remove_duplicate_rows and duplicate_rows_removed > 0:
        cleaning_steps.append(
            {
                "column": "all columns",
                "cleaning_action": "Removed duplicate rows",
                "affected_rows": duplicate_rows_removed,
                "replacement_value": "N/A",
            }
        )

    if not cleaning_steps:
        cleaning_steps.append(
            {
                "column": "all columns",
                "cleaning_action": "No cleaning changes were needed",
                "affected_rows": 0,
                "replacement_value": "N/A",
            }
        )

    cleaning_summary = pd.DataFrame(cleaning_steps)
    return cleaned_df, cleaning_summary


def run_audit(
    df,
    date_column=None,
    amount_column=None,
    unique_column=None,
    status_column=None,
    valid_statuses=None,
):
    df = df.copy()
    df.columns = [clean_column_name(column) for column in df.columns]
    column_map = {clean_column_name(column): clean_column_name(column) for column in df.columns}

    date_column = column_map.get(clean_column_name(date_column)) if date_column else None
    amount_column = column_map.get(clean_column_name(amount_column)) if amount_column else None
    unique_column = column_map.get(clean_column_name(unique_column)) if unique_column else None
    status_column = column_map.get(clean_column_name(status_column)) if status_column else None
    valid_statuses = valid_statuses or []

    audit_results = []
    affected_rows = []

    def add_affected_row(row_number, issue_type, column, current_value, recommendation):
        if len(affected_rows) < MAX_AFFECTED_ROWS:
            affected_rows.append(
                {
                    "row_number": row_number,
                    "issue_type": issue_type,
                    "column": column,
                    "current_value": current_value,
                    "recommendation": recommendation,
                }
            )

    missing_counts = df.apply(lambda column: column.map(is_blank).sum())
    for column, issue_count in missing_counts.items():
        if issue_count > 0:
            audit_results.append(
                {
                    "check": f"Missing values in {column}",
                    "issue_count": int(issue_count),
                    "severity": "High",
                    "recommendation": f"Fill or review missing values in {column}",
                }
            )

            missing_indexes = df.index[df[column].map(is_blank)]
            for index in missing_indexes:
                add_affected_row(
                    index + 2,
                    f"Missing value in {column}",
                    column,
                    "blank",
                    f"Fill or review missing values in {column}",
                )

    duplicate_rows = df[df.duplicated(keep=False)]
    if len(duplicate_rows) > 0:
        audit_results.append(
            {
                "check": "Duplicate rows",
                "issue_count": int(df.duplicated().sum()),
                "severity": "High",
                "recommendation": "Review duplicate rows before analysis or reporting",
            }
        )

        for index, row in duplicate_rows.iterrows():
            add_affected_row(
                index + 2,
                "Duplicate row",
                "all columns",
                "duplicate record",
                "Review duplicate rows before analysis or reporting",
            )

    if unique_column:
        duplicate_values = df[df[unique_column].duplicated(keep=False) & ~df[unique_column].map(is_blank)]
        if len(duplicate_values) > 0:
            audit_results.append(
                {
                    "check": f"Duplicate values in {unique_column}",
                    "issue_count": int(df[unique_column].duplicated().sum()),
                    "severity": "High",
                    "recommendation": f"Review duplicate values in {unique_column}",
                }
            )

            for index, row in duplicate_values.iterrows():
                add_affected_row(
                    index + 2,
                    f"Duplicate value in {unique_column}",
                    unique_column,
                    row[unique_column],
                    f"Review duplicate values in {unique_column}",
                )

    if amount_column:
        numeric_amount = pd.to_numeric(df[amount_column], errors="coerce")
        invalid_amounts = df[numeric_amount.isna() & ~df[amount_column].map(is_blank)]
        negative_amounts = df[numeric_amount < 0]
        zero_amounts = df[numeric_amount == 0]

        amount_checks = [
            {
                "name": f"Invalid numeric values in {amount_column}",
                "rows": invalid_amounts,
                "severity": "High",
                "recommendation": f"Convert {amount_column} to valid numbers",
            },
            {
                "name": f"Negative values in {amount_column}",
                "rows": negative_amounts,
                "severity": "High",
                "recommendation": f"Review negative values in {amount_column}",
            },
            {
                "name": f"Zero values in {amount_column}",
                "rows": zero_amounts,
                "severity": "Medium",
                "recommendation": f"Confirm whether zero values in {amount_column} are valid",
            }
        ]

        for check in amount_checks:
            if len(check["rows"]) > 0:
                audit_results.append(
                    {
                        "check": check["name"],
                        "issue_count": len(check["rows"]),
                        "severity": check["severity"],
                        "recommendation": check["recommendation"],
                    }
                )

                for index, row in check["rows"].iterrows():
                    add_affected_row(
                        index + 2,
                        check["name"],
                        amount_column,
                        row[amount_column],
                        check["recommendation"],
                    )

    if date_column:
        parsed_dates = pd.to_datetime(df[date_column], errors="coerce")
        invalid_dates = df[parsed_dates.isna() & ~df[date_column].map(is_blank)]
        if len(invalid_dates) > 0:
            audit_results.append(
                {
                    "check": f"Invalid dates in {date_column}",
                    "issue_count": len(invalid_dates),
                    "severity": "High",
                    "recommendation": f"Correct invalid date values in {date_column}",
                }
            )

            for index, row in invalid_dates.iterrows():
                add_affected_row(
                    index + 2,
                    f"Invalid date in {date_column}",
                    date_column,
                    row[date_column],
                    f"Correct invalid date values in {date_column}",
                )

    if status_column and valid_statuses:
        valid_statuses_lower = [status.strip().lower() for status in valid_statuses]
        status_values = df[status_column].astype(str).str.strip().str.lower()
        invalid_status = df[
            ~status_values.isin(valid_statuses_lower) & ~df[status_column].map(is_blank)
        ]
        if len(invalid_status) > 0:
            audit_results.append(
                {
                    "check": f"Invalid status values in {status_column}",
                    "issue_count": len(invalid_status),
                    "severity": "Medium",
                    "recommendation": f"Update status to one of: {', '.join(valid_statuses)}",
                }
            )

            for index, row in invalid_status.iterrows():
                add_affected_row(
                    index + 2,
                    f"Invalid status value in {status_column}",
                    status_column,
                    row[status_column],
                    f"Update status to one of: {', '.join(valid_statuses)}",
                )

    if not audit_results:
        audit_results.append(
            {
                "check": "No issues found",
                "issue_count": 0,
                "severity": "None",
                "recommendation": "No immediate data quality action required",
            }
        )

    audit_report = pd.DataFrame(audit_results)
    affected_rows_report = pd.DataFrame(affected_rows)

    total_issues = audit_report["issue_count"].sum()
    total_checks = max(1, len(df) * len(audit_report))
    quality_score = max(0, 100 - ((total_issues / total_checks) * 100))

    return audit_report, affected_rows_report, round(quality_score, 2)


def create_excel_file(
    audit_report,
    affected_rows_report,
    quality_score,
    recommendation_title,
    recommendation_message,
    readiness_report,
    use_case_report,
    column_health_report,
):
    output = BytesIO()
    recommendation_report = pd.DataFrame(
        [
            {
                "data_quality_score": f"{quality_score}%",
                "recommendation_level": recommendation_title,
                "recommendation": recommendation_message,
            }
        ]
    )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        recommendation_report.to_excel(
            writer, sheet_name="Overall Recommendation", index=False
        )
        readiness_report.to_excel(writer, sheet_name="AI Data Readiness", index=False)
        use_case_report.to_excel(writer, sheet_name="Use Case Readiness", index=False)
        column_health_report.to_excel(writer, sheet_name="Column Health", index=False)
        audit_report.to_excel(writer, sheet_name="Audit Summary", index=False)
        affected_rows_report.to_excel(writer, sheet_name="Affected Rows", index=False)

    output.seek(0)
    return output


def create_cleaned_excel_file(cleaned_df, cleaning_summary):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        cleaning_summary.to_excel(writer, sheet_name="Cleaning Summary", index=False)
        cleaned_df.to_excel(writer, sheet_name="Cleaned Dataset", index=False)

    output.seek(0)
    return output


def get_overall_recommendation(quality_score):
    if quality_score >= 95:
        return (
            "Excellent data quality",
            "This dataset looks reliable for analysis and reporting. Do a quick business review, then proceed.",
        )
    if quality_score >= 85:
        return (
            "Good data quality",
            "This dataset is usable, but fix the highlighted issues before final reporting or decision-making.",
        )
    if quality_score >= 70:
        return (
            "Moderate data quality",
            "Use this dataset with caution. Review affected rows, correct high-severity issues, and rerun the audit.",
        )
    return (
        "Poor data quality",
        "This dataset is not ready for reliable analysis. Clean the major issues first, then audit it again.",
    )


def get_next_action(audit_report):
    high_issues = audit_report[audit_report["severity"] == "High"]["issue_count"].sum()
    medium_issues = audit_report[audit_report["severity"] == "Medium"]["issue_count"].sum()

    if high_issues > 0:
        return "Fix high-severity issues first, then rerun the audit before using this dataset."
    if medium_issues > 0:
        return "Review medium-severity issues before final reporting or dashboarding."
    return "Dataset is in good shape. Do a final business review before using it."


def get_ai_readiness_report(df, audit_report):
    rows = max(1, len(df))
    total_cells = max(1, rows * max(1, len(df.columns)))
    missing_rate = df.apply(lambda column: column.map(is_blank).sum()).sum() / total_cells
    duplicate_rate = df.duplicated().sum() / rows
    high_issue_count = audit_report[audit_report["severity"] == "High"]["issue_count"].sum()
    medium_issue_count = audit_report[audit_report["severity"] == "Medium"]["issue_count"].sum()
    messy_headers = sum(1 for column in df.columns if column != clean_column_name(column))
    messy_header_rate = messy_headers / max(1, len(df.columns))

    score = 100
    score -= min(40, missing_rate * 100)
    score -= min(25, duplicate_rate * 100)
    score -= min(20, (high_issue_count / rows) * 20)
    score -= min(10, (medium_issue_count / rows) * 10)
    score -= min(5, messy_header_rate * 10)
    score = round(max(0, score), 2)

    if score >= 90:
        level = "AI-ready with light review"
        recommendation = "This dataset is broadly ready for analysis or AI workflows after a business-context review."
    elif score >= 75:
        level = "Nearly ready"
        recommendation = "Clean the highlighted issues before using this dataset for AI, modeling, or automated decisions."
    elif score >= 60:
        level = "Needs preparation"
        recommendation = "The dataset needs cleaning and validation before serious analysis or AI use."
    else:
        level = "Not AI-ready"
        recommendation = "Do not use this dataset for AI workflows yet. Resolve major data quality issues first."

    return pd.DataFrame(
        [
            {
                "ai_data_readiness_score": f"{score}%",
                "readiness_level": level,
                "recommendation": recommendation,
            }
        ]
    )


def get_use_case_readiness_report(quality_score, unique_column=None, date_column=None, amount_column=None):
    reporting = "Ready" if quality_score >= 85 else "Needs cleanup"
    dashboarding = "Ready" if quality_score >= 85 else "Review before dashboarding"
    reconciliation = (
        "Ready to test"
        if unique_column and amount_column
        else "Needs ID/reference and amount columns"
    )
    ai_workflow = "Ready with review" if quality_score >= 90 else "Needs preparation"

    return pd.DataFrame(
        [
            {
                "use_case": "Reporting",
                "readiness": reporting,
                "note": "Best when missing values and duplicate rows are resolved.",
            },
            {
                "use_case": "Dashboarding",
                "readiness": dashboarding,
                "note": "Best when categories, dates, and numeric fields are consistent.",
            },
            {
                "use_case": "Reconciliation",
                "readiness": reconciliation,
                "note": "Needs reliable reference/ID and amount columns for matching.",
            },
            {
                "use_case": "AI/ML Workflow",
                "readiness": ai_workflow,
                "note": "Needs clean structure, low missingness, and validated labels/categories.",
            },
        ]
    )


def get_column_health_report(df):
    rows = max(1, len(df))
    health_rows = []

    for column in df.columns:
        missing_count = int(df[column].map(is_blank).sum())
        duplicate_count = int(df[column].duplicated().sum())
        unique_count = int(df[column].nunique(dropna=True))
        missing_rate = round((missing_count / rows) * 100, 2)

        if missing_rate == 0:
            note = "Healthy"
        elif missing_rate <= 10:
            note = "Minor missing values"
        elif missing_rate <= 30:
            note = "Needs review"
        else:
            note = "High missingness"

        health_rows.append(
            {
                "column": column,
                "data_type": str(df[column].dtype),
                "missing_count": missing_count,
                "missing_rate": f"{missing_rate}%",
                "unique_values": unique_count,
                "duplicate_values": duplicate_count,
                "readiness_note": note,
            }
        )

    return pd.DataFrame(health_rows)


def get_dataset_summary(df):
    return {
        "Rows": len(df),
        "Columns": len(df.columns),
        "Total missing values": int(df.isna().sum().sum()),
        "Duplicate rows": int(df.duplicated().sum()),
    }


def get_severity_summary(audit_report):
    severity_counts = audit_report["severity"].value_counts().to_dict()
    return {
        "High severity": severity_counts.get("High", 0),
        "Medium severity": severity_counts.get("Medium", 0),
        "Low severity": severity_counts.get("Low", 0),
    }


def get_download_file_name(uploaded_file_name):
    clean_name = uploaded_file_name.rsplit(".", 1)[0].replace(" ", "_").lower()
    return f"{clean_name}_data_quality_audit_report.xlsx"


def get_cleaned_download_file_name(uploaded_file_name):
    clean_name = uploaded_file_name.rsplit(".", 1)[0].replace(" ", "_").lower()
    return f"{clean_name}_cleaned_dataset.xlsx"


if uploaded_file is not None:
    df, read_error = read_uploaded_file(uploaded_file)

    if read_error:
        st.error(read_error)
        st.stop()

    st.subheader("Dataset Summary")
    summary = get_dataset_summary(df)
    first, second, third, fourth = st.columns(4)
    first.metric("Rows", summary["Rows"])
    second.metric("Columns", summary["Columns"])
    third.metric("Missing Values", summary["Total missing values"])
    fourth.metric("Duplicate Rows", summary["Duplicate rows"])

    st.subheader("Dataset Preview")
    st.dataframe(df.head())

    if len(df) > 5000 or len(df.columns) > 50:
        st.warning(
            "Large dataset detected. The audit summary will still count issues, "
            f"but affected row details are limited to the first {MAX_AFFECTED_ROWS:,} "
            "findings to keep the app responsive."
        )

    columns = list(df.columns)
    column_options = ["None"] + columns

    st.subheader("Optional Smart Checks")
    st.write("Choose columns from the uploaded dataset for deeper checks.")
    st.caption("Detected columns: " + ", ".join(columns))

    left, right = st.columns(2)
    with left:
        date_column = st.selectbox("Date column", column_options, index=0)
        unique_column = st.selectbox(
            "ID/reference column for duplicate checks",
            column_options,
            index=0,
        )
    with right:
        amount_column = st.selectbox("Amount/number column", column_options, index=0)
        status_column = st.selectbox("Status/category column", column_options, index=0)

    date_column = None if date_column == "None" else date_column
    amount_column = None if amount_column == "None" else amount_column
    unique_column = None if unique_column == "None" else unique_column
    status_column = None if status_column == "None" else status_column

    valid_statuses = []
    if status_column:
        status_values = (
            df[status_column]
            .dropna()
            .astype(str)
            .str.strip()
        )
        status_values = sorted(value for value in status_values.unique() if value)
        accepted_statuses = st.multiselect(
            "Accepted values for the selected status/category column",
            options=status_values,
            default=status_values,
        )
        valid_statuses = accepted_statuses
        st.caption(
            "Remove any value that should be treated as invalid, then run the audit."
        )

    st.subheader("Cleaning Options")
    clean_left, clean_middle, clean_right = st.columns(3)
    with clean_left:
        text_fill_value = st.text_input("Fill missing text values with", "Not Available")
    with clean_middle:
        numeric_fill_strategy = st.selectbox(
            "Fill missing numeric values with",
            ["Mean", "Median", "Zero"],
            index=0,
        )
    with clean_right:
        remove_duplicate_rows = st.checkbox("Remove duplicate rows", value=True)

    if st.button("Run Audit"):
        audit_report, affected_rows_report, quality_score = run_audit(
            df,
            date_column=date_column,
            amount_column=amount_column,
            unique_column=unique_column,
            status_column=status_column,
            valid_statuses=valid_statuses,
        )

        st.subheader("Data Quality Score")
        st.metric("Score", f"{quality_score}%")

        recommendation_title, recommendation_message = get_overall_recommendation(
            quality_score
        )
        st.subheader("Overall Recommendation")
        st.info(f"**{recommendation_title}:** {recommendation_message}")
        st.info(f"**Recommended Next Action:** {get_next_action(audit_report)}")

        readiness_report = get_ai_readiness_report(df, audit_report)
        use_case_report = get_use_case_readiness_report(
            quality_score,
            unique_column=unique_column,
            date_column=date_column,
            amount_column=amount_column,
        )
        column_health_report = get_column_health_report(df)

        st.subheader("AI/Data Readiness")
        st.dataframe(readiness_report)

        st.subheader("Use Case Readiness")
        st.dataframe(use_case_report)

        st.subheader("Audit Summary")
        st.dataframe(audit_report)

        chart_data = audit_report[audit_report["issue_count"] > 0]
        if not chart_data.empty:
            st.subheader("Issue Charts")
            chart_left, chart_right = st.columns(2)
            with chart_left:
                st.write("Issues by Check")
                st.bar_chart(chart_data.set_index("check")["issue_count"])
            with chart_right:
                st.write("Issues by Severity")
                severity_chart = (
                    chart_data.groupby("severity", as_index=False)["issue_count"]
                    .sum()
                    .set_index("severity")
                )
                st.bar_chart(severity_chart)

        st.subheader("Severity Summary")
        severity_summary = get_severity_summary(audit_report)
        high, medium, low = st.columns(3)
        high.metric("High", severity_summary["High severity"])
        medium.metric("Medium", severity_summary["Medium severity"])
        low.metric("Low", severity_summary["Low severity"])

        st.subheader("Column Health")
        st.dataframe(column_health_report)

        st.subheader("Affected Rows")
        if affected_rows_report.empty:
            st.success("No affected rows found.")
        else:
            if len(affected_rows_report) >= MAX_AFFECTED_ROWS:
                st.warning(
                    f"Showing the first {MAX_AFFECTED_ROWS:,} affected rows only. "
                    "Use the audit summary for the full issue counts."
                )
            st.dataframe(affected_rows_report)

        excel_file = create_excel_file(
            audit_report,
            affected_rows_report,
            quality_score,
            recommendation_title,
            recommendation_message,
            readiness_report,
            use_case_report,
            column_health_report,
        )

        st.download_button(
            label="Download Excel Audit Report",
            data=excel_file,
            file_name=get_download_file_name(uploaded_file.name),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        cleaned_df, cleaning_summary = create_cleaned_dataset(
            df,
            text_fill_value=text_fill_value,
            numeric_fill_strategy=numeric_fill_strategy,
            remove_duplicate_rows=remove_duplicate_rows,
        )
        cleaned_excel_file = create_cleaned_excel_file(cleaned_df, cleaning_summary)
        st.subheader("Cleaned Dataset Summary")
        st.dataframe(cleaning_summary)
        st.download_button(
            label="Download Cleaned Dataset",
            data=cleaned_excel_file,
            file_name=get_cleaned_download_file_name(uploaded_file.name),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

st.divider()
st.caption("Built by Balqis Shittu with Python, Pandas, and Streamlit.")
