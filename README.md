# PROITBRIDGE Attrition Insight

A production-style machine-learning web app: it predicts how likely an employee is to leave,
explains **why** (the top drivers), and uses OpenAI to write a short **retention plan**.

- **Model:** scikit-learn Logistic Regression, trained on 6,000 synthetic employee records (no real people). ROC AUC 0.81 on the test set.
- **API:** FastAPI — single prediction, AI summary, and CSV scoring for a whole team.
- **Front end:** PROITBRIDGE navy and white theme, works on laptop and phone.
- **Deploys to:** Google Cloud Run from source (no Dockerfile). The OpenAI key comes from Secret Manager.
- **Storage (optional):** mount a Cloud Storage bucket at `/mnt/data` and every team upload and its scores are saved there.

## Project structure

```
attrition-insight/
├── main.py                 FastAPI app (Cloud Run starts: uvicorn main:app)
├── app/
│   ├── config.py           settings (paths, OpenAI model, upload limits)
│   ├── features.py         the 11 input features and their labels
│   ├── model.py            loads the model, predicts, explains the drivers
│   ├── ai.py               OpenAI retention summary
│   ├── storage.py          saves team uploads to the mounted bucket (/mnt/data)
│   └── schemas.py          request / response validation
├── ml/
│   ├── generate_data.py    creates data/employees.csv (synthetic)
│   └── train.py            trains the model, writes model/ and the model card
├── data/employees.csv      training data (synthetic)
├── model/                  attrition_model.joblib + model_card.json
├── static/                 web page, logo, fonts, sample_team.csv
├── sample_data/            ready-made team CSVs to upload (see below)
├── tests/test_api.py       API tests (pytest)
├── requirements.txt        exact versions used by Cloud Run
├── requirements-dev.txt    test tools
├── .python-version         3.13 (Cloud Run reads this)
├── .env.example            copy to .env for local runs
├── .gitignore / .gcloudignore
```

## Run on your laptop

Needs Python **3.13** (the easiest way is [uv](https://docs.astral.sh/uv/), which downloads it for you).

```bash
cd attrition-insight
uv venv --python 3.13 .venv
# Windows:  .venv\Scripts\activate        macOS / Linux:  source .venv/bin/activate
uv pip install -r requirements.txt
```

Add your key (optional — without it everything works except the AI retention plan):

```bash
# copy .env.example to .env, then put your own key in .env:
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
```

Start the app and open http://127.0.0.1:8000 :

```bash
uvicorn main:app --reload
```

Run the tests:

```bash
uv pip install -r requirements-dev.txt
pytest -q
```

Retrain the model (only if you change the data or features):

```bash
python ml/generate_data.py
python ml/train.py
```

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | `{"status":"ok","model_version":"1.0","ai_enabled":true}` |
| GET | `/api/model-card` | metrics, features, intended use |
| GET | `/api/samples` | two sample employees |
| POST | `/api/predict` | risk %, band (Low / Medium / High) and top drivers |
| POST | `/api/explain` | AI summary + 3 retention actions (needs `OPENAI_API_KEY`) |
| POST | `/api/predict-batch` | upload a CSV (up to 1,000 rows, 1 MB) and score a team; saved to storage when a bucket is mounted |
| GET | `/api/storage` | `enabled` (bucket mounted or not) and the newest saved files |

Interactive API docs: `/docs`.

## Push to GitHub

1. On GitHub, create a new **public** repository named **`attrition-insight`** — empty, without a README.
2. In the project folder:

```bash
git init
git add .
git commit -m "Attrition Insight: ML + OpenAI app for Cloud Run"
git branch -M main
git remote add origin https://github.com/Madhavan1009/attrition-insight.git
git push -u origin main
```

Git asks you to sign in to GitHub the first time. Never paste a token into a command or a screenshot.
`.env` is in `.gitignore`, so your key is never pushed.

## Deploy to Cloud Run

Follow **GCP_Cloud_Run_FastAPI_Deployment_Handbook.html**. The deploy command is:

```bash
gcloud run deploy attrition-insight \
  --source . \
  --region asia-south1 \
  --no-invoker-iam-check \
  --memory 512Mi \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-build-env-vars GOOGLE_ENTRYPOINT="uvicorn main:app --host 0.0.0.0 --port 8080"
```

## Save team uploads to Cloud Storage (optional)

Cloud Run's own disk is wiped when an instance stops. To keep files, mount a Cloud Storage bucket as a folder:

1. **Cloud Storage → Buckets → Create**: a unique name, location `asia-south1`, keep public access prevented.
2. **Cloud Run → attrition-insight → Edit & deploy new revision → Volumes → Add volume**: type *Cloud Storage bucket*, your bucket, mount path **`/mnt/data`**, Read-only **off**. Deploy.
3. On the bucket, give the Cloud Run service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`) the role **Storage Object User**.

Now each team upload saves two files in the bucket: `team-<date>_<time>_<id>_original.csv` (the upload) and `..._scored.csv` (risk, band, top driver).
The header shows **Storage on**, and the team tab lists the newest saved files. Without a mounted folder (for example on your laptop) the app works as before and saves nothing.
To use another folder, set the environment variable `DATA_DIR`.

## Sample files to upload

| File | What it shows |
|---|---|
| `sample_data/team_sales_12.csv` | A Sales team: 4 High, 2 Medium, 6 Low |
| `sample_data/team_support_10.csv` | A Support team: 3 High, 1 Medium, 6 Low |
| `sample_data/team_engineering_15.csv` | A mostly stable Engineering team |
| `sample_data/company_mixed_50.csv` | 50 employees across all departments |
| `sample_data/team_with_errors_8.csv` | 3 bad rows (overtime "Maybe", age 70, satisfaction 6): the app skips them and says why |
| `sample_data/company_1000_rows.csv` | The maximum allowed size (1,000 rows) |

All sample employees are synthetic.

## Responsible use

The data is synthetic and the model is for teaching and decision support only.
Never use a model score alone to make decisions about a person.
