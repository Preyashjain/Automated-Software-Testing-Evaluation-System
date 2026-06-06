# Automated Software Testing & Evaluation System

A hybrid Python–Java pipeline that ingests software test records across six domains, analyzes code snippets via a Java core engine, classifies domains using HuggingFace embeddings and scikit-learn, and visualizes results in a Streamlit dashboard.

## Overview

This system processes structured JSON test records spanning **web**, **api**, **database**, **security**, **performance**, and **mobile** domains. It:

1. Validates and ingests input records
2. Runs Java-based code analysis (complexity, assertions, language detection)
3. Extracts 384-dim sentence embeddings plus numeric metrics
4. Classifies records into domains with 85%+ accuracy
5. Generates reports and displays them in an interactive dashboard

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Input JSON     │────▶│   Java Core      │────▶│  Python Pipeline    │
│  (6 domains)    │     │  Analyzer        │     │  Feature Extraction │
│                 │     │  TestRunner      │     │  (MiniLM-L6-v2)     │
│                 │     │  ResultFormatter │     │                     │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                            │
                         ┌──────────────────┐     ┌─────────▼──────────┐
                         │  Streamlit       │◀────│  Scikit-learn      │
                         │  Dashboard       │     │  Classifier        │
                         └──────────────────┘     └────────────────────┘
```

## Prerequisites

- **Python** 3.11+
- **Java** 11+
- **Maven** 3.6+

## Setup

### 1. Build the Java JAR

```bash
cd java_core && mvn package
```

This produces `java_core/target/testpipeline.jar`.

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Download spaCy model

```bash
python -m spacy download en_core_web_sm
```

### 4. Configure environment

```bash
cp .env.example .env
```

### 5. Train the classifier

```bash
python scripts/train_classifier.py
```

Expected output includes per-fold accuracy and a final line like:

```
Mean accuracy: 0.95 across 6 domains
```

### 6. Run the dashboard

```bash
streamlit run app/dashboard/streamlit_app.py
```

Upload a JSON file from `data/sample_inputs/` and click **Run Pipeline**.

## Running Tests

```bash
pytest tests/
```

## Project Structure

```
automated-testing-system/
├── java_core/              # Java analysis engine
├── app/
│   ├── pipeline/           # Ingestion, bridge, features, classifier, orchestrator
│   ├── dashboard/          # Streamlit UI
│   └── utils/              # Logging
├── data/sample_inputs/     # 120 sample records (20 per domain)
├── models_store/           # Trained classifier model
├── reports/                # Pipeline job reports
├── scripts/                # Training script
└── tests/                  # pytest test suite
```

## Environment Variables

| Variable            | Default                              | Description                          |
|---------------------|--------------------------------------|--------------------------------------|
| `JAVA_JAR_PATH`     | `java_core/target/testpipeline.jar`  | Path to the Java analysis JAR        |
| `MODELS_STORE_PATH` | `models_store/`                      | Directory for saved ML models        |
| `REPORTS_PATH`      | `reports/`                           | Directory for pipeline job reports   |
| `LOG_LEVEL`         | `INFO`                               | Logging level (DEBUG, INFO, WARNING) |

## Sample Input Format

```json
[
  {
    "id": "uuid-string",
    "domain": "web",
    "code_snippet": "def test_login():\n    assert page.title() == 'Login'",
    "description": "Tests the login page title renders correctly in the browser."
  }
]
```

## License

MIT
