# fifa_futsal
FIFA Futsal 2024 world cup project

## Run instructions

Quick steps to run the Streamlit app locally (Windows PowerShell):

1. Create and activate a Python environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app with Streamlit:

```powershell
streamlit run main.py
```

4. The app will open in your browser at `http://localhost:8501` by default.

## Troubleshooting

- If `streamlit` is not found after installing, make sure your virtualenv is activated and use the full path to the `streamlit` executable inside `.venv\Scripts`.
- If imports fail (ModuleNotFoundError) for `numpy`, `matplotlib`, or `PIL`/`Pillow`, re-run the `pip install -r requirements.txt` command and check for errors during installation.
- If the app fails to fetch data from the FIFA endpoints, ensure you have an internet connection and that the API base URL in `common/constants.py` is correct. The app uses cached helpers (`st.cache_data`) so a transient network error may be recoverable by reloading the page.
- For cookie-based login issues, the app uses `extra-streamlit-components`' CookieManager; if cookies are not persisted, try a different browser or clear cookies for `localhost` and retry.
- If images (flags) fail to download, the infographic page will still render; missing flags are ignored by design. Check your network or the remote image server if many flags are missing.
