# Recipes

Recipes describe how to shape this template for common project types. They are
intentionally small and practical: pick the closest recipe, delete what you do
not need, and keep the backend quality gate intact.

## Available Recipes

- [API-only SaaS](api-only-saas.md)
- [Internal Admin Backend](internal-admin-backend.md)
- [Background Worker Service](background-worker-service.md)
- [Hatchet Crawler](hatchet-crawler.md)
- [AI-enabled API](ai-enabled-api.md)
- [Data Processing API](data-processing-api.md)
- [OpenRouter / OpenAI](openrouter-openai.md)
- [Stripe Payments](stripe.md)
- [File Uploads](file-upload.md)
- [Admin Dashboard](admin-dashboard.md)
- [Deployment](deployment.md)

## First Setup

```bash
make doctor
python3 scripts/create_project.py my-project ../my-project
```

After creating a project:

```bash
cd ../my-project
make api-install
cp apps/api/.env.example apps/api/.env
make api-test-up
make api-ci
```
