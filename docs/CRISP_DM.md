# CRISP-DM Documentation — FIFA Futsal World Cup Streamlit App

This document explains how the final project follows the **CRISP-DM methodology**
(Cross-Industry Standard Process for Data Mining).

The methodology is included in the project structure for academic review.
It is not part of the end-user Streamlit navigation.

---

## 1. Business Understanding

### Project objective
The project aims to analyze FIFA Futsal World Cup data through an interactive Streamlit application and apply Machine Learning to generate tactical insights.

### Main analytical goals
1. Explore match timelines and attacking events.
2. Visualize team and player attacking performance.
3. Group teams by attacking style using clustering.
4. Create a modular sports analytics app that combines data exploration and ML outputs.

### Files mainly related to this phase
- `README.md`
- `main.py`
- `pages/2_Statistics.py`
- `pages/3_Team_Profiles.py`
- `pages/4_Infographic.py`

---

## 2. Data Understanding

### Main data sources
The application uses the FIFA API as its main source of truth.

The app retrieves:
- Match metadata
- Match timelines/events
- Team squads
- Team flags

### Supporting local data sources
The project also uses a local SQLite database for team colors:
- `assets/team_colors.db`

This means the final project uses at least two data sources:
1. FIFA API
2. SQLite database

### Files mainly related to this phase
- `common/utils.py`
- `controllers/data_controller.py`
- `common/flags.py`
- `common/colors.py`

---

## 3. Data Preparation

### Preparation tasks
The project prepares the raw data for analysis through several steps:

- Filter attacking events only:
  - `Attempt at Goal`
  - `Goal!`
- Convert match minute strings into numeric minute values
- Join team names and player names
- Normalize team-level features
- Build per-match and per-team aggregates
- Prepare tactical profile features for clustering

### Team profile feature engineering
The clustering model uses:
- Attempts per match
- Goals per match
- Conversion rate
- Mean attack minute
- Early attack share
- Late attack share
- Attack variability

### Files mainly related to this phase
- `common/metrics.py`
- `common/team_profiles.py`
- `controllers/data_controller.py`

---

## 4. Modeling

### Model developed for app integration
The app currently integrates one Machine Learning model:
- **K-Means clustering** for team attacking profiles

### Modeling objective
Group teams into tactical categories:
- High-Intensity Attackers
- Efficient Finishers
- Low-Intensity Teams

### Modeling steps
1. Build team-level feature matrix
2. Standardize features with `StandardScaler`
3. Fit `KMeans`
4. Reduce dimensionality with `PCA` for 2D visualization
5. Convert raw cluster IDs into stable human-readable labels

### Files mainly related to this phase
- `common/team_profiles.py`
- `common/ml_labels.py`
- `pages/4_Team_Profiles.py`

### Additional academic model
A separate classification model (goal probability) was developed in notebook form as part of the coursework.
It is not yet deployed in the Streamlit app, but it belongs to the overall CRISP-DM workflow of the project.

---

## 5. Evaluation

### Evaluation logic used in the clustering model
The clustering output is evaluated through:
- Tactical interpretability
- Comparison of average feature values by cluster
- PCA visualization for cluster separation
- Consistency of profile definitions with match behavior

### Main interpretation
The model identifies structural differences in offensive behavior:
- Some teams create many attacks
- Some teams are more efficient
- Some teams have lower attacking intensity

### Limitations
- The number of clusters is predefined
- The model does not use spatial shot data
- The app does not yet deploy the goal classification model
- Team profiles depend on available event-level variables

### Files mainly related to this phase
- `common/team_profiles.py`
- `pages/3_Team_Profiles.py`
- `docs/CRISP_DM.md`

---

## 6. Deployment

### Deployment inside the app
The clustering model is deployed directly inside the Streamlit project.

Deployment outputs include:
- Team Profiles page
- Cluster labels for tactical interpretation
- PCA cluster visualization
- Team → cluster summary table

### Why deployment is app-integrated
The app does not rely on external ML CSV snapshots.
Instead, it rebuilds the tactical profiles directly from the same live data pipeline
used in the rest of the project.

This ensures:
- consistency
- maintainability
- a single source of truth

### Files mainly related to this phase
- `pages/3_Team_Profiles.py`
- `common/team_profiles.py`
- `common/ml_labels.py`

---

## Final note

This project follows CRISP-DM not only as a reporting framework, but also as a structural guide for how the data, analytics, modeling, and deployment layers are organized in the codebase.