# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmartVocab is an intelligent English vocabulary learning system with deep learning-based recommendations. It uses a Flask backend with MySQL database and a vanilla JavaScript frontend.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all unit tests (112 tests)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_auth.py -v

# Run single test
python -m pytest tests/test_auth.py::TestJWTToken::test_generate_token -v

# Run tests without loading DL model (faster)
SMARTVOCAB_SKIP_DL_INIT=1 python -m pytest tests/ -v

# Run E2E tests (Playwright)
cd tests/e2e && npx playwright test

# Run E2E tests with UI (headed mode)
cd tests/e2e && npx playwright test --headed

# Start development server
python main.py

# Start production server (Gunicorn)
set APP_ENV=production
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

# Database connection test
python -c "from tools.database import test_connection; test_connection()"
```

## Architecture

### Backend Structure

- **`api/`**: Flask Blueprint REST API endpoints
  - `api_launcher.py`: Registers all blueprints, Flask app factory
  - Each `*_api.py` is a Blueprint with related endpoints
  - `auth_middleware.py`: JWT token generation/validation, `@require_auth` decorator
  - `utils.py`: `APIResponse` helper class

- **`core/`**: Business logic layer
  - `auth/`: User authentication with bcrypt
  - `recommendation/`: Multi-algorithm recommendation engine + PyTorch deep learning model
  - `learning/`: Learning record management
  - `forgetting_curve/`: Ebbinghaus forgetting curve calculations
  - `vocabulary/`: Vocabulary learning sessions
  - `evaluation/`: Level test paper generation and scoring

- **`tools/`**: Database CRUD operations
  - `database.py`: MySQL connection pool singleton
  - `base_crud.py`: Base CRUD class with common operations
  - `*_crud.py`: Table-specific CRUD classes
  - `migrate_db.py`: Database schema migration helper

- **`models/`**: Trained PyTorch model files (`.pth`)
  - `deep_learning_recommender.pth`: Global recommendation model
  - `deep_learning_recommender_user_<id>.pth`: User-specific models

- **`config.py`**: Configuration constants (`APP_CONFIG`, `LEARNING_PARAMS`, etc.)

### Frontend Structure

- **`frontend/`**: Single-page application
  - `index.html`: All pages (auth, dashboard, learning, statistics, plans, levels, evaluation, profile)
  - `main.js`: ES module with all page logic (includes `escapeHtml` for XSS prevention)
  - `js/api-client.js`: API request wrapper with JWT handling
  - `styles.css`: Global styles with CSS animations

### Database

14 tables: `users`, `words`, `user_learning_records`, `learning_sessions`, `recommendations`, `evaluation_papers`, `evaluation_paper_items`, `evaluation_results`, `level_gates`, `user_level_progress`, `user_learning_plans`, `user_achievements`, `user_streaks`, `learning_reports`

### API Modules

| Module | Endpoints | Description |
|--------|-----------|-------------|
| Auth | `/api/auth/login`, `/register`, `/profile` | JWT authentication |
| Vocabulary | `/api/vocabulary/...` | Learning sessions, import/export |
| Learning | `/api/learning/...` | Records, forgetting curve |
| Plans | `/api/plans` | Learning plan CRUD |
| Evaluation | `/api/evaluation/...` | Level tests |
| Levels | `/api/levels/...` | Gate progress, unlock |
| Achievements | `/api/achievements/<user_id>` | User achievements, streak, reports |
| Health | `/api/health` | System status |

## Key Patterns

### Authentication Flow
1. User login/register returns JWT token
2. Frontend stores token in `localStorage`
3. All protected API calls include `Authorization: Bearer <token>`
4. Backend uses `@require_auth` decorator to validate

### Recommendation System
- Multi-algorithm with dynamic weights: difficulty_based, frequency_based, learning_history, deep_learning, collaborative, random_exploration
- Weights are normalized and adjusted based on user history
- PyTorch dual-tower neural network (falls back to traditional if unavailable)
- User-specific models trained after 50 learning records
- Cold-start handling for new users

### Learning Session Flow
1. `POST /api/vocabulary/start-session` creates session
2. `POST /api/vocabulary/current-word` gets current word with question
3. `POST /api/vocabulary/submit-answer` submits answer, updates mastery
4. Repeat until complete

### Question Types
- `choice`: Multiple choice with 4 options
- `translation`: User types Chinese translation
- `spelling`: User types English word from Chinese definition

## Environment Variables

Required in `.env`:
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: MySQL connection
- `SECRET_KEY`: Flask session signing
- `JWT_SECRET_KEY`: JWT token signing
- `ADMIN_USERS`: Comma-separated usernames for admin operations (optional)

Optional:
- `SMARTVOCAB_SKIP_DL_INIT=1`: Skip PyTorch model loading during tests (faster startup)

## Code Standards

### Security
- **XSS Prevention**: Use `escapeHtml()` function in `frontend/main.js` for all user-displayed content
- **SQL Injection**: Use parameterized queries via `execute_query(query, params)`; whitelist validation for dynamic column names
- **Authentication**: All sensitive endpoints must use `@require_auth` decorator
- **Input Validation**: Empty answers return `False` in answer checking

### Logging
- Use `logging.getLogger(__name__)` for logging, never `print()`
- Database uses connection pool - no manual connection management needed

### Testing
- Unit tests in `tests/` directory (pytest)
- E2E tests in `tests/e2e/specs/` (Playwright)
- Test user: `e2e_tester` / `TestPass123`
- Production mode (`APP_ENV=production`) enforces strong JWT/secret keys

### Frontend
- `api-client.js` handles 401 by clearing token and dispatching `auth:logout` event
- All dynamic content must be HTML-escaped before insertion
