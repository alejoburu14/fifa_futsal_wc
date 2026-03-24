# CRISP-DM Methodology Implementation  
## FIFA Futsal 2024 World Cup Analytics App

---

## Overview

This document describes how the CRISP-DM methodology has been applied not only as a reporting framework, but as a guiding structure for the design of the data pipeline, analytical logic, and machine learning components of the application.

The project integrates data ingestion, transformation, modeling, and visualization into a unified Streamlit application, ensuring consistency between analytical outputs and user-facing insights.

---

## CRISP-DM Workflow Mapping

- **Business Understanding →** App objectives and analytical goals  
- **Data Understanding →** API and database integration  
- **Data Preparation →** Feature engineering pipeline  
- **Modeling →** K-Means clustering + PCA  
- **Evaluation →** Interpretability and cluster validation  
- **Deployment →** Streamlit app integration  

---

## 1. Business Understanding

### Project objective
The project aims to analyze FIFA Futsal World Cup data through an interactive Streamlit application and apply Machine Learning techniques to generate tactical insights.

### Main analytical goals
1. Explore match timelines and attacking events  
2. Visualize team and player attacking performance  
3. Group teams by attacking style using clustering  
4. Build a modular sports analytics application combining data exploration and ML outputs  

### Analytical perspective
The project focuses on understanding **how teams attack**, rather than simply measuring outcomes.  
It seeks to identify structural differences in offensive behavior, such as:
- attacking intensity,
- scoring efficiency,
- temporal distribution of attacks.

### Files mainly related to this phase
- `README.md`  
- `main.py`  
- `pages/2_Statistics.py`  
- `pages/3_Team_Profiles.py`  
- `pages/4_Infographic.py`  

---

## 2. Data Understanding

### Main data sources
The application uses the FIFA API as its primary source of data.

The app retrieves:
- Match metadata  
- Match event timelines  
- Team squads  
- Team identifiers  

### Supporting local data sources
A local SQLite database is used for team colors:
- `assets/team_colors.db`

### Data structure characteristics
- Event-level data is semi-structured (text-based descriptions)
- Time is encoded as strings (e.g., `"12'"`, `"40+1"`)
- Team and player mappings must be reconstructed dynamically

### Key data challenges
- Parsing time formats into numerical values  
- Filtering relevant attacking events from general event logs  
- Ensuring consistent team identification across matches  

### Files mainly related to this phase
- `common/utils.py`  
- `controllers/data_controller.py`  
- `common/flags.py`  
- `common/colors.py`  

---

## 3. Data Preparation

### Data pipeline design

The project follows a reproducible pipeline:

1. Data ingestion (API + SQLite)  
2. Event filtering and normalization  
3. Feature engineering at team level  
4. Feature scaling  
5. Clustering model  
6. Dimensionality reduction (PCA)  
7. Visualization layer  

This pipeline ensures consistency between analytical outputs and visual components of the app.

---

### Preparation tasks

- Filter attacking events:
  - `Attempt at Goal`
  - `Goal!`
- Convert match minute strings into numeric values  
- Map team and player identifiers  
- Aggregate event-level data into team-level features  
- Normalize features for modeling  

---

### Team profile feature engineering

The selected features capture three complementary dimensions of attacking behavior:

- **Volume**
  - Attempts per match  

- **Output**
  - Goals per match  

- **Efficiency**
  - Conversion rate  

- **Temporal behavior**
  - Mean attack minute  
  - Early attack share  
  - Late attack share  

- **Variability**
  - Attack variability (dispersion of actions over time)

This combination allows the model to distinguish between teams that:
- generate high attacking volume,
- convert efficiently,
- or show lower attacking intensity.

---

### Reproducibility considerations

- Data transformations are deterministic  
- Feature engineering is centralized in `team_profiles.py`  
- Streamlit caching (`st.cache_data`) ensures stable outputs  
- The model is rebuilt dynamically to avoid stale dependencies  

---

### Files mainly related to this phase
- `common/metrics.py`  
- `common/team_profiles.py`  
- `controllers/data_controller.py`  

---

## 4. Modeling

### Model developed for app integration

The application integrates one Machine Learning model:

- **K-Means clustering** for team attacking profiles  

---

### Modeling objective

Segment teams into tactical categories based on attacking behavior:

- High-Intensity Attackers  
- Efficient Finishers  
- Low-Intensity Teams  

---

### Modeling steps

1. Build team-level feature matrix  
2. Standardize features using `StandardScaler`  
3. Fit K-Means clustering model  
4. Apply PCA for 2D visualization  
5. Map raw cluster IDs to stable, interpretable labels  

---

### Why K-Means was considered appropriate

- The objective is **segmentation (unsupervised learning)**  
- Features are continuous and comparable after scaling  
- The dataset size is moderate and well-suited to centroid-based clustering  
- Interpretability is prioritized over predictive performance  

---

### Alternative approaches considered

- **Hierarchical clustering**
  - Rejected due to complexity and lower interpretability for end users  

- **DBSCAN**
  - Rejected due to sensitivity to density parameters and small dataset size  

---

### Additional academic model

A separate classification model (goal probability) was developed in notebook form as part of the coursework.  
It is not yet deployed in the Streamlit app but forms part of the overall CRISP-DM workflow.

---

### Files mainly related to this phase
- `common/team_profiles.py`  
- `common/ml_labels.py`  
- `pages/3_Team_Profiles.py`  

---

## 5. Evaluation

### Evaluation logic

Given the absence of labeled data, evaluation focuses on:

- **Interpretability of clusters**  
- **Internal coherence of feature distributions**  
- **Separation in PCA visualization space**  
- **Consistency with observed match behavior**  

---

### Validation approach

The model is assessed through:

- Comparison of average feature values across clusters  
- Visual inspection of cluster separation (PCA)  
- Alignment with domain knowledge of futsal tactics  

---

### Main findings

The model identifies structural differences in offensive behavior:

- Some teams generate high attacking volume  
- Some teams achieve higher efficiency with fewer attempts  
- Some teams exhibit consistently lower attacking intensity  

---

### Limitations

- The number of clusters is predefined  
- No spatial data (e.g., shot location) is included  
- The classification model is not yet deployed  
- Results depend on available event-level variables  

---

### Files mainly related to this phase
- `common/team_profiles.py`  
- `pages/3_Team_Profiles.py`  
- `docs/CRISP_DM.md`  

---

## 6. Deployment

### Deployment approach

The clustering model is deployed directly within the Streamlit application.

---

### Deployment outputs

- Team Profiles page  
- Cluster labels for tactical interpretation  
- PCA visualization of team similarity  
- Team-to-cluster summary tables  

---

### Why deployment is app-integrated

The application rebuilds the model dynamically using the same data pipeline as the rest of the app.

This ensures:

- Consistency  
- Maintainability  
- Single source of truth  
- No dependency on static ML outputs  

---

### Deployment environment and performance considerations

The application is deployed as a cloud-based Streamlit service using Render:

https://fifa-futsal-wc.onrender.com/

Given that the dataset corresponds to a completed tournament (FIFA Futsal World Cup 2024), the data is static and does not change over time. This allows for optimization strategies focused on performance and reproducibility rather than real-time data updates.

To improve user experience and ensure efficient deployment:

- Streamlit caching (`st.cache_data`) is used extensively to avoid repeated API calls and recomputation of derived datasets
- Expensive computations (e.g., team profile clustering) are avoided in entry pages to reduce initial load time
- The application prioritizes responsiveness and stability over real-time data ingestion

This deployment approach reflects a trade-off between:

- dynamic data pipelines (not required in this context)
- and efficient delivery of precomputed analytical insights

From a CRISP-DM perspective, this highlights how deployment decisions must adapt to:

- data characteristics (static vs dynamic)
- user interaction patterns
- infrastructure constraints

---

### Files mainly related to this phase
- `pages/3_Team_Profiles.py`  
- `common/team_profiles.py`  
- `common/ml_labels.py`  

---

## Final Note

This project applies CRISP-DM not only as a reporting framework, but as a structural backbone for organizing data workflows, modeling logic, and deployment.

The integration of Machine Learning within an interactive application demonstrates how analytical pipelines can be translated into practical tools for domain-specific insight generation.