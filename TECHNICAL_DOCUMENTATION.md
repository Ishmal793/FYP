# System Architecture & Technical Documentation

## Overview

This project is an AI-driven Career Platform built with Django and Django REST Framework. The system provides a comprehensive pipeline that reads a job seeker's resume, parses it using LLMs, predicts matching job roles, fetches real-world job listings, and calculates ATS match scores between the candidate's CV and the job descriptions.

It leverages Groq's high-speed API with the `llama-3.3-70b-versatile` model to power specialized "agents" (micro-apps) that handle specific portions of the logic in a modular fashion.

---

## Complete Flow Diagram (System Pipeline)

```text
User (Job Seeker)
   │
   ▼
[ accounts ] API auth & role assignment
   │
   ▼
[ agents_resume_parser ]
   ├─ Upload PDF/TXT
   ├─ LLM extracts Skills, Exp, Edu, Certs
   └─ Saves JSON to [ resumes ] APP (Database)
        │
        ├─► [ agents_readiness ]
        │     └─ LLM evaluates resume quality (0-100) & provides feedback.
        │
        ├─► [ agents_field_classifier ]
        │     └─ LLM categorizes resume into Top 5 Job Families (e.g., Software Eng).
        │
        └─► [ agents_job_predictor ]
              └─ LLM recommends Top 5 specific Job Titles (e.g., Senior React Dev).
                   │
                   ▼
             [ agents_job_search ]
              ├─ SerpAPI queries Google Jobs for the predicted Titles.
              ├─ Validates raw job results via [ agents_jd_validator ] (LLM logic).
              └─ Returns valid jobs.
                   │
                   ▼
             [ agents_ats_matcher ]
              ├─ LLM compares specific parsed Resume against specific Job Description.
              ├─ Produces ATS Score (0-100), missing keywords, improvement tips.
              └─ If ATS >= 70, autosaves to [ jobs ] APP (Database) history.
```

---

## App 1: `accounts`

### 1️⃣ APP OVERVIEW
* **Purpose**: Manages user authentication, profile creation, and core authorization logic.
* **Role in AI pipeline**: Foundation level. Secures the endpoints and binds users to their CVs and generated job results.
* **Input/Output**: Inputs user credentials; outputs JWT tokens and user profiles.
* **Interaction**: Integrated globally using the `IsJobSeeker` permission to restrict agent endpoints to valid users.

### 2️⃣ PROJECT STRUCTURE
* `models.py`: Defines the user database schema.
* `serializers.py`: Defines data serialization for signup and profile retrieval.
* `views.py`: Holds the API endpoints.
* `urls.py`: Holds routing information.

### 3️⃣ MODELS (models.py)
* **Classes**: `CustomUser` (inherits `AbstractBaseUser`), `CustomUserManager`.
* **Fields**: `email` (unique identifier), `role` (choices: 'job_seeker', 'hr'), `is_active`, `is_staff`.
* **Relationships**: No direct foreign keys, but serves as the target for `resumes.Resume` and `jobs.JobResult` relationships.
* **Behavior**: Uses email over standard Django usernames. Auto-defaults to 'job_seeker'. Superusers default to 'hr'.

### 4️⃣ SERIALIZERS (serializers.py)
* **Classes**: `UserSerializer` (retrieval), `RegisterSerializer` (creation).
* **Validation**: Checks `password` write-only conditions. Extracts `email`, `password`, `role`.

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* **Endpoints**: 
  - `POST /api/auth/register/`: Creates user.
  - `POST /api/auth/login/`: SimpleJWT TokenObtainPairView.
  - `GET /api/auth/profile/`: Returns current user details.
* **Logic**: Uses DRF generic views and JWT middleware.

### 11️⃣ SECURITY / VALIDATION
* **Permissions**: `AllowAny` for registration. `IsAuthenticated` for profile views.

---

## App 2: `resumes`

### 1️⃣ APP OVERVIEW
* **Purpose**: Serves as the database repository for uploaded/parsed resumes.
* **Role in AI pipeline**: The central state cache. Stores the parsed JSON data so LLMs don't have to re-parse the file repeatedly.
* **Interactions**: Created by `agents_resume_parser`, read by all predictive/scoring agents.

### 3️⃣ MODELS (models.py)
* **Classes**: `Resume`
* **Fields**: `user` (FK to CustomUser), `file` (FileField), `parsed_data` (JSONField), `created_at`.
* **Database behavior**: Stores unstructured outputs securely. `parsed_data` defaults to a dict.

---

## App 3: `jobs`

### 1️⃣ APP OVERVIEW
* **Purpose**: Database repository for matched jobs.
* **Role in AI pipeline**: End-of-the-line sink where successful, highly-matched ATS results are stored for the user to review.
* **Interactions**: Written to passively by `agents_ats_matcher`.

### 3️⃣ MODELS (models.py)
* **Classes**: `JobResult`
* **Fields**: `user` (FK to CustomUser), `resume` (FK to Resume), `job_title`, `company`, `location`, `description`, `job_url`, `ats_score`, `skills_score`, `experience_score`, `education_score`, `matching_reason`, `improvement_suggestion`, `missing_keywords` (JSON).
* **Behavior**: Orders by `-created_at`. Acts as a historical log.

### 4️⃣ SERIALIZERS (serializers.py)
* **Classes**: `JobResultSerializer` (Reads all fields, maps FKs).

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* **Endpoints**: 
  - `GET /api/profile/jobs/history/`: Pulls the user's matched jobs.
  - `POST /api/profile/jobs/history/`: Can manually save a job result.
* **Logic**: Auto-deduplicates manual POSTs based on `job_title` + `company`.

---

## App 4: `agents_resume_parser`

### 1️⃣ APP OVERVIEW
* **Purpose**: Translates unstructured PDF/TXT files into strict JSON format.
* **Role in AI pipeline**: Step 1. Extracts data. 
* **Input**: Binary file -> Text.
* **Output**: JSON containing arrays of Skills, Tools, Education, Experience, Certifications.

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* `POST /api/resume/parse/`: 
  - Extracts text from `request.FILES['resume']`.
  - Determines if PDF or TXT.
  - Calls `parse_resume_text()`.
  - Auto-saves the result into the `resumes.Resume` model and returns the ID.

### 6️⃣ AGENT WORKFLOW
* Parses file -> Extracts raw string -> Checks guardrails (length >= 50 chars) -> Prompts Groq LLaMA3 -> Validates if returned JSON comprises empty lists -> Returns valid structured object.

### 7️⃣ FUNCTIONS BREAKDOWN
* `extract_text_from_pdf`: Uses `fitz` (PyMuPDF) to loop over pages and return a long string.
* `get_parser_llm`: Initializes `ChatGroq` (`llama-3.3-70b-versatile`, `temp=0.0`) with `with_structured_output(ParsedResume)`.
* `parse_resume_text`: Formats the prompt enforcing comprehensive extraction, guarding against empty texts and LLM fallback errors.

### 8️⃣ AI / LANGCHAIN / GROQ
* **Model**: `llama-3.3-70b-versatile`.
* **Prompt**: Demands NO EMPTY ARRAYS, "EXHAUSTIVE EXTRACTION", and hallucination prevention. Uses Pydantic `ParsedResume` strictly.

---

## App 5: `agents_readiness`

### 1️⃣ APP OVERVIEW
* **Purpose**: Computes a confidence score of how strongly the resume is written.
* **Role in AI pipeline**: Parallel analysis branch.
* **Output**: Readiness Score out of 100 with actionable feedback.

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* `POST /api/readiness/score/`: 
  - Takes `resume_id`.
  - Pulls `parsed_data` from DB context.
  - Runs `calculate_readiness_score()`.

### 6️⃣ AGENT WORKFLOW
* Receives JSON -> Prompt requests strict rubrical scoring (Skills:40, Tools:30, Certifications:20, Projects:10) -> Groq returns structured Math breakdown and 3 suggestions. 

### 7️⃣ FUNCTIONS BREAKDOWN
* `calculate_readiness_score`: Builds prompt and parses result. Enforces math and schema matching `ReadinessScore` Pydantic model. 

---

## App 6: `agents_field_classifier`

### 1️⃣ APP OVERVIEW
* **Purpose**: Provides broad domains suitable for the candidate (e.g., "Web Development").
* **Role in AI pipeline**: Analytics helper. Categorization.

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* `POST /api/fields/classify/`: Validates `resume_id`, fetches `parsed_data`, outputs 5 domains.

### 6️⃣ AGENT WORKFLOW
* Instructs LLM acting as "Career Counselor" to map granular technical skills to broad industry buckets. Requires exactly 5 answers.

---

## App 7: `agents_job_predictor`

### 1️⃣ APP OVERVIEW
* **Purpose**: Target specifically what job titles this candidate should look for.
* **Role in AI pipeline**: Precursor to Job Search. Connects candidate background to actual job market titles.

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* `POST /api/jobs/predict/`: Validates `resume_id`, fetches `parsed_data`, loops through LLM.

### 6️⃣ AGENT WORKFLOW
* Feeds ONLY `skills`, `tools`, and `experience` fragments to LLM to preserve token context.
* Demands modern titles (e.g., "Full Stack Engineer") with a 0-100 `confidence` score and `match_reason`. Output constrained to exactly 5 objects.

---

## App 8: `agents_job_search`

### 1️⃣ APP OVERVIEW
* **Purpose**: Fetches live jobs from Google Jobs mapping the predicted titles.
* **Role in AI pipeline**: Data ingestion from the external world. Requires internet fetching.

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* `POST /api/search/live/`: Takes list of `titles` and `location`. Returns array of `live_jobs`.

### 6️⃣ AGENT WORKFLOW
* Loops top 2 titles -> Queries SerpAPI `google_jobs` engine -> Parses pagination/links -> Checks for generic duplicated links -> Validates JD using `agents_jd_validator`. Truncates massive descriptions for memory-safe UI transport. Caps at 8 results max for cost/rate limits.

### 9️⃣ DATA FLOW
* External API (SerpAPI JSON) -> Transformation (filtering duplicates, mapping keys) -> Filtered via LLM validation -> Final formatted list.

---

## App 9: `agents_jd_validator`

### 1️⃣ APP OVERVIEW
* **Purpose**: Cleans garbage job postings.
* **Role in AI pipeline**: Filter node. Prevents bad generic text from breaking the ATS Matcher.

### 6️⃣ AGENT WORKFLOW
* Asks LLM if the JD text contains 1. a Title, 2. Tasks, 3. Qualifications.
* Returns `True` if at least 2 conditions evaluate to True.

---

## App 10: `agents_ats_matcher`

### 1️⃣ APP OVERVIEW
* **Purpose**: Evaluates candidate fit for a specific real-world job posting.
* **Role in AI pipeline**: The Final Execution. Highly complex verification step. Outputs the ultimate platform metric (ATS match %).

### 5️⃣ VIEWS / API ENDPOINTS (views.py)
* `POST /api/ats/match/`: 
  - Takes `resume_id` and array of `jobs` dicts.
  - Matches each sequentially.
  - Hard-filters jobs with ATS Score < 70%.
  - Sorts descending and takes TOP 3.
  - AUTO-SAVES the top 3 into the `jobs.JobResult` database module for historical tracking.

### 6️⃣ AGENT WORKFLOW
* Uses cross-referencing prompt technique.
* LLM receives `[Parsed Candidate Profile]` vs `[Job Target Requirements]`.
* Output is forced into strict arithmetic bounds (Skills 40 max, Experience 30 max, Edu 30 max = 100 max).
* Also mandates identifying `missing_keywords` to empower the user.

### 9️⃣ DATA FLOW
* Inputs: `models.Resume` (DB) + `SerpAPI Web Output` (Live Data).
* Transforms: LLM Arithmetic + Text generation.
* Output State: `models.JobResult` (DB) + JSON response to frontend.

---

## 13️⃣ SUMMARY

### Core Responsibilities
- Secure user flow and isolation of resumes.
- Perfect text extraction from CV PDFs to structured dictionaries using generative AI.
- Intelligent inference mapping a CV to market job titles.
- Validated external search against live job engines.
- Strict, rubrical benchmarking and gap-analysis using agentic comparison layers.

### Key Features
- Uses Langchain structured output (`pydantic`) explicitly throughout to guarantee predictable JSON APIs.
- Pipelined guardrails (preventing LLMs from hallucinating properties, filtering broken JDs, error fallback structures).
- Modular architecture: 7 discrete "agents" apps instead of monolithic logic.

### Dependencies
- Django & Django REST Framework (Routing, Auth, DB)
- LangChain Groq (Agentic LLM bindings)
- PyMuPDF (PDF Extraction)
- SerpAPI (Live Web Searching)
- Pydantic (Output constraints)
