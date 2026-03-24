# ⚽ FIFA Futsal World Cup 2024 --- Analytics App

An interactive **Streamlit application** for analyzing FIFA Futsal World Cup 2024 data, combining event-level exploration with machine learning to generate **tactical insights** on team attacking behavior.

------------------------------------------------------------------------

## 🌐 Live App

Access the deployed app here:

https://fifa-futsal-wc.onrender.com/

------------------------------------------------------------------------

## 📊 Project Overview

This project focuses on understanding **how teams attack**, using event-level data to analyze:

-   Match timelines and attacking actions\
-   Team and player performance\
-   Tactical patterns across the tournament

It integrates data processing, machine learning, and visualization into a single app.

------------------------------------------------------------------------

## 🧠 Key Features

-   **Match Timeline (Home)**\
    Select a match and explore attacking events (Attempts & Goals)

-   **Statistics**\
    Momentum, cumulative attacks, and top players

-   **Team Profiles (ML)**\
    Teams grouped by attacking style using K-Means clustering

    -   PCA visualization of tactical similarity

-   **Infographic**\
    Exportable academic-style match summary (PDF)

------------------------------------------------------------------------

## 🤖 Machine Learning

The app integrates a **K-Means clustering model** to segment teams based on attacking behavior.

### Features used:
-   Attempts per match\
-   Goals per match\
-   Conversion rate\
-   Mean attack minute\
-   Early/Late attack share\
-   Attack variability

### Output: 
Teams are grouped into interpretable tactical categories, enabling comparison across the tournament.

- High-Intensity Attackers\
- Efficient Finishers\
- Low-Intensity Teams

------------------------------------------------------------------------

## ⚙️ Data Sources

-   FIFA API (matches, events, squads)\
-   Local SQLite DB (`assets/team_colors.db`)

------------------------------------------------------------------------

## 🚀 Run Locally

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run main.py
```

App runs at: http://localhost:8501

------------------------------------------------------------------------

## ⚡ Performance

-   Dataset is static (2024 tournament)\
-   `st.cache_data` is used to avoid repeated API calls\
-   Heavy computations are minimized on entry pages

------------------------------------------------------------------------

## 📚 Methodology

The project follows the **CRISP-DM framework**:

1.  Business Understanding\
2.  Data Understanding\
3.  Data Preparation\
4.  Modeling (K-Means + PCA)\
5.  Evaluation\
6.  Deployment

See: `docs/CRISP_DM.md`

------------------------------------------------------------------------

## ⚠️ Troubleshooting

-   Internet connection required (FIFA API)\
-   Missing images (flags) do not affect functionality\
-   If issues occur, try refreshing or clearing cache

------------------------------------------------------------------------

## 🎯 Final Note

This project demonstrates how event-level sports data can be transformed into meaningful tactical insights through a combination of data engineering, machine learning, and interactive visualization.
