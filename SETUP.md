# 🎓 Diploma Project Setup Guide - Proactive Microclimate Monitoring

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Seed Test Data
```bash
curl -X POST http://127.0.0.1:8000/api/seed_data
```

### 4. Access Swagger UI
Open: http://127.0.0.1:8000/docs

---

## 🎓 4 Diploma Criteria Implementation

### CRITERION 1: Practical Problem-Solving ✅
- **Task:** Proactive microclimate monitoring with intelligent recommendations
- **Implementation:** Detects anomalies and generates executable recommendations with target values
- **Key File:** `intelligent_recommendation_engine.py` (652 lines)
- **API:** `POST /api/recommendations/generate`

### CRITERION 2: 2+ NLP Models ✅
- **Task:** Analyze sensor time series with multiple approaches
- **Classical (3):** Moving Average, Isolation Forest, Seasonal Decomposition
- **Transformer (3):** Time Series with Attention, Trend Analysis, Ensemble
- **Key Files:** 
  - `anomaly_detection_classical.py` (661 lines)
  - `anomaly_detection_transformer.py` (509 lines)
- **API:** `GET /api/sensors/{sensor_id}/anomalies`

### CRITERION 3: Model Comparison ✅
- **Task:** Compare classical vs Transformer methods
- **Metrics:** Models agreement, consensus confidence, score comparison
- **Database:** `AnomalyAnalysis` table stores both method results
- **API:** `GET /api/diploma/analysis-stats`

### CRITERION 4: Speech Recognition ✅
- **Task:** Voice commands for notification management
- **Technology:** OpenAI Whisper
- **Commands:** confirm, reject, modify, request_info, request_report
- **Languages:** Russian + English
- **Key File:** `voice_notification_commands.py` (450+ lines)
- **API:** `POST /api/voice/notification-command`

---

## ENVIRONMENT SETUP

### Virtual Environment (Python 3.8+)

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. DEPENDENCIES INSTALLATION

All dependencies are in `requirements.txt`. The main packages:

```
FastAPI & Web:
  - fastapi
  - uvicorn[standard]
  - python-multipart

Database:
  - sqlalchemy
  - pydantic

NLP & ML:
  - transformers (BERT, BART models from HuggingFace)
  - torch (PyTorch for neural networks)
  - scikit-learn (classical ML models)
  - nltk (NLP toolkit)
  - vaderSentiment (classical sentiment)

Speech:
  - openai-whisper (speech recognition)
  - librosa (audio processing)
  - soundfile (audio I/O)
  - pydub (audio manipulation)

Analysis & Visualization:
  - pandas
  - numpy
  - matplotlib
  - seaborn
  - jupyter
```

### GPU Acceleration (Optional)

For faster Transformer inference, install CUDA-enabled PyTorch:

```bash
# For NVIDIA GPU with CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For NVIDIA GPU with CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Check GPU availability:
```python
import torch
print(torch.cuda.is_available())  # Should print True
```

## 3. MODEL DOWNLOADING

Models are downloaded on first use and cached in `~/.cache/huggingface/`:

- **VADER Sentiment**: Downloaded from VADER package (~50KB)
- **XLM-RoBERTa**: ~700MB (multilingual sentiment)
- **BART-large-MNLI**: ~1.6GB (zero-shot classification)
- **BERT-NER**: ~400MB (named entity recognition)
- **Whisper**: ~140MB for 'base' model

**First run may take 5-10 minutes for model downloads.**

## 4. DATABASE SETUP

SQLite database is created automatically on first run:

```bash
uvicorn main:app --reload
```

The startup event creates:
- `sql_app.db` (SQLite database)
- `reports/` (directory for reports)

Then populate with test data:
```bash
curl -X POST http://127.0.0.1:8000/api/seed_data
```

## 5. RUNNING THE SERVER

### Development Mode (with auto-reload)
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Access Swagger UI:
- Browser: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 6. JUPYTER NOTEBOOK

Run analysis and examples:

```bash
jupyter notebook diploma_analysis.ipynb
```

Or launch Jupyter Lab:
```bash
jupyter lab
```

## 7. TESTING NLP MODELS

### Test VADER (Classical)
```python
from nlp_classical import classical_sentiment

review = "Great climate control! Very comfortable"
result = classical_sentiment.analyze(review)
print(result)
# {'positive': 0.7, 'negative': 0.0, 'neutral': 0.3, 
#  'compound': 0.6, 'label': 'positive'}
```

### Test Transformer
```python
from nlp_transformer import transformer_sentiment

review = "The temperature is way too high!"
result = transformer_sentiment.analyze(review)
print(result)
# {'label': 'NEGATIVE', 'score': 0.95, 'model': 'transformer'}
```

### Test Model Comparison
```python
from model_comparison import model_comparator

reviews = [
    "Excellent climate system",
    "Too hot, very uncomfortable",
    "Perfect conditions"
]

comparison = model_comparator.compare_sentiment_analysis(reviews)
print(f"Agreement: {comparison['summary']['model_agreement_rate']*100:.1f}%")
```

### Test Speech Recognition
```python
from speech_recognition import voice_manager

# Requires audio file
result = voice_manager.process_voice_input('voice_command.wav')
print(f"Transcript: {result['transcript']}")
print(f"Command: {result['command']}")
```

## 8. API TESTING

### Create Feedback
```bash
curl -X POST http://127.0.0.1:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Temperature is too high, needs AC",
    "rating": 2,
    "location_id": 1
  }'
```

### Get Regional Statistics
```bash
curl http://127.0.0.1:8000/api/feedback/sentiment-stats/1
```

### Compare Models
```bash
curl http://127.0.0.1:8000/api/models/comparison
```

### Process Voice Command
```bash
curl -X POST http://127.0.0.1:8000/api/voice/process \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "command.wav",
    "location_id": 1,
    "user_id": 1
  }'
```

## 9. TROUBLESHOOTING

### ModuleNotFoundError
```bash
# Install missing package
pip install [package_name]

# Verify installation
python -c "import [package_name]"
```

### CUDA/GPU Issues
```bash
# Fall back to CPU
export CUDA_VISIBLE_DEVICES=""
python main.py

# Or in Python:
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
```

### Models Not Downloading
```bash
# Check cache directory
ls ~/.cache/huggingface/

# Clear cache and redownload
rm -rf ~/.cache/huggingface/
```

### Database Lock
```bash
# Remove lock file if exists
rm sql_app.db-wal
rm sql_app.db-shm

# Restart server
```

## 10. PROJECT STRUCTURE

```
diploma-project/
├── main.py                      # FastAPI app
├── models.py                    # SQLAlchemy models
├── schemas.py                   # Pydantic schemas
├── crud.py                      # CRUD operations
├── database.py                  # DB connection
│
├── nlp_classical.py             # VADER, TF-IDF, Rules
├── nlp_transformer.py           # BERT, BART, RoBERTa
├── speech_recognition.py        # Whisper, Voice parser
├── model_comparison.py          # Model benchmarks
│
├── diploma_analysis.ipynb       # Jupyter notebook
├── simulator.py                 # IoT sensor simulator
│
├── QUICKSTART.py                # Quick start guide
├── USAGE_EXAMPLES.py            # API examples
├── ARCHITECTURE.md              # Architecture doc
│
├── requirements.txt             # Dependencies
├── README.md                    # Project documentation
├── sql_app.db                   # SQLite database
└── reports/                     # Report directory
```

## 11. VERIFICATION CHECKLIST

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] FastAPI server starts: `uvicorn main:app --reload`
- [ ] Database created: `sql_app.db` file exists
- [ ] Test data seeded: Call `/api/seed_data`
- [ ] Swagger UI accessible: `http://localhost:8000/docs`
- [ ] Can create feedback: POST `/api/feedback`
- [ ] Can analyze feedback: GET `/api/feedback/sentiment-stats/1`
- [ ] Can compare models: GET `/api/models/comparison`
- [ ] Jupyter notebook runs: `jupyter notebook diploma_analysis.ipynb`
- [ ] All 4 diploma criteria implemented ✓

## 12. PERFORMANCE NOTES

### Speed (on 4-core CPU without GPU)
- VADER: 500-1000 reviews/sec
- Transformer: 20-50 reviews/sec
- Whisper: 1-2 sec per audio minute

### Memory Usage
- VADER: ~100MB
- Transformer models: 2-4GB
- Full system: 4-6GB RAM recommended

### Optimization Tips
1. Use classical VADER for fast processing
2. Use Transformer only for complex/uncertain cases
3. Implement caching for repeated texts
4. Use GPU if available (100x faster)
5. Batch process texts when possible

## 13. NEXT STEPS

1. **Read**: `ARCHITECTURE.md` for system design
2. **Learn**: `USAGE_EXAMPLES.py` for API patterns
3. **Try**: `diploma_analysis.ipynb` for full examples
4. **Modify**: Adapt for your use case
5. **Deploy**: Use production settings for deployment

---

**Questions?** Check README.md or ARCHITECTURE.md for details.
