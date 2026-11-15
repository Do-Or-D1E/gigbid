"""Job archetypes (category + stack pool + tasks + titles) and pricing tables, shared by jobs and proposals."""
from __future__ import annotations

# (category, owner persona or None, titles, tasks (infinitive), pool ordered core-first)
_A = []


def A(cat, owner, titles, tasks, pool):
    _A.append(dict(category=cat, owner=owner, titles=titles, tasks=tasks, pool=pool))


# ------------------------------------------------------------------ ai_ml
A("LLM & RAG Applications", "ai_ml",
  ["RAG chatbot over our company documents", "LLM assistant for our internal knowledge base", "Document Q&A with source citations"],
  ["build a chatbot that answers customer questions from our help-center articles and PDF manuals",
   "set up a document question-answering tool over our internal policies that shows where each answer came from",
   "create an assistant that drafts replies to support emails using our existing knowledge base"],
  ["RAG", "OpenAI API", "embeddings", "Pinecone", "LangChain", "prompt engineering", "FastAPI", "vector databases"])
A("LLM & RAG Applications", "ai_ml",
  ["LLM agent workflow with human approval", "Agentic research assistant", "AI agent to qualify inbound leads"],
  ["build a multi-step agent that researches a topic, drafts a summary and waits for a person to approve it before anything is sent",
   "automate lead qualification with an LLM agent that can look up the CRM, ask follow-up questions and hand off to sales",
   "design a tool-using assistant that can check order status and escalate edge cases to a human"],
  ["LangGraph", "OpenAI API", "LLM evaluation", "prompt engineering", "FastAPI", "RAG"])
A("LLM & RAG Applications", "ai_ml",
  ["Semantic search with pgvector", "Natural-language search for our catalogue", "Vector search inside Postgres"],
  ["add semantic search to our product catalogue using the PostgreSQL database we already run",
   "let our editors search a large archive by meaning rather than exact keywords",
   "replace our keyword search with similarity search over embeddings and keep the infrastructure small"],
  ["pgvector", "PostgreSQL", "embeddings", "FastAPI", "vector databases", "RAG"])
A("ML Model Development", "ai_ml",
  ["Customer churn prediction model", "Lead scoring model", "Late-payment prediction"],
  ["build a model that predicts which subscribers will cancel in the next 30 days",
   "score incoming leads by how likely they are to convert so sales can focus on the best ones",
   "predict which invoices will be paid late from payment history and customer data"],
  ["scikit-learn", "XGBoost", "pandas", "feature engineering", "Python", "PostgreSQL"])
A("ML Model Development", "ai_ml",
  ["Product recommendation engine", "Recommender for our store", "Personalised suggestions for app users"],
  ["add a customers-also-bought recommender to our online store",
   "build personalised content suggestions from reading history for our app",
   "rank items on the home page using each user's past behaviour"],
  ["recommendation systems", "Python", "pandas", "Redis", "embeddings", "scikit-learn"])
A("ML Model Development", "ai_ml",
  ["Neural network for sensor data", "Deep learning model for tabular and image inputs", "PyTorch model for prediction"],
  ["train a neural network on our sensor logs to predict equipment failures a week ahead",
   "port an existing notebook experiment into a clean, reproducible training pipeline",
   "improve a baseline model's accuracy with better features and a small neural network"],
  ["PyTorch", "Python", "NumPy", "feature engineering", "Docker"])
A("NLP & Text Analytics", "ai_ml",
  ["Review sentiment and topic classifier", "Fine-tune a transformer for text tagging", "Text classification with transformers"],
  ["classify thousands of customer reviews by topic and sentiment",
   "fine-tune a pretrained language model to tag clauses in legal documents",
   "build a classifier that sorts incoming emails into twelve categories"],
  ["Hugging Face Transformers", "text classification", "NLP", "Python", "PyTorch", "fine-tuning"])
A("NLP & Text Analytics", "ai_ml",
  ["Entity extraction from contracts", "Extract names, dates and amounts from documents", "NER pipeline"],
  ["extract company names, dates and monetary amounts from long contracts into a spreadsheet",
   "pull structured facts out of free-text incident reports",
   "build a service that tags people, places and organisations in news articles"],
  ["named entity recognition", "NLP", "Python", "FastAPI", "Docker"])
A("NLP & Text Analytics", "ai_ml",
  ["Support ticket auto-routing", "Automatic ticket categorisation", "Message triage classifier"],
  ["route support tickets to the correct team automatically and flag urgent ones",
   "categorise incoming customer messages and suggest a priority",
   "cut manual sorting of inbound requests with a lightweight classifier"],
  ["text classification", "scikit-learn", "NLP", "pandas", "Celery"])
A("Computer Vision & OCR", "ai_ml",
  ["Defect detection from camera images", "Object counting in photos", "Computer vision for quality control"],
  ["detect cosmetic defects on products from line-camera images",
   "count and classify items in warehouse photos",
   "classify field photos into a dozen categories with a model small enough to run on a modest server"],
  ["computer vision", "PyTorch", "Python", "NumPy", "Docker", "model deployment"])
A("Computer Vision & OCR", "ai_ml",
  ["Invoice and receipt data extraction", "OCR pipeline for scanned forms", "Extract fields from scanned documents"],
  ["extract totals, dates and vendor names from scanned receipts and invoices",
   "digitise a backlog of scanned paper forms into structured records",
   "read text from photographed documents and validate it against our database"],
  ["OCR", "Python", "FastAPI", "named entity recognition", "Docker"])
A("MLOps & Deployment", "ai_ml",
  ["Deploy our model as a production API", "Productionise a notebook model", "Model serving on AWS"],
  ["take a model that only runs in a notebook and deploy it as a monitored production API",
   "move our model hosting to managed infrastructure with versioning and rollbacks",
   "set up endpoints that autoscale during our busy hours"],
  ["model deployment", "Docker", "FastAPI", "MLflow", "AWS SageMaker", "AWS"])
A("MLOps & Deployment", "ai_ml",
  ["Automated model retraining pipeline", "ML pipeline with experiment tracking", "Nightly training and evaluation jobs"],
  ["build a pipeline that retrains and evaluates our models on a schedule and promotes the winner automatically",
   "add experiment tracking and a model registry to our data science team's workflow",
   "replace manual retraining with a scheduled, monitored job"],
  ["Airflow", "MLflow", "Docker", "Python", "model deployment", "Celery"])
A("Forecasting & Anomaly Detection", "ai_ml",
  ["Demand forecasting for 2,000 SKUs", "Weekly sales forecasting model", "Energy load forecasting"],
  ["forecast weekly demand for about two thousand products across several warehouses",
   "produce day-ahead forecasts of consumption for each of our sites",
   "replace spreadsheet forecasts with a backtested model that updates every week"],
  ["time-series forecasting", "XGBoost", "pandas", "Python", "feature engineering", "Airflow"])
A("Forecasting & Anomaly Detection", "ai_ml",
  ["Anomaly detection for sensor streams", "Fraud and anomaly alerts", "Unusual-activity detection service"],
  ["detect unusual readings in sensor data and alert the operations team",
   "flag suspicious transactions for manual review in near real time",
   "build alerts that tell us when a metric drifts outside its normal range"],
  ["anomaly detection", "Python", "scikit-learn", "Redis", "Celery", "FastAPI"])

# ------------------------------------------------------------------ fullstack
A("Web App Development", "fullstack",
  ["Customer dashboard web app", "Next.js app with login and billing", "Build our SaaS front end and API"],
  ["build a customer dashboard where users log in, see their usage and update their plan",
   "turn our design files into a responsive web app with a database behind it",
   "launch the first version of our SaaS product, with accounts, teams and an admin area"],
  ["React", "Next.js", "TypeScript", "Tailwind CSS", "PostgreSQL", "Prisma"])
A("Web App Development", "fullstack",
  ["Internal booking and invoicing tool", "Django back-office application", "Admin system for our team"],
  ["build an internal tool for managing bookings, clients and invoices",
   "replace a set of shared spreadsheets with a proper web application and user roles",
   "create a staff-facing system with reports and an audit trail"],
  ["Django", "PostgreSQL", "Python", "REST API design", "Docker", "Redis"])
A("Web App Development", "fullstack",
  ["Rebuild admin screens in React", "React front end for an existing API", "Modernise our legacy front end"],
  ["rebuild our old jQuery admin screens as a modern single-page app on top of the API we already have",
   "add a new customer-facing area to an existing product without rewriting the back end",
   "move our front end to typed components with proper state management and tests"],
  ["React", "Redux", "TypeScript", "GraphQL", "Jest", "REST API design"])
A("E-commerce Development", "fullstack",
  ["Shopify theme customisation", "Custom Shopify store features", "Shopify product bundle builder"],
  ["customise our Shopify theme and add a bundle builder to product pages",
   "speed up our store and rebuild the collection pages to match a new brand design",
   "connect our store to an inventory system and show live stock on product pages"],
  ["Shopify", "JavaScript", "HTML/CSS", "REST API design"])
A("E-commerce Development", "fullstack",
  ["Custom storefront with checkout", "Headless e-commerce build", "Online shop on Next.js"],
  ["build a custom storefront with a cart, checkout and order history",
   "launch a small online shop for our products with card payments and email receipts",
   "replace a hosted shop with our own storefront so we can control the checkout experience"],
  ["Next.js", "Stripe", "PostgreSQL", "Tailwind CSS", "Vercel", "Redis"])
A("API & Backend Development", "fullstack",
  ["REST API for our mobile app", "Node.js backend and database design", "Build a secure backend API"],
  ["build the REST API behind our mobile app, including login, profiles and notifications",
   "design the database and API for a new booking product",
   "split a slow monolith endpoint into a clean, documented API"],
  ["Node.js", "Express", "PostgreSQL", "REST API design", "JWT authentication", "Docker", "Jest"])
A("API & Backend Development", "fullstack",
  ["GraphQL API design", "NestJS GraphQL backend", "Typed API gateway"],
  ["design a GraphQL API that unifies three internal services for our web and mobile clients",
   "build a typed backend with authentication and role-based access",
   "move a set of REST endpoints behind a single GraphQL schema without breaking clients"],
  ["NestJS", "GraphQL", "PostgreSQL", "TypeScript", "OAuth", "Prisma"])
A("API & Backend Development", "fullstack",
  ["Content API with search", "Node and MongoDB backend", "Backend for a publishing platform"],
  ["build a content backend with scheduling, drafts and fast search",
   "add full-text search and background processing to our existing Node backend",
   "create a backend for a catalogue of thousands of items with filters and an admin interface"],
  ["MongoDB", "Express", "Node.js", "REST API design", "Elasticsearch", "RabbitMQ"])
A("Web Testing & QA", "fullstack",
  ["Set up Playwright end-to-end tests", "Automated browser tests in CI", "E2E test suite for our web app"],
  ["set up automated end-to-end tests for our main user journeys and run them on every pull request",
   "replace a manual regression checklist with tests that run in CI",
   "make our flaky browser tests reliable and fast"],
  ["Playwright", "TypeScript", "GitHub Actions", "Jest", "Docker"])
A("Web Testing & QA", "fullstack",
  ["Cypress tests for checkout", "Cypress regression suite", "Front-end test automation"],
  ["write Cypress tests that cover our checkout and account flows",
   "add component and end-to-end tests to a React app that currently has none",
   "run browser tests on every release so regressions are caught before customers see them"],
  ["Cypress", "React", "GitHub Actions", "JavaScript"])
A("Cloud & DevOps Setup", "fullstack",
  ["Containerise app and set up CI/CD on AWS", "AWS deployment and pipeline", "Move our app to managed cloud hosting"],
  ["containerise our application and deploy it to AWS with a CI/CD pipeline and zero-downtime releases",
   "move off a single aging server onto managed infrastructure",
   "set up staging and production environments with automated deployments and basic monitoring"],
  ["AWS", "Docker", "GitHub Actions", "Bash scripting", "PostgreSQL", "Vercel"])
A("Real-time & Payments Features", "fullstack",
  ["Add Stripe subscriptions", "Subscription billing integration", "Payments and invoices for our SaaS"],
  ["add subscription billing, upgrades and invoices to our product",
   "integrate card payments with webhooks and a customer billing portal",
   "let customers manage their plan and payment method without contacting support"],
  ["Stripe", "Node.js", "React", "PostgreSQL", "JWT authentication", "Next.js"])
A("Real-time & Payments Features", "fullstack",
  ["Real-time chat and notifications", "Live updates with WebSockets", "Live dashboard features"],
  ["add live chat and instant notifications to our web app",
   "show live status changes on a dispatch or operations board without refreshing",
   "build presence and collaborative editing features"],
  ["WebSockets", "Node.js", "Redis", "React", "TypeScript", "Firebase"])
A("Real-time & Payments Features", "fullstack",
  ["Add single sign-on login", "OAuth login and role-based access", "SSO integration"],
  ["add company single sign-on and social login to an existing web app",
   "move our app from home-made passwords to a proper identity provider",
   "add role-based access and secure token handling to our API"],
  ["OAuth", "Express", "JWT authentication", "Docker", "Jest"])

# ------------------------------------------------------------------ data_analyst
A("Business Intelligence & Dashboards", "data_analyst",
  ["Power BI sales dashboard", "Executive KPI dashboard in Power BI", "Power BI reports for operations"],
  ["build a Power BI dashboard that shows sales, margin and returns by region and product",
   "rebuild our monthly management report as an interactive dashboard people can filter themselves",
   "replace a dozen emailed spreadsheets with one dashboard that refreshes daily"],
  ["Power BI", "DAX", "SQL", "dashboard design", "KPI definition", "data visualization"])
A("Business Intelligence & Dashboards", "data_analyst",
  ["Tableau dashboards for operations", "Tableau workbook and data prep", "Interactive Tableau reporting"],
  ["build Tableau dashboards that show utilisation, delays and cost per unit",
   "clean up our data sources and publish a trusted Tableau workbook for managers",
   "redesign our executive dashboard so the key numbers are obvious in five seconds"],
  ["Tableau", "SQL", "dashboard design", "data visualization", "KPI definition"])
A("Business Intelligence & Dashboards", "data_analyst",
  ["Looker semantic layer", "Looker model and metrics definitions", "Set up Looker for our team"],
  ["define our core metrics once in Looker so every team sees the same numbers",
   "build explores and dashboards on top of our BigQuery tables",
   "document and test a metrics layer that finance and product both trust"],
  ["Looker", "BigQuery", "data modeling", "KPI definition", "SQL"])
A("Business Intelligence & Dashboards", "data_analyst",
  ["Looker Studio marketing dashboard", "Automated reporting in Looker Studio", "Client report templates"],
  ["build a marketing performance dashboard that pulls from analytics and ad platforms",
   "create reusable client report templates that refresh on their own",
   "show campaign results, cost per lead and traffic sources on one page"],
  ["Looker Studio", "Google Analytics 4", "data visualization", "dashboard design"])
A("Data Pipelines & ETL", "data_analyst",
  ["dbt models on Snowflake", "Analytics engineering with dbt", "Warehouse transformation project"],
  ["move our reporting queries into tested, documented dbt models on Snowflake",
   "build staging and mart layers so analysts stop writing the same joins",
   "add data tests and freshness checks to our warehouse"],
  ["dbt", "Snowflake", "SQL", "data modeling", "ETL"])
A("Data Pipelines & ETL", "data_analyst",
  ["Nightly ETL pipeline with Airflow", "Automated data loads into Postgres", "Reporting database pipeline"],
  ["load data from three operational systems into one reporting database every night",
   "automate a manual export-and-clean routine and alert us when it fails",
   "build a reliable pipeline that standardises messy CSV exports"],
  ["Airflow", "Python", "PostgreSQL", "ETL", "data cleaning", "Docker"])
A("Data Pipelines & ETL", "data_analyst",
  ["BigQuery data mart with dbt", "KPI mart on BigQuery", "Warehouse modelling and orchestration"],
  ["build a KPI data mart on BigQuery that planners can slice by site and week",
   "orchestrate dbt runs and add monitoring for late or failing loads",
   "model our raw events into clean fact and dimension tables"],
  ["BigQuery", "dbt", "Airflow", "data modeling", "ETL", "SQL"])
A("Statistical & Experiment Analysis", "data_analyst",
  ["A/B test design and analysis", "Experiment analysis for checkout", "Experimentation support"],
  ["design and analyse A/B tests on our checkout and onboarding flows",
   "set up a repeatable way to read experiment results with proper significance checks",
   "review our last six tests and tell us which results we can actually trust"],
  ["A/B testing", "statistics", "Python", "funnel analysis", "regression analysis"])
A("Statistical & Experiment Analysis", "data_analyst",
  ["Pricing and driver analysis", "Regression analysis of key drivers", "Statistical modelling for pricing"],
  ["find out which factors really move price or demand and by how much",
   "build a regression model that explains what drives customer spend",
   "analyse a year of sales data and explain the main drivers to non-technical managers"],
  ["regression analysis", "statistics", "Python", "Excel", "data visualization"])
A("Statistical & Experiment Analysis", "data_analyst",
  ["Customer retention and churn analysis", "Cohort retention study", "Why customers cancel: analysis"],
  ["analyse retention by signup cohort and explain when and why customers leave",
   "identify the behaviours that predict churn and size the opportunity",
   "produce a retention report the leadership team can act on"],
  ["cohort analysis", "churn analysis", "pandas", "SQL", "data visualization"])
A("Statistical & Experiment Analysis", "data_analyst",
  ["Revenue forecast model", "Budget forecasting workbook", "Quarterly sales forecast"],
  ["build a revenue forecast with scenarios for the next two quarters",
   "replace a fragile forecasting spreadsheet with a documented model",
   "forecast monthly demand by region for budget planning"],
  ["sales forecasting", "Excel", "Python", "regression analysis"])
A("Marketing & Web Analytics", "data_analyst",
  ["GA4 reporting and attribution", "Google Analytics 4 audit and BigQuery export", "Marketing attribution analysis"],
  ["audit our Google Analytics 4 setup and work out which channels actually drive sales",
   "use the BigQuery export to build funnel and attribution reports",
   "fix our tracking and give the marketing team trustworthy conversion numbers"],
  ["Google Analytics 4", "BigQuery", "funnel analysis", "SQL", "data cleaning"])
A("Marketing & Web Analytics", "data_analyst",
  ["Product analytics in Mixpanel", "Funnels and retention for a mobile app", "In-app behaviour analysis"],
  ["analyse where new users drop out of our app in the first week",
   "set up funnels, cohorts and experiment readouts in Mixpanel",
   "tell us which features are associated with long-term retention"],
  ["Mixpanel", "funnel analysis", "cohort analysis", "A/B testing", "SQL"])
A("Marketing & Web Analytics", "data_analyst",
  ["Customer segmentation project", "RFM segmentation for CRM", "Audience segments from order history"],
  ["segment our customers into groups that deserve different offers",
   "turn two years of order history into segments the CRM team can target",
   "profile our best customers and find lookalikes in the rest of the base"],
  ["customer segmentation", "pandas", "SQL", "data visualization", "data cleaning"])
A("Spreadsheet Automation", "data_analyst",
  ["Google Sheets automation with Apps Script", "Automate weekly reporting in Sheets", "Spreadsheet workflow automation"],
  ["automate a weekly reporting routine that currently takes three people half a day",
   "add scripts to our shared sheets that clean imports and email a summary",
   "connect several spreadsheets so numbers stop being copied by hand"],
  ["Google Apps Script", "Excel", "data cleaning", "ETL"])
A("Spreadsheet Automation", "data_analyst",
  ["Excel reporting model", "Excel KPI workbook and clean-up", "Management reporting in Excel"],
  ["rebuild our monthly KPI workbook so it is accurate, documented and quick to refresh",
   "clean a messy data export and set up a pivot-based report",
   "make a finance workbook that non-experts can update safely"],
  ["Excel", "KPI definition", "dashboard design", "data cleaning"])
A("Survey & Research Analysis", "data_analyst",
  ["Customer survey analysis", "Employee survey report", "Survey design and results analysis"],
  ["analyse the results of a 3,000-response customer satisfaction survey and write up the findings",
   "clean the survey export, code the open-ended answers and summarise by segment",
   "produce a report on employee survey results for the leadership team"],
  ["survey analysis", "Excel", "statistics", "data visualization", "data cleaning"])
A("Survey & Research Analysis", "data_analyst",
  ["Survey data analysis in Python", "Research data analysis", "Statistical analysis of questionnaire data"],
  ["analyse questionnaire data with weighting and significance tests",
   "compare survey results between groups and explain which differences are real",
   "build reproducible analysis scripts for a recurring research survey"],
  ["survey analysis", "Python", "pandas", "statistics", "regression analysis"])

# ------------------------------------------------------------------ off-domain
A("Mobile App Development", None,
  ["Cross-platform mobile app", "Build an iOS and Android app", "Flutter app for our service"],
  ["build a cross-platform mobile app for our booking service", "ship a first version of our app to both app stores",
   "rebuild our existing app with a new design and offline mode"],
  ["Flutter", "iOS development", "Android development"])
A("Mobile App Development", None,
  ["React Native app with Firebase", "Native iPhone app", "Android app maintenance"],
  ["build a React Native app that reads from our existing API", "create a native iPhone app for field staff",
   "update an Android app to the latest platform version and fix crashes"],
  ["React Native", "iOS development", "Firebase", "Android development"])
A("WordPress & CMS", None,
  ["WordPress website build", "WooCommerce shop customisation", "Fix and speed up our WordPress site"],
  ["build a brochure website on WordPress with a blog and a contact form", "customise a WooCommerce shop and add a booking plugin",
   "speed up and clean a hacked WordPress site"],
  ["WordPress", "PHP", "HTML/CSS", "SEO"])
A("Graphic & Brand Design", None,
  ["Logo and brand identity", "Social media graphics pack", "Brand guidelines and marketing visuals"],
  ["design a logo and a simple brand kit for our new company", "create a set of social media templates in our brand colours",
   "design a pitch deck and a one-page flyer"],
  ["Graphic design", "Copywriting", "Video editing"])
A("Video & Motion", None,
  ["Edit YouTube videos", "Short-form video editor needed", "Explainer video with motion graphics"],
  ["edit weekly YouTube videos with captions and music", "turn long interviews into short clips for social media",
   "produce a 60-second animated explainer"],
  ["Video editing", "Graphic design", "Copywriting"])
A("Writing & Translation", None,
  ["Blog writer for a tech company", "English to Spanish translation", "SEO articles and website copy"],
  ["write four blog posts a month about our industry", "translate our app strings and help centre into Spanish",
   "rewrite our website copy and write product descriptions"],
  ["Copywriting", "SEO", "Translation"])
A("Game Development", None,
  ["Unity mobile game developer", "3D game prototype", "Game level and gameplay scripting"],
  ["build a small casual mobile game with in-app ads", "prototype a 3D puzzle game with a few levels",
   "add gameplay mechanics and polish to an existing project"],
  ["Unity", "Android development", "iOS development", "Unreal Engine"])
A("SEO & Digital Marketing", None,
  ["SEO audit and link building", "Google Ads campaign manager", "Digital marketing for a local business"],
  ["audit our website and fix the technical SEO problems", "set up and manage Google Ads campaigns for our online shop",
   "grow organic traffic with content and backlinks"],
  ["SEO", "Google Ads", "Copywriting", "Google Analytics 4"])
A("Admin & Bookkeeping", None,
  ["Bookkeeper for a small business", "Data entry from PDFs into Excel", "Virtual assistant and data entry"],
  ["reconcile our bank feeds and keep monthly books for a small company", "enter product details from supplier PDFs into a spreadsheet",
   "tidy our customer list and keep it updated each week"],
  ["Bookkeeping", "Excel", "Data entry"])
A("Blockchain & Web3", None,
  ["Smart contract developer", "NFT minting site", "Token and wallet integration"],
  ["write and test smart contracts for a token sale", "build a minting site with wallet connection",
   "audit and fix a decentralised application"],
  ["Solidity", "JavaScript", "React", "Node.js"])
A("Enterprise Software", None,
  ["Salesforce admin and automation", ".NET developer for internal tools", "SAP reporting consultant"],
  ["automate lead routing and reporting inside Salesforce", "maintain and extend a .NET line-of-business application",
   "configure finance reports in our SAP system"],
  ["Salesforce", "SAP", ".NET", "Java Spring", "Azure"])

# Adjacent-stack archetypes: in-domain flavour but built on tools none of the personas has evidence for.
ADJ = [
    dict(category="ML Model Development", titles=["TensorFlow model for mobile", "Deep learning pipeline on Spark", "Neural network in TensorFlow"],
         tasks=["train a TensorFlow model and export it for on-device inference", "process billions of rows on a Spark cluster before training a model",
                "implement a reinforcement learning agent for dynamic pricing"],
         pool=["TensorFlow", "Apache Spark", "Kubernetes", "reinforcement learning", "Python", "scikit-learn"], owner_hint="ai_ml"),
    dict(category="MLOps & Deployment", titles=["MLOps on Kubernetes", "Streaming ML with Kafka", "Azure ML deployment"],
         tasks=["run our training and serving workloads on a Kubernetes cluster", "score events from a Kafka stream in real time",
                "migrate our models to Azure and set up pipelines there"],
         pool=["Kubernetes", "Kafka", "Azure", "Docker", "model deployment", "Apache Spark"], owner_hint="ai_ml"),
    dict(category="NLP & Text Analytics", titles=["Speech-to-text pipeline", "Call transcription and analysis", "Voice assistant backend"],
         tasks=["transcribe thousands of call recordings and analyse them", "build a voice interface for our app",
                "add multilingual speech recognition to our support tool"],
         pool=["speech recognition", "TensorFlow", "NLP", "Azure", "Python"], owner_hint="ai_ml"),
    dict(category="Web App Development", titles=["Vue.js front end for our dashboard", "Angular enterprise app", "Laravel web application"],
         tasks=["build a Vue.js dashboard on top of our existing API", "extend an Angular app used by our sales team",
                "build a customer portal in Laravel with a MySQL database"],
         pool=["Vue.js", "Angular", "Laravel", "PHP", "HTML/CSS", "JavaScript"], owner_hint="fullstack"),
    dict(category="API & Backend Development", titles=["Go microservices", "Rails API maintenance", "Spring Boot backend"],
         tasks=["write a set of Go microservices for our order system", "maintain and upgrade a Ruby on Rails API",
                "build a Spring Boot service that integrates with our ERP"],
         pool=["Go", "Ruby on Rails", "Java Spring", ".NET", "Kubernetes", "PostgreSQL"], owner_hint="fullstack"),
    dict(category="Cloud & DevOps Setup", titles=["Kubernetes cluster setup", "Azure DevOps pipelines", "Cloud migration to Azure"],
         tasks=["set up a Kubernetes cluster with autoscaling and monitoring", "migrate our infrastructure to Azure",
                "run our services on Kubernetes with Helm charts and GitOps"],
         pool=["Kubernetes", "Azure", "Docker", "Go", "Bash scripting"], owner_hint="fullstack"),
    dict(category="Business Intelligence & Dashboards", titles=["Qlik Sense dashboards", "Legacy QlikView migration", "R Shiny reporting app"],
         tasks=["build Qlik Sense dashboards for our sales team", "migrate a legacy reporting portal to a modern tool",
                "build an interactive report app in R for our researchers"],
         pool=["Qlik", "R", "SQL", "dashboard design"], owner_hint="data_analyst"),
    dict(category="Statistical & Experiment Analysis", titles=["SPSS statistical analysis", "R statistical modelling", "Big data analysis with Spark"],
         tasks=["analyse research data in SPSS and write up the methods", "fit mixed-effects models in R for a clinical study",
                "analyse a very large event log on a Spark cluster"],
         pool=["SPSS", "R", "Apache Spark", "statistics", "regression analysis"], owner_hint="data_analyst"),
]

ARCHETYPES = _A

# --------------------------------------------------------------------- pricing model
# Base fixed price at medium complexity / 1-3 months / intermediate, and base hourly rate.
CATEGORY_PRICE = {
    "LLM & RAG Applications": (2200, 58), "ML Model Development": (1800, 52), "NLP & Text Analytics": (1500, 50),
    "Computer Vision & OCR": (1900, 52), "MLOps & Deployment": (1700, 55), "Forecasting & Anomaly Detection": (1500, 50),
    "Web App Development": (2400, 45), "E-commerce Development": (1600, 40), "API & Backend Development": (1500, 45),
    "Web Testing & QA": (900, 38), "Cloud & DevOps Setup": (1100, 48), "Real-time & Payments Features": (1300, 45),
    "Business Intelligence & Dashboards": (900, 32), "Data Pipelines & ETL": (1100, 36), "Statistical & Experiment Analysis": (800, 33),
    "Marketing & Web Analytics": (700, 30), "Spreadsheet Automation": (400, 24), "Survey & Research Analysis": (500, 26),
    "Mobile App Development": (2200, 42), "WordPress & CMS": (600, 22), "Graphic & Brand Design": (350, 25),
    "Video & Motion": (450, 25), "Writing & Translation": (200, 18), "Game Development": (2000, 40),
    "SEO & Digital Marketing": (400, 25), "Admin & Bookkeeping": (150, 12), "Blockchain & Web3": (2500, 55),
    "Enterprise Software": (3000, 50),
}
# Real-data calibration: data/real/price_calibration.json (from scripts/import_kaggle.py) replaces the
# hand-set bases above with bases derived from real Upwork postings and contracts where enough real data exists.
CATEGORY_PRICE_HAND = dict(CATEGORY_PRICE)  # hand-set values, kept for the comparison table
_CAL = __import__("pathlib").Path(__file__).resolve().parents[2] / "data" / "real" / "price_calibration.json"
if _CAL.exists():
    for _cat, _row in __import__("json").loads(_CAL.read_text(encoding="utf-8"))["categories"].items():
        if _cat in CATEGORY_PRICE:
            CATEGORY_PRICE[_cat] = tuple(_row["calibrated_base"])
DURATIONS = [("Less than 1 month", 0.7, 30), ("1 to 3 months", 1.0, 40), ("3 to 6 months", 1.5, 20), ("More than 6 months", 2.0, 10)]
EXPERIENCE = [("entry", 0.7, 25), ("intermediate", 1.0, 50), ("expert", 1.35, 25)]
DUR_FACTOR = {d: f for d, f, _ in DURATIONS}
EXP_FACTOR = {e: f for e, f, _ in EXPERIENCE}
MEAN_FACTOR = (sum(f * w for _, f, w in DURATIONS) / 100.0) * (sum(f * w for _, f, w in EXPERIENCE) / 100.0)
EXP_MEAN = sum(f * w for _, f, w in EXPERIENCE) / 100.0


def complexity_bucket(n_skills: int) -> str:
    return "S" if n_skills <= 3 else ("M" if n_skills <= 5 else "L")


CX_FACTOR = {"S": 0.7, "M": 1.0, "L": 1.6}


def connects_cost(budget_type: str, budget_max: float) -> int:
    if budget_type == "hourly":
        return 6
    if budget_max < 100:
        return 2
    if budget_max < 500:
        return 4
    if budget_max < 1000:
        return 6
    return 8


def archetypes_for(owner):
    return [a for a in ARCHETYPES if a["owner"] == owner]


# task-index -> index into pool of the skill that the task is specifically about (for off-domain / adjacent stacks)
_FOCUS = {
    "TensorFlow model for mobile": [0, 1, 3], "MLOps on Kubernetes": [0, 1, 2], "Speech-to-text pipeline": [0, 0, 0],
    "Vue.js front end for our dashboard": [0, 1, 2], "Go microservices": [0, 1, 2], "Kubernetes cluster setup": [0, 1, 0],
    "Qlik Sense dashboards": [0, 0, 1], "SPSS statistical analysis": [0, 1, 2],
    "React Native app with Firebase": [0, 1, 3], "Blog writer for a tech company": [0, 2, 0],
    "SEO audit and link building": [0, 1, 0], "Salesforce admin and automation": [0, 2, 1],
}
for _a in ARCHETYPES + ADJ:
    _a["focus"] = _FOCUS.get(_a["titles"][0])
