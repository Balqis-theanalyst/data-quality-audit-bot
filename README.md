# DataTrust Audit

A Streamlit app that audits uploaded CSV datasets for common data quality issues and generates a downloadable Excel report.

## Problem

Business teams often use datasets that contain missing values, duplicates, invalid dates, invalid numbers, or inconsistent categories. These issues can affect reporting, reconciliation, and decision-making.

## Solution

This app allows users to upload a CSV file, review a dataset summary, run data quality checks, view affected rows, receive an overall recommendation, and download an Excel audit report.

DataTrust Audit helps users quickly understand whether a dataset is ready for analysis, reporting, reconciliation, or decision-making.

## Features

- Upload any CSV dataset
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
- Download a multi-sheet Excel audit report

## Tools Used

- Python
- Pandas
- Streamlit
- OpenPyXL
- Excel

## How To Run Locally

Install the required packages:

```bash
pip install pandas streamlit openpyxl
```

Run the app:

```bash
streamlit run app.py
```

## Sample Dataset

The project includes `sample_transactions.csv` for testing. You can also upload your own CSV file.

## Excel Report Sheets

The downloaded report contains:

- Overall Recommendation
- Audit Summary
- Affected Rows

## Future Improvements

- Add Excel file upload support
- Add automatic column suggestions
- Add visual charts for data quality issues
- Add cleaned dataset download
- Add multi-source reconciliation checks

## Author

Built by Balqis Shittu as part of a practical data analytics and data quality portfolio project.
