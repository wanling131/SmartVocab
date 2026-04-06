# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmartVocab is an intelligent English vocabulary learning system with deep learning-based recommendations. It uses a Flask backend with MySQL database and a vanilla JavaScript frontend.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all unit tests (pytest)
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
  - `utils.py`: `APIResponse` helper class, `@handle_api_error` decorator

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
  - `memory_cache.py`: TTL + LRU memory cache with decorator support

- **`models/`**: Trained PyTorch model files (`.pth`)
  - `deep_learning_recommender.pth`: Global recommendation model
  - `deep_learning_recommender_user_<id>.pth`: User-specific models

- **`config.py`**: Configuration constants (`APP_CONFIG`, `LEARNING_PARAMS`, etc.)

### Frontend Structure

- **`frontend/`**: Single-page application
  - `index.html`: All pages (auth, dashboard, learning, statistics, plans, levels, evaluation, profile, favorites)
  - `main.js`: ES module entry point with all page logic (~3800 lines)
  - `js/api-client.js`: API request wrapper with JWT handling, 2-min cache, request deduplication
  - `js/utils.js`: ES module with shared utilities (`escapeHtml`, `safeHtml`, `showToast`, `animateNumber`, etc.)
  - `js/charts.js`: Chart.js wrapper module for data visualization (progress, difficulty, radar charts)
  - `js/worker.js`: Web Worker for background filtering/sorting/statistics
  - `js/worker-client.js`: `WorkerClient` class wraps Web Worker with auto-fallback
  - `js/components/`: Page-specific modules (achievements.js, toast.js)
  - `styles.css`: Global styles with CSS variables and animations

### Database

16 tables: `users`, `words`, `user_learning_records`, `learning_sessions`, `recommendations`, `evaluation_papers`, `evaluation_paper_items`, `evaluation_results`, `level_gates`, `user_level_progress`, `user_learning_plans`, `user_achievements`, `user_streaks`, `learning_reports`, `user_favorite_words`

### API Modules

| Module | Endpoints | Description |
|--------|-----------|-------------|
| Auth | `/api/auth/login`, `/register`, `/profile`, `/password/<user_id>` | JWT authentication, password change |
| Vocabulary | `/api/vocabulary/...`, `/words`, `/words/<id>` | Learning sessions, import/export, word CRUD (admin) |
| Learning | `/api/learning/...` | Records, forgetting curve |
| Recommendation | `/api/recommendations/<user_id>` | Smart word recommendations with algorithm selection |
| Plans | `/api/plans` | Learning plan CRUD |
| Evaluation | `/api/evaluation/...` | Level tests |
| Levels | `/api/levels/...` | Gate progress, unlock |
| Achievements | `/api/achievements/<user_id>` | User achievements, streak, reports |
| Favorites | `/api/favorites/<user_id>`, `/api/favorites/<user_id>/ids`, `/api/favorites/<user_id>/word/<id>` | Word favorites CRUD, quick ID check |
| Health | `/api/health`, `/api/health/db`, `/api/health/cache`, `/api/health/metrics` | System status, DB/cache checks, metrics |

## Key Patterns

### Database Setup
1. Create MySQL database (e.g., `smartvocab`)
2. Run `文档/数据库建表脚本.sql` for base schema
3. Run `文档/数据库升级迁移脚本.sql` for incremental updates (favorites, achievements, etc.)
4. Or use `python tools/migrate_db.py` for programmatic migration

### Authentication Flow
1. User login/register returns JWT token
2. Frontend stores token in `localStorage`
3. All protected API calls include `Authorization: Bearer <token>`
4. Backend uses `@require_auth` decorator to validate

### Permission Check
- Use `check_user_access(user_id)` from `api/auth_middleware.py` to verify current user can access target user's data
- This function is shared across all API modules - do NOT create local `_check_user_access` copies

### Recommendation System
- Multi-algorithm with dynamic weights: difficulty_based, frequency_based, learning_history, deep_learning, collaborative, random_exploration
- Weights are normalized and adjusted based on user history
- **Deep Learning Model** (`core/recommendation/deep_learning_recommender.py`):
  - PyTorch dual-tower neural network with LayerNorm (NOT BatchNorm - supports batch=1 inference)
  - 25-dimensional word/user feature vectors
  - Cross-attention mechanism between user and word encoders
  - Falls back to traditional recommendations if PyTorch unavailable
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
- `DB_POOL_SIZE`: Connection pool size (optional, default 10)
- `SECRET_KEY`: Flask session signing
- `JWT_SECRET_KEY`: JWT token signing
- `JWT_EXPIRATION_HOURS`: Token validity period (optional, default 24)
- `ADMIN_USERS`: Comma-separated usernames for admin operations (optional)

Optional:
- `SMARTVOCAB_SKIP_DL_INIT=1`: Skip PyTorch model loading during tests (faster startup)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Login returns 500 error | Check if request body is double-stringified in `api-client.js` |
| Dashboard blank after login | Clear browser cache, check console for JS errors |
| `JWT_SECRET_KEY` error in production | Set strong key: `openssl rand -hex 32` |
| PyTorch import fails | System falls back to traditional recommendations automatically |
| Database connection fails | Verify `.env` has correct `DB_*` values, run connection test command |
| PyTorch model fails to load | Check `models/` directory for `.pth` files; system falls back to traditional recommendations |
| Model key mismatch error | Old model was BatchNorm+20dim, new is LayerNorm+25dim; delete old `.pth` and retrain |
| Tests fail with import errors | Ensure `pip install -r requirements.txt` includes `werkzeug<3` |
| Frontend shows blank page | Check browser console for JS errors; clear localStorage |
| Charts not rendering | Ensure Chart.js CDN loaded; check `window.ChartModule` exists |

## Code Standards

### Security
- **XSS Prevention**: Use `escapeHtml()` function in `frontend/main.js` for all user-displayed content
- **SQL Injection**: Use parameterized queries via `execute_query(query, params)`; whitelist validation for dynamic column names
- **Authentication**: All sensitive endpoints must use `@require_auth` decorator
- **Input Validation**: Empty answers return `False` in answer checking

### Logging
- Use `logging.getLogger(__name__)` for logging, never `print()`
- Database uses connection pool - no manual connection management needed
- Use `@handle_api_error` decorator on API endpoints for consistent error handling

### Caching
- Use `tools/memory_cache.py` for frequently accessed data
- `@cached(ttl_seconds)` decorator for function result caching
- Cache keys: `make_word_key()`, `make_user_stats_key()`, `make_recommendation_key()`
- Invalidate with `invalidate_user_cache(user_id)` when user data changes

### Testing
- Unit tests in `tests/` directory (pytest)
- E2E tests in `tests/e2e/specs/` (Playwright)
- Test user: `e2e_tester` / `TestPass123`
- Production mode (`APP_ENV=production`) enforces strong JWT/secret keys

### Frontend
- **ES Module**: `main.js` is loaded as type="module", imports from `js/api-client.js`
- `api-client.js` handles 401 by clearing token and dispatching `auth:logout` event
- All dynamic content must be HTML-escaped before insertion
- `showPage()` manages page visibility via `.active` class
- **API caching**: GET requests are cached for 2 minutes by default
- **Modularity**: `main.js` is large (~3400 lines). For new features, prefer adding modules in `frontend/js/` and importing

### Key Frontend Functions
- `loadDashboard()`: Loads progress stats and recommendations
- `loadFavoritesPage()`: Loads user's favorite words with search/filter
- `loadProfilePage()`: Loads user info and achievements
- `loadPlansPage()`: Loads active plan and plan history
- `loadStatistics()`: Loads learning statistics with Chart.js visualizations
- `loadAdvancedCharts()`: Initializes Chart.js charts (trend, difficulty, POS, radar)
- `speakWord(word)`: Uses Web Speech API to pronounce words
- `exportFavoritesCSV()`: Exports favorites to CSV file
- `exportLearningReportCSV/JSON/PDF()`: Export learning reports in multiple formats
- `updateExampleSection(word)`: Displays example sentence with highlighted word
- `getDifficultyDescription(level)`: Returns difficulty label (入门/基础/中级/高级)

### UI Components
- **Word Card**: Shows word, phonetic, example sentence, pronunciation button
- **Gate Card**: Shows level name, difficulty stars, progress bar, status badges
- **Example Section**: Collapsible example sentence with word highlighting

### Performance Features
- **Lazy Loading**: Pages only load data on first visit (`pageLoaded` Set)
- **Web Worker**: Background thread for filtering/sorting/statistics (`js/worker.js`); use `window.workerClient.filter()` / `.stats()` / `.sort()` with auto-fallback
- **API Cache**: 2-minute TTL for GET requests, request deduplication for concurrent identical requests
- **Skeleton Loading**: Animated placeholders during data fetch
- **Chart.js Integration**: `js/charts.js` provides `ChartModule` with pre-configured chart types (line, bar, doughnut, radar) matching dark theme
