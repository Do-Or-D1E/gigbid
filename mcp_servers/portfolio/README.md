# GigBid Portfolio MCP server

A read-only MCP server that answers one question for an AI assistant: "what in this freelancer's portfolio proves they can do X?"

GigBid uses it inside its agents. It also runs on its own, so any freelancer can connect it to Claude Desktop, Cursor or another MCP client and let the assistant look things up in their own portfolio when they write proposals.

It never changes the portfolio and it never sends anything anywhere. Over stdio it needs no account and no network (after the first start has downloaded the small embedding model).

## What it does

It indexes a portfolio folder (CV, case studies, repositories with code, client reviews, past proposals) and searches it by meaning and by keywords. Each result has an id, a type, a source file and a date. For past proposals it also shows the outcome (won, replied, ignored).

### Tools

| Tool | What it does |
|---|---|
| `search_evidence` | Finds the items that best prove ONE requirement, for example "Celery task queues for ETL". Arguments: `requirement`, `k` (1 to 15, default 5), optional `filters` (`types`, `outcome`, `since`, `exclude_items`) |
| `get_case_study` | Loads the full text and metadata of one item by id, for example `ai_ml-cs-07` |
| `list_skills` | Lists the skills on the profile and how many items mention each skill |

All three are annotated read only, not destructive, idempotent and closed world.

### Resources

| URI | Content |
|---|---|
| `portfolio://case/{item_id}` | A case study as Markdown |
| `portfolio://proposal/{item_id}` | A past proposal with its job summary and outcome |
| `portfolio://repo/{item_id}` | A repository README and its code files |
| `portfolio://profile` | The profile JSON (skills, rates, availability) |

### Prompts

| Prompt | Use |
|---|---|
| `answer_screening_question` | Answer a client's screening question in 2 to 4 sentences from portfolio evidence only, citing item ids |
| `check_fit` | Paste a job post. It lists the requirements and rates your evidence for each as strong, partial or none, then gives a bid-or-skip view |
| `pick_case_study` | Describe a client's problem. It picks the best case study and gives 3 bullets |

## Run it

The repository has no `[project.scripts]` entry in `pyproject.toml`, so `uvx --from git+...` does not work. Clone the repository and run the module.

```bash
git clone https://github.com/Do-Or-D1E/gigbid
cd gigbid
uv sync
uv run python -m mcp_servers.portfolio.server --stdio --owner ai_ml
```

`--owner` is the name of a folder under `data/personas/`. The repository ships three fictional portfolios: `ai_ml`, `fullstack` and `data_analyst`.

Do not set `DATABASE_URL` for standalone use. Without a database the server uses a local identity (`local:<owner>`) and writes one line per search to `cache/audit.jsonl` in the clone (arguments are masked). Note that `agent/settings.py` reads a `.env` file in the repository root, so do not leave a `DATABASE_URL` there.

Other modes of the same server:

```bash
# Authenticated Streamable HTTP server on port 8101 (what GigBid itself uses)
uv run python -m mcp_servers.portfolio.server --port 8101 --owner ai_ml
# The same without the bearer token check (local testing only)
uv run python -m mcp_servers.portfolio.server --port 8101 --owner ai_ml --no-auth
```

The first search builds the index, which takes a moment. In a clone it is saved under `data/processed/<flavour>/<owner>/` and reused. If you change a portfolio folder, delete those folders for that owner so the index is rebuilt. The embedding model (`minishlab/potion-base-8M`, MIT, CPU only) is downloaded on first use into `cache/models`, or into `GIGBID_MODEL_DIR` if you set it.

### Docker

```bash
docker build -f infra/docker/portfolio-mcp.Dockerfile -t gigbid-portfolio-mcp .
docker run -i --rm gigbid-portfolio-mcp --owner ai_ml
```

The image runs the server over stdio (`-i` keeps stdin open). It contains the three sample portfolios and the embedding model. To use your own folder, mount it (see below).

## Connect it to Claude Desktop

Edit `claude_desktop_config.json` (Settings, Developer, Edit Config) and restart Claude Desktop.

With a clone and `uv`:

```json
{
  "mcpServers": {
    "gigbid-portfolio": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/gigbid",
        "python",
        "-m",
        "mcp_servers.portfolio.server",
        "--stdio",
        "--owner",
        "ai_ml"
      ]
    }
  }
}
```

With Docker:

```json
{
  "mcpServers": {
    "gigbid-portfolio": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "gigbid-portfolio-mcp", "--owner", "ai_ml"]
    }
  }
}
```

On Windows, write paths with forward slashes or doubled backslashes in the JSON.

Then ask something like: "Use the portfolio tools to find proof of experience with RAG pipelines, then draft a 3 sentence answer to this screening question: ...". The prompts appear in the prompt picker of clients that support MCP prompts.

## Use your own portfolio

The server reads a folder with the same layout as `data/personas/<id>/`. Only `profile.json` is required for the folder to be recognised as a portfolio. Add whatever else you have.

```
data/personas/<your_id>/
  profile.json          required: persona_id, name, headline, skills (list), hourly_rate_usd, min_project_usd
  cv.pdf or cv.md       your CV (the PDF is used if both exist)
  case_studies/*.md     one Markdown file per case study, with front matter (below)
  repos/<slug>/         one folder per repository
    README.md
    meta.json           item_id, project_id, slug, date, language
    src/...             code files (.py, .ts, .tsx, .js, .jsx, .sql, .yaml, .yml, .toml, .ipynb, .r, .sh, .json)
  reviews.jsonl         one JSON object per line: item_id, project_id, client_industry, rating, date, text
  proposals.jsonl       one JSON object per line: item_id, job_title, job_summary, proposal_text, date,
                        client_industry, outcome (won, replied, ignored), cited_project_ids
```

A case study starts with YAML front matter:

```markdown
---
item_id: me-cs-01
project_id: me-p01
title: "Invoice field extraction for accounts payable"
date: 2022-09
client_industry: "fintech"
---
# Invoice field extraction for accounts payable

Problem, approach, stack, results...
```

Use item ids that start with your folder name and a dash (for example `me-cs-01`). The resource templates find the owner from that prefix.

Folder location is fixed to `data/personas/` of the repository. With a clone, copy or link your folder there and pass its name:

```bash
uv run python -m mcp_servers.portfolio.server --stdio --owner me
```

With Docker, mount your folder over a new persona folder:

```bash
docker run -i --rm -v /path/to/my_portfolio:/app/data/personas/me gigbid-portfolio-mcp --owner me
```

`list_skills` compares the skills in `profile.json` with the skills it finds in your items. Skills are tagged by exact name or alias from `data/taxonomy.json`, so a skill that is not in the taxonomy is not counted as evidenced there. Search itself does not depend on the taxonomy. Add your own skills to `data/taxonomy.json` if you want them counted. The gold files in `data/personas/<id>/gold/` are only used by evaluations and are not needed.

## Privacy

- Stdio mode makes no network calls while running. The only download is the embedding model on first use.
- Your portfolio files stay where they are. The server reads them and builds an index (kept in memory and, in a clone, saved under `data/processed/`).
- Search calls are logged locally to `cache/audit.jsonl` (arguments with emails, phone numbers and handles masked). Delete the file any time.
- The content you return to an AI assistant goes to whichever assistant you connect. Check what your client sends to its model.

## Tests

```bash
uv run pytest -q tests/contract
```

The contract test fails when a tool's name, schema or annotations change without a new snapshot (`tests/contract/snapshots/portfolio.json`).
