<!-- Copilot instructions for the proctoring-system repo -->
# Copilot / AI Agent Instructions

Purpose
- Help contributors and AI agents make safe, focused code changes in this repo.

Big picture
- Monorepo with a Node/Express backend and a React frontend. Docker compose can start Postgres + Redis + both apps.
- Backend: REST API + Socket.IO real-time events for proctoring; media uploaded to S3 and analyzed via AWS Rekognition. See [backend/server.js](backend/server.js).
- Frontend: React app (Create React App) using `socket.io-client`, `simple-peer`, and `react-webcam`. See [frontend/package.json](frontend/package.json).

Key components & patterns (find and follow these)
- API prefix and rate limiting: all API routes mounted under `/api/*` and limited in [backend/server.js](backend/server.js).
- WebSockets & rooms: sockets join rooms named `session-<id>`, `student-<userId>`, `faculty-<userId>`; common events: `join-session`, `video-stream`, `screen-share`, `suspicious-activity`. See [backend/server.js](backend/server.js).
- WebRTC signaling: lightweight placeholder in [backend/src/services/webrtcService.js](backend/src/services/webrtcService.js) using `offer`/`answer`/`ice-candidate` relay.
- Face recognition: uploads current image to S3 then calls AWS Rekognition `compareFaces`. See [backend/src/services/faceRecognitionService.js](backend/src/services/faceRecognitionService.js).
- Recording handling: `RecordingService` buffers chunks in memory and flushes to S3 every 10 chunks (to avoid memory bloat). See [backend/src/services/recordingService.js](backend/src/services/recordingService.js).
- Database: Sequelize with `sync({ alter: true })` in [backend/src/config/database.js](backend/src/config/database.js) — migrations are not used; be cautious when changing models in production.
- Logging: winston logger centralized in [backend/src/utils/logger.js](backend/src/utils/logger.js).

Developer workflows
- Backend local dev: `cd backend && npm run dev` (uses `nodemon`). See scripts in [backend/package.json](backend/package.json).
- Frontend local dev: `cd frontend && npm start`.
- Run tests: `cd backend && npm test` (Jest) — tests may be sparse.
- Docker compose: `docker-compose up --build` from repo root to start Postgres, Redis, backend, and frontend as configured in `docker-compose.yml`.

Required environment variables (create `.env` in `backend/` for local dev)
- Database: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- AWS: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`
- App: `PORT`, `FRONTEND_URL` (used by CORS)

Project-specific conventions & cautions
- Avoid committing secrets. AWS keys must be in env, not source control.
- Database synchronization: code uses Sequelize `sync({ alter: true })`. For schema changes prefer manual planning; altering in production can be destructive.
- S3 URL handling: `faceRecognitionService.extractS3Key(url)` assumes `https://<bucket>.s3.amazonaws.com/<key>` format; watch for alternate URL formats.
- Recording memory model: `RecordingService` keeps chunks in memory until flush; do not increase the chunk threshold without considering memory.
- Socket rooms are the primary access-control surface for real-time messages; ensure emits target the correct room names.

Integration points to inspect before changes
- AWS SDK usage: [backend/src/config/aws.js](backend/src/config/aws.js) — S3, Rekognition, SQS, CloudWatch are configured.
- Authentication: routes under [backend/src/routes/authRoutes.js](backend/src/routes/authRoutes.js) protect user context (controllers expect `req.user`). Confirm JWT middleware when modifying controllers.
- Database models: review `backend/src/models/*` before schema changes.

Useful examples to copy/adapt
- Join session socket flow: see [backend/server.js](backend/server.js) lines handling `join-session` and room naming.
- Face verification flow: `faceRecognitionService.verifyFace` — pattern is: upload image -> Rekognition compareFaces -> return S3 URL + similarity score.
- Recording lifecycle: `startRecording`, `addChunk`, `flushChunks`, `stopRecording` in [backend/src/services/recordingService.js](backend/src/services/recordingService.js).

When in doubt
- Run the app locally via Docker Compose to reproduce end-to-end behavior: `docker-compose up --build`.
- Check `server.js` for top-level middleware (CORS, rate limiting, body parsers) that affect API behavior and tests.
- Preserve logging calls (use `logger.info` / `logger.warn` / `logger.error`) rather than console.log when adding backend logic.

Ask for clarification
- If the repository lacks tests or CI, ask maintainers which environment is canonical for integration testing (local docker-compose vs cloud).

If you update these instructions, keep them short and reference concrete files above.
