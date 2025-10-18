# Higgsfield API Quick Notes

## Core Patterns

- **Base URL**: `https://platform.higgsfield.ai`
- **Auth Headers**: `hf-api-key` (UUID) and `hf-secret`; both required on every call.
- **Lifecycle**: Most endpoints return a `JobSet` ID. Poll `GET /v1/job-sets/{job_set_id}` (or rely on webhooks) for completion and asset URLs. Results persist for 7 days.
- **Webhooks**: DoP and Soul generators accept an optional `webhook: {url, secret}` payload. Completed jobs POST the same JobSet payload to your URL with an `X-Webhook-Secret-Key` header.

## Generation Endpoints

- **Image → Video (DoP)** `POST /v1/image2video/dop`
  - Requires `params.model` (`dop-lite`, `dop-preview`, `dop-turbo`), prompt, `input_images[]` (each `{type, image_url}`), optional `input_images_end[]` for start/end frames, and motion presets.
  - Motion presets come from `GET /v1/motions` (fields: `id`, `name`, `description`, `preview_url`, `start_end_frame`).
- **Text → Image (Soul)** `POST /v1/text2image/soul`
  - Mandatory `prompt` and `width_and_height` (one of 13 allowed sizes).
  - Optional knobs: `enhance_prompt`, `style_id` (`GET /v1/text2image/soul-styles`), `custom_reference_id` (character ID), `quality` (`720p|1080p`), `seed`, `batch_size` (`1|4`).
- **Speech → Video (Speak v2)** `POST /v1/speak/higgsfield`
  - Needs `params.input_image`, `params.input_audio` (URLs + type), plus `prompt`, `quality` (`mid|high`), `duration` (`5|10|15s`), `enhance_prompt`, `seed` (default 42).
- **Characters (Soul ID)**
  - Create: `POST /v1/custom-references` with `name` and `input_images[]`.
  - List: `GET /v1/custom-references/list?page=&page_size=`.
  - Fetch/Delete: `GET` / `DELETE /v1/custom-references/{reference_id}`.
  - Returned IDs plug into Soul’s `custom_reference_id` field.

## Pricing Snapshot (1 USD = 16 credits)

- **DoP**: Lite 2 credits ($0.125); Turbo 6.5 credits ($0.406); Standard 9 credits ($0.563).
- **Soul**: 720p batch 1 = 1.5 credits ($0.09); 1080p batch 1 = 3 credits ($0.19). First 1000 × 1080p runs cost 1 credit (limited to 2 concurrent jobs).
- **Speak v2**: Mid quality 5/10/15 s cost 11/22/33 credits; High quality 5/10/15 s cost 18/36/54 credits.
- **Character creation**: 40 credits ($2.50).

## Operational Tips

- Cache `GET /v1/motions` and `GET /v1/text2image/soul-styles` responses locally for picker UIs.
- Validate webhook secrets before trusting payloads; the body mirrors `JobSet_Pydantic` from the OpenAPI spec.
- Failed/NSFW jobs still show in `jobs[]`; check per-job `results.min` / `results.raw` once status is `completed`.
- Changelog highlights: webhooks added Aug 28 2025; Speak v2 endpoint launched Sep 1 2025.
