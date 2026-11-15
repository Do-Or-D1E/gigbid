"""Canonical skill taxonomy for GigBid.

DSL, one skill per line:  Name | category | alias, alias | implied ;; implied ;; implied
Implied phrases are noun phrases that describe the skill without naming it.
The `personas` field is computed later from persona evidence (see personas.py).
"""
from __future__ import annotations

_RAW = """
Python | language | python3, py, Python scripting | scripts and services written in a general-purpose scripting language with a deep data ecosystem ;; notebooks promoted into packaged, importable modules ;; a typed, tested codebase in the language most data teams default to
SQL | language | structured query language, SQL queries, T-SQL | hand-written joins and window functions over relational tables ;; queries that aggregate millions of rows with common table expressions ;; reporting views defined directly in the database
TypeScript | language | TS, typed JS | a statically typed layer over browser scripting with shared interfaces ;; compile-time checked types across client and server ;; strict typing enforced on the whole codebase
JavaScript | language | JS, ES6, vanilla JS | browser scripting without a framework ;; client-side logic written in modern ECMAScript
Bash scripting | language | shell scripting, bash, shell scripts | cron-driven command-line scripts that glue deployment steps together ;; terminal automation for repetitive server chores
R | language | R language, RStudio, tidyverse | pipe-chained analysis scripts with grammar-of-graphics output ;; reproducible statistical notebooks rendered to web reports
Go | language | Golang, go lang | compiled, concurrent services with goroutines and channels ;; a single static binary deployed without a runtime
PHP | language | php, PHP 8, LAMP stack | server-rendered pages from classic shared-hosting scripts ;; a legacy dynamic-page codebase on cheap hosting
PyTorch | ml | torch, pytorch lightning | a deep-learning framework with dynamic computation graphs ;; custom neural network layers trained on a single GPU ;; hand-written training loops with mixed precision
TensorFlow | ml | tensorflow, Keras, TF, TFLite | layered neural network models exported to a lite format for on-device inference ;; a graph-based deep-learning stack with a high-level model API
scikit-learn | ml | sklearn, scikit learn | classical machine-learning pipelines with cross-validation and grid search ;; a reusable preprocessing-plus-estimator pipeline ;; baseline classifiers and regressors benchmarked before anything heavier
XGBoost | ml | xgb, gradient boosting, gradient boosted trees | gradient-boosted decision trees tuned on tabular data ;; a boosted-tree model that beat the neural baseline on structured features
Hugging Face Transformers | ml | transformers, HuggingFace, HF Transformers, hugging face | pretrained language models pulled from the open model hub ;; a BERT-style encoder loaded from a public checkpoint ;; tokenizers and model classes from the community model library
LangChain | llm | langchain, LangChain agents | chains of prompts, parsers and tools wired together in an orchestration library ;; a composable LLM pipeline with output parsers and retrievers
LangGraph | llm | langgraph, LangGraph agents | a stateful multi-step agent modelled as a graph of nodes with checkpoints ;; an agent workflow with explicit branches, loops and human-approval steps
RAG | llm | retrieval-augmented generation, retrieval augmented generation, RAG pipeline, RAG system | an assistant that answers from the client's own documents with cited passages ;; document chunking, retrieval and grounded answer generation ;; a question-answering bot that looks up source material before replying
Pinecone | llm | pinecone, Pinecone index | a managed hosted vector index with namespaces and metadata filters ;; a serverless similarity-search service for high-dimensional points
pgvector | llm | pg_vector, Postgres vector extension | embedding similarity search inside the relational database ;; vector columns with an approximate-nearest-neighbour index next to the transactional tables
vector databases | llm | vector database, vector store, vector DB | a store optimised for nearest-neighbour lookups over high-dimensional points ;; an index that returns the closest passages for a query vector
embeddings | llm | vector embeddings, sentence embeddings, text embeddings | dense numeric representations of text for semantic search ;; documents and queries mapped into the same numeric space
OpenAI API | llm | openai, GPT-4, ChatGPT API, GPT API, OpenAI GPT | calls to a hosted frontier chat-completion model with function calling ;; structured JSON output from a commercial language-model endpoint
prompt engineering | llm | prompting, prompt design, prompt templates | carefully versioned instruction text with few-shot examples ;; systematic wording and structure tweaks to get reliable model output
LLM evaluation | llm | LLM evals, eval harness, LLM testing, model evaluation | a regression suite of graded prompts and reference answers ;; judge-model scoring with a rubric plus human spot checks ;; golden test sets that catch prompt regressions
fine-tuning | llm | fine tuning, LoRA, PEFT, instruction tuning | a base language model adapted on a few thousand labelled examples ;; low-rank adapters trained on the client's domain data
NLP | ml | natural language processing, text mining, text analytics | a pipeline that turns free-text tickets and emails into structured fields ;; linguistic preprocessing of messy user-written text
text classification | ml | document classification, sentiment analysis, intent classification | a labelled-category model for incoming messages ;; automatic routing of each inbound message to the right queue by predicted topic
named entity recognition | ml | NER, entity extraction | extraction of company names, dates and amounts from unstructured paragraphs ;; token-level tagging of people, places and products
computer vision | ml | CV, image recognition, image classification, object detection | models that inspect photos or video frames for defects ;; bounding-box detection on camera images ;; pixel-level analysis of product photos
OCR | ml | optical character recognition, document OCR, Tesseract, text extraction from scans | automatic reading of text from scanned invoices and photographed forms ;; digitised paper documents turned into machine-readable fields
speech recognition | ml | ASR, speech-to-text, Whisper, audio transcription | automatic transcripts of call recordings ;; time-stamped transcripts generated from audio files
recommendation systems | ml | recommender systems, recommender, collaborative filtering | a customers-also-liked ranking built from interaction history ;; personalised suggestions from purchase and click behaviour
anomaly detection | ml | outlier detection, fraud detection, anomaly alerts | automatic flagging of records that deviate from learned patterns ;; an unsupervised detector that surfaces unusual sensor readings
time-series forecasting | ml | time series forecasting, demand forecasting, Prophet, ARIMA | weekly demand projections with seasonality and holiday effects ;; a rolling-origin backtested prediction of future volumes
feature engineering | ml | feature creation, feature store, feature pipelines | hand-crafted aggregates and lag columns derived from raw event logs ;; derived model inputs built from transactional history
reinforcement learning | ml | RL, Q-learning, reward modelling | an agent that learns a policy from rewards in a simulator ;; trial-and-error training against a reward signal
MLflow | mlops | mlflow, MLflow tracking, ML experiment tracking | an experiment tracker with a model registry and run comparisons ;; logged parameters, metrics and artefacts for every training run
AWS SageMaker | mlops | SageMaker, Amazon SageMaker | managed training jobs and real-time model endpoints in the client's cloud account ;; hosted inference endpoints with autoscaling
model deployment | mlops | model serving, ML deployment, MLOps, productionizing models | a trained model wrapped behind a versioned, monitored HTTP endpoint ;; a notebook prototype shipped into a production service with health checks
FastAPI | backend | fastapi, FastAPI framework | an async web service with automatic request validation and generated interactive docs ;; typed endpoints that validate payloads against schema models
Celery | backend | celery, Celery workers, distributed task queue | a broker-backed task queue with retries ;; background workers that pull jobs off a queue with backoff ;; scheduled, retryable asynchronous jobs
Redis | database | redis, Redis cache, in-memory cache | an in-memory key-value store for caching and rate limiting ;; a low-latency cache in front of the primary database ;; ephemeral state and counters held in memory
Airflow | data_infra | Apache Airflow, airflow DAGs | scheduled DAGs with dependencies, retries and backfills ;; a workflow orchestrator that runs the nightly pipelines in order
Docker | devops | docker, containerization, Docker Compose, containers | reproducible container images for every service ;; a compose file that brings up the whole stack with one command ;; packaged environments that behave identically on laptops and servers
Kubernetes | devops | k8s, K8s, kube | pods, deployments and autoscalers on a container orchestrator ;; rolling updates across a managed cluster
Apache Spark | data_infra | Spark, PySpark, Databricks | distributed tables processed across a cluster ;; billion-row transformations on a managed big-data platform
Kafka | data_infra | Apache Kafka, event streaming, Kafka Streams | partitioned event streams with consumer groups ;; a durable log of events consumed by several services
pandas | data | Pandas, Python data analysis | dataframe-based cleaning and reshaping of tabular files ;; in-memory tabular transformations with groupby and merge
NumPy | data | numpy, numerical computing | vectorised array maths in place of slow loops ;; matrix operations on large numeric arrays
Azure | cloud | Microsoft Azure, Azure cloud | workloads deployed on the client's Microsoft tenant ;; resources provisioned in a Microsoft-hosted cloud subscription
AWS | cloud | Amazon Web Services, EC2, S3, Lambda, AWS S3 | servers, object storage and serverless functions in Amazon's cloud ;; presigned uploads to a storage bucket and a managed queue ;; infrastructure in a private network with least-privilege roles
React | frontend | React.js, ReactJS, react | component-based user interfaces with hooks and shared state ;; a single-page application assembled from reusable view components ;; a client-side app that re-renders only what changed
Next.js | frontend | NextJS, Next.js App Router | server-rendered pages with file-based routing and incremental regeneration ;; a full-stack web framework with API routes and edge rendering
Redux | frontend | Redux Toolkit, redux, state management | a predictable global store with reducers and selectors ;; centralised client state with time-travel debugging
Tailwind CSS | frontend | Tailwind, tailwindcss | utility-class styling driven by a design-token config ;; a consistent look built from atomic classes instead of custom stylesheets
HTML/CSS | frontend | HTML, CSS, responsive design, HTML5 | hand-written semantic markup and responsive layouts ;; mobile-first page layouts without a UI kit
Vue.js | frontend | Vue, VueJS, Nuxt | a progressive component framework with single-file components ;; reactive templates built with a lightweight view library
Angular | frontend | AngularJS, Angular 15, RxJS | a batteries-included front-end framework with dependency injection and observables ;; enterprise dashboards built on a strongly opinionated framework
Node.js | backend | NodeJS, Node, node | event-driven server code running outside the browser on a non-blocking runtime ;; a lightweight service handling many concurrent connections
Express | backend | Express.js, ExpressJS | a minimal HTTP routing layer with middleware chains ;; hand-rolled route handlers with validation middleware
NestJS | backend | Nest.js, Nest | a modular server framework with dependency injection and decorators ;; controllers, providers and guards organised into feature modules
Django | backend | django, Django REST Framework, DRF | a batteries-included server framework with an ORM, admin and migrations ;; a model-driven back office with a generated admin site
Ruby on Rails | backend | Rails, RoR, Ruby | convention-over-configuration MVC with generators and active-record models ;; a rapidly scaffolded monolith with opinionated defaults
Java Spring | backend | Spring Boot, Spring, Java | enterprise services built with annotation-driven dependency injection on the JVM ;; layered controllers and repositories in a corporate-style stack
.NET | backend | C#, ASP.NET, dotnet | enterprise web services built on Microsoft's managed runtime ;; a corporate line-of-business app in a statically typed Microsoft stack
Laravel | backend | laravel, Eloquent, Blade | an expressive MVC web framework with templated views and a built-in ORM ;; artisan-style scaffolding for quick CRUD apps
GraphQL | backend | graphql, Apollo, GraphQL API | a single typed query endpoint where clients ask for exactly the fields they need ;; a schema with resolvers replacing a pile of separate routes
REST API design | backend | REST API, RESTful API, API design, REST | resource-oriented HTTP endpoints with versioning and pagination ;; consistent error formats and idempotent writes
WebSockets | backend | websockets, Socket.IO, real-time updates, websocket | live updates pushed to the browser over a persistent connection ;; chat and presence features that feel instant ;; a bidirectional channel for notifications
RabbitMQ | backend | rabbitmq, AMQP, message queue | a message broker decoupling the web tier from slow jobs ;; durable queues with acknowledgements between services
OAuth | security | OAuth2, Auth0, social login, SSO, OpenID Connect | sign-in with Google and company single sign-on ;; delegated login through an identity provider with scopes and refresh tokens ;; hosted identity with social logins and role claims
JWT authentication | security | JWT, JSON Web Tokens, token auth | stateless signed access tokens with short expiry and refresh rotation ;; session handling without server-side session storage
PostgreSQL | database | Postgres, psql, PG | a relational database with transactions, constraints and JSON columns ;; carefully indexed tables with versioned migrations ;; foreign keys, partial indexes and constraint-level integrity enforced in the database itself
Prisma | database | Prisma ORM, prisma | a type-safe ORM with a declarative schema file and generated client ;; schema-first database access with automatic migrations
MongoDB | database | Mongo, mongoose, MongoDB Atlas | a document database with flexible schemas and aggregation pipelines ;; JSON-shaped records stored without fixed tables
Elasticsearch | database | elasticsearch, Elastic, OpenSearch, ELK | full-text search with relevance tuning and faceted filters ;; typo-tolerant product search over a large catalogue
Firebase | cloud | firebase, Firestore, Firebase Auth | a hosted backend-as-a-service with a realtime database and push notifications ;; serverless data sync for web and phone clients
Vercel | cloud | vercel, Vercel deployment | git-push deploys with preview URLs for every branch ;; edge-hosted frontend with serverless functions and zero-config builds
GitHub Actions | devops | CI/CD, CI pipeline, continuous integration, GitHub CI | automated build, test and deploy workflows triggered on every push ;; a pipeline that blocks merges when checks fail
Stripe | payments | stripe, Stripe Checkout, Stripe Connect, Stripe payments | card payments, subscriptions and webhooks handled by a hosted payments processor ;; recurring billing with proration and failed-payment retries ;; a checkout flow with signed webhook handlers
Shopify | ecommerce | Shopify store, Shopify theme, Shopify Liquid, Shopify apps | a hosted storefront with custom theme code and app integrations ;; theme templates and a custom checkout extension for an online shop ;; a merchant-facing store with product and inventory syncing
Playwright | testing | playwright, Playwright tests | cross-browser end-to-end scripts that click through real user journeys on every pull request ;; headless browser tests run in the pipeline with traces on failure
Cypress | testing | cypress, Cypress e2e | browser tests with time-travel debugging and network stubbing ;; component and end-to-end checks authored in an interactive runner
Jest | testing | jest, Vitest, unit testing | unit tests with mocks and snapshot assertions ;; a fast test suite guarding the business logic ;; coverage gates enforced on every merge
Excel | spreadsheet | Microsoft Excel, MS Excel, VLOOKUP, Excel formulas | pivot tables and lookup formulas in workbooks ;; a macro-free workbook model with named ranges and scenario tabs ;; spreadsheet models the finance team opens every Monday
Google Apps Script | spreadsheet | Apps Script, Google Sheets automation, Sheets macros, GAS | scripts living inside a shared online spreadsheet that email people and fill tabs automatically ;; custom menu items and time-based triggers in a cloud spreadsheet
Power BI | bi | PowerBI, Microsoft Power BI, Power BI Desktop | interactive reports published to the company's Microsoft analytics workspace ;; drill-through dashboards with row-level security
DAX | bi | DAX measures, Data Analysis Expressions | calculated measures for year-over-year and rolling averages in a tabular model ;; time-intelligence calculations inside the semantic model
Tableau | bi | tableau, Tableau Desktop, Tableau Public | visual-analytics workbooks with parameters and calculated fields ;; a published executive view with filters and action links
Looker | bi | Looker Explore, LookML | a governed semantic layer where metrics are defined once in code ;; modelled dimensions and measures exposed to non-technical explorers
Looker Studio | bi | Google Data Studio, Data Studio | free browser-based dashboards connected straight to spreadsheets and ad platforms ;; shareable marketing report templates that refresh on open
Qlik | bi | Qlik Sense, QlikView | associative-engine dashboards with a load script behind them ;; a legacy corporate reporting portal built on a niche analytics suite
dbt | data_infra | dbt Core, dbt Cloud, data build tool | version-controlled query models with tests and documentation ;; modular warehouse transformations with lineage and automated assertions ;; staging, intermediate and mart layers built from plain query files
BigQuery | warehouse | big query, GCP BigQuery, Google BigQuery | a serverless columnar warehouse billed per terabyte scanned ;; partitioned tables queried at scale in Google's cloud
Snowflake | warehouse | snowflake, Snowflake data warehouse, Snowflake SQL | a cloud warehouse with separate compute clusters per team ;; virtual warehouses that suspend when idle
ETL | data_infra | ETL pipelines, ELT, data pipelines, data ingestion | an extract, reshape and load process that gathers several sources into one place ;; nightly ingestion jobs that land raw files and publish clean tables
data modeling | data_infra | dimensional modelling, star schema, data modelling | fact and dimension tables arranged so reporting queries stay simple ;; a schema designed around the questions the business asks
data cleaning | data | data wrangling, data preparation, data quality, data munging | deduplication, standardisation and repair of malformed records before any analysis ;; reconciling inconsistent exports from several systems
Google Analytics 4 | analytics | GA4, Google Analytics, GA4 reporting | event-based web and app measurement with conversion tracking ;; a tagged website whose sessions, events and audiences are visible in Google's measurement suite
Mixpanel | analytics | mixpanel, product analytics, Amplitude | event-level product usage tracking with user properties ;; in-app event streams turned into usage graphs
A/B testing | stats | AB testing, split testing, experimentation, A/B experiments | randomised variant comparisons with a pre-agreed success metric ;; control-versus-treatment experiments with significance checks ;; a landing-page experiment readout
statistics | stats | statistical analysis, hypothesis testing, inferential statistics | confidence intervals and significance tests on messy samples ;; careful treatment of variance, sample size and bias
regression analysis | stats | linear regression, logistic regression, regression modelling | a fitted model that quantifies how much each driver moves the outcome ;; coefficient-level explanations of what drives the number
survey analysis | stats | survey data analysis, questionnaire analysis, Likert analysis | weighted, cross-tabulated responses from a questionnaire ;; coded open-ended answers and rating-scale summaries
sales forecasting | stats | revenue forecasting, budget forecasting, forecast model | revenue projections for the coming quarter with best and worst-case ranges ;; a trend-and-seasonality projection reviewed monthly with finance
SPSS | stats | spss, SAS, Stata | menu-driven statistical packages favoured by academic researchers ;; legacy syntax files from a university stats department
cohort analysis | analytics | cohort retention, retention analysis, cohort tables | signup-month cohorts tracked for how many users stay active ;; a retention triangle that shows when each group drops off
funnel analysis | analytics | conversion funnel, funnel optimisation, drop-off analysis | step-by-step conversion rates from first visit to purchase ;; a map of where in the sign-up journey most people abandon
churn analysis | analytics | attrition analysis, retention drivers, churn drivers | an analysis of which accounts are drifting away and why ;; a list of at-risk subscribers with contributing factors
customer segmentation | analytics | RFM analysis, clustering customers, audience segmentation, customer clustering | customers grouped by recency, frequency and spend ;; distinct behavioural segments for targeted campaigns
KPI definition | analytics | metric definition, KPI framework, metrics design | an agreed, written definition of exactly how each headline number is calculated ;; a metric dictionary the whole team signs off
data visualization | bi | data viz, dataviz, visual analytics | clear charts that make a trend obvious at a glance ;; annotated visuals prepared for a board pack
dashboard design | bi | KPI dashboard, executive dashboard, dashboarding | a one-page view of the numbers leadership checks every morning ;; layout and metric hierarchy designed around decisions
Flutter | mobile | Dart, Flutter app | a cross-platform widget toolkit compiling one codebase to both phone platforms ;; pixel-identical screens on two mobile operating systems
React Native | mobile | RN, Expo, React Native app | a cross-platform phone app built from component code and native bridges ;; one team shipping to both app stores from shared screens
iOS development | mobile | Swift, SwiftUI, iPhone app, Xcode | a native app shipped through Apple's app store ;; screens built with Apple's declarative interface toolkit
Android development | mobile | Kotlin, Jetpack Compose, Android app, Android Studio | a native app published on the Google Play store ;; activities and view models in a Google-flavoured mobile stack
Unity | gamedev | Unity3D, Unity game, C# Unity | a 3D scene with physics, prefabs and a scripted gameplay loop ;; a mobile game built in a popular real-time engine
Unreal Engine | gamedev | UE5, Unreal, Blueprints | a photoreal real-time scene with visual scripting graphs ;; cinematic game levels with high-end lighting
Solidity | blockchain | smart contracts, Ethereum, Web3, NFT | on-chain contracts for token minting and escrow ;; a decentralised application with wallet connection
WordPress | cms | wordpress, WP, WooCommerce, Elementor | a plugin-driven content site managed from an admin dashboard ;; custom theme and plugin work on a popular blogging platform
SEO | marketing | search engine optimization, on-page SEO, link building | higher search rankings earned through keyword and backlink work ;; technical audits of crawlability and metadata
Google Ads | marketing | PPC, Google AdWords, paid search | search-engine ad campaigns with keyword bids and landing-page tests ;; a monthly ad budget optimised for cost per lead
Graphic design | design | logo design, Photoshop, Illustrator, Figma, branding | a brand identity with logo, palette and typography ;; polished marketing visuals and social creatives
Video editing | media | Premiere Pro, After Effects, video production, motion graphics | raw footage cut into a polished edit with titles and sound ;; short-form clips with captions and transitions
Copywriting | content | content writing, blog writing, ghostwriting, article writing | persuasive web copy and long-form articles in the brand's voice ;; a month of publish-ready blog posts
Translation | content | translator, localization, English-Spanish translation, subtitling | documents rendered faithfully between two languages ;; localised product strings and subtitles
Salesforce | crm | Salesforce Apex, SFDC, Salesforce admin | a customer-relationship platform with custom objects and automated flows ;; lead-routing automations inside a hosted sales system
SAP | erp | SAP ERP, SAP ABAP, SAP HANA | enterprise resource-planning configuration for finance and procurement modules ;; a heavyweight back-office suite used by large manufacturers
Bookkeeping | finance | accounting, QuickBooks, Xero | reconciled monthly books and a tidy chart of accounts ;; bank feeds matched to invoices every week
Data entry | admin | manual data entry, copy-paste work, keying, listing upload | manual copy-and-paste of listing details into a spreadsheet ;; figures keyed in from scanned pages into a form
""".strip()


def _parse():
    skills = {}
    for line in _RAW.splitlines():
        parts = [p.strip() for p in line.split(" | ")]
        assert len(parts) == 4, line
        name, cat, aliases, implied = parts
        skills[name] = {
            "category": cat,
            "aliases": [a.strip() for a in aliases.split(",") if a.strip()],
            "implied_by": [i.strip() for i in implied.split(";;") if i.strip()],
        }
    return skills


BASE = _parse()
SKILL_NAMES = sorted(BASE)


def build_taxonomy(persona_skills: dict[str, set[str]]) -> dict:
    """persona_skills: pid -> set of canonical skills with evidence."""
    out = {}
    for name in sorted(BASE):
        e = BASE[name]
        out[name] = {
            "category": e["category"],
            "aliases": list(e["aliases"]),
            "implied_by": list(e["implied_by"]),
            "personas": sorted(pid for pid, s in persona_skills.items() if name in s),
        }
    return out


def forms(name: str):
    e = BASE[name]
    return e["aliases"], e["implied_by"]
