# Known Limitations & Future Improvements

## 1. Known Prototype Limitations

1. **Multi-Modal Complex Diagrams:**  
   The prototype uses high-performance optical text extraction (PyMuPDF) with OCR fallback. Complex architectural flowcharts or vector circuit diagrams without accompanying text labels are not transcribed via multi-modal vision models to control API latency and token cost.
2. **Local Volume Document Storage:**  
   In the default prototype setup, uploaded PDFs are saved to an isolated local directory (`backend/storage/uploads`). In multi-node production setups, this must be backed by an S3 or Cloudflare R2 bucket.
3. **In-Memory Cache vs Redis:**  
   When running without an active Redis container, background jobs run using FastAPI's asynchronous thread/task queue. Full distributed state locking requires the Dockerized Redis container.
4. **Context Window Sliding Cap:**  
   To prevent token explosion and maintain sub-second response times, the Tutor chat history is capped at an anchor message + the 4 most recent turns. Extremely long conversation threads may lose nuance from messages older than 5 turns unless they relate to active concepts.

---

## 2. Future Improvements Roadmap

1. **Multi-Modal Vision Understanding:** Integrate GPT-4o / Gemini 1.5 Pro vision to parse diagrams and charts into markdown tables during ingestion.
2. **Interactive Concept Knowledge Graph:** Build a force-directed SVG/D3 graph visualization showing concept dependencies (`depends_on`, `relates_to`).
3. **Spaced Repetition Flashcards (SM-2 Algorithm):** Automatically convert extracted concepts into an active recall flashcard deck with optimal review intervals.
4. **Audio & Voice Tutoring:** Integrate OpenAI Realtime WebRTC voice interface for hands-free audio study sessions.
