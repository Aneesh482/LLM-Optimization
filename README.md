<h1 align="center">Welcome to LLM Optimization Gateway 👋</h1>
<p>
  <img alt="Version" src="https://img.shields.io/badge/version-v1.0-blue.svg?cacheSeconds=2592000" />
  <a href="https://github.com/Aneesh482/LLM-Optimization" target="_blank">
    <img alt="Documentation" src="https://img.shields.io/badge/documentation-yes-brightgreen.svg" />
  </a>
</p>

> A provider-agnostic gateway for optimizing LLM requests before they reach the model provider.The system analyzes incoming prompts and conversation context, applies context-aware compression, manages long conversations, stores recoverable context, and integrates with provider-side caching to reduce unnecessary input token usage while preserving important information.Modern LLM applications often send large amounts of repeated or unnecessary context with every request. This increases token consumption, latency, and cost.

### 🏠 [Homepage](https://github.com/Aneesh482/LLM-Optimization)

## Author

👤 **Aneesh**

* Github: [@Aneesh482](https://github.com/Aneesh482)
* LinkedIn: [@Aneesh Dasgupta](https://linkedin.com/in/aneesh-dasgupta22)

## Installation

### Prerequisites

- Python 3.10+
- Bun
- Git
- Gemini API Key

### Clone the Repository

```bash
git clone https://github.com/Aneesh482/LLM-Optimization.git
cd LLM-Optimization
````

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` directory:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

### Frontend Setup

Open a new terminal:

```bash
cd frontend
bun install
bun run dev
```

The frontend will start using Vite.

### API Documentation

Once the backend is running, open:

```text
http://localhost:8000/docs
```

### Show your support

Give a ⭐️ if this project helped you!





