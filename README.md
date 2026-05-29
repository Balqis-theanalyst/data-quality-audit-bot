# DataTrust Audit

A Streamlit app that audits uploaded CSV and Excel datasets for common data quality issues and generates downloadable Excel reports.

## Problem

Business teams often use datasets that contain missing values, duplicates, invalid dates, invalid numbers, or inconsistent categories. These issues can affect reporting, reconciliation, and decision-making.

## Solution

This app allows users to upload a CSV or Excel file, review a dataset summary, run data quality checks, view affected rows, receive an overall recommendation, view issue charts, and download Excel reports.

DataTrust Audit helps users quickly understand whether a dataset is ready for analysis, reporting, reconciliation, or decision-making.

## Features

- Upload CSV or Excel datasets
- Detect missing values across all columns
- Detect duplicate rows
- Select optional columns for deeper checks
- Check duplicate IDs or references
- Check invalid dates
- Check invalid numeric values
- Check negative and zero values
- Check invalid status or category values
- Generate a data quality score
- Show an overall recommendation
- Show affected rows with recommended actions
- View simple issue charts
- Download a multi-sheet Excel audit report
- Download a cleaned dataset with standardized headers, trimmed text values, and duplicate rows removed

## Tools Used

- Python
- Pandas
- Streamlit
- OpenPyXL
- Excel / OpenPyXL / xlrd

## How To Run Locally

Install the required packages:

```bash
pip install pandas streamlit openpyxl xlrd
```

Run the app:

```bash
streamlit run app.py
```

## Sample Dataset

The project includes `sample_transactions.csv` for testing. You can also upload your own CSV or Excel file.

## Excel Report Sheets

The downloaded report contains:

- Overall Recommendation
- Audit Summary
- Affected Rows

## Future Improvements

- Add automatic column suggestions
- Add multi-source reconciliation checks
- Add stronger cleaning rules users can choose before downloading cleaned data

## Author

Built by Balqis Shittu as part of a practical data analytics and data quality portfolio project.
