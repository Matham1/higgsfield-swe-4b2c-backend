# SWE Track Guide

## Program Overview
The SWE Track is Higgsfield's engineering sprint focused on building production-ready demos with the multimodal API stack. Teams receive 24 hours to ship a functional experience that could graduate to a real product. Speed and reliability matter more than flashy proofs of concept.

## Access & Credits
- Each team receives a $100 coupon (1,600 credits).
- Activate the coupon at `https://cloud.higgsfield.ai/promocode`, then create API credentials in `https://cloud.higgsfield.ai/api-keys`.
- Monitor credit usage and model statistics via the dashboard (`/dashboard`). Always mock API calls in local/test environments to conserve credits.

## Preferred Stack
The platform is stack-agnostic but optimized for:
- Python backends (FastAPI, Flask, Django).
- React or Next.js frontends.

## Example Build Patterns
1. **Recreate the Higgsfield platform** using official APIs.
2. **Chain multimodal endpoints** (e.g., generate an image → convert to video → add narration or style).
3. Feel free to invent novel workflows as long as they hinge on Higgsfield APIs.

## Using Nano Banana (Text-to-Image)
1. Explore the model in the playground, test prompts, and switch to cURL mode.
2. Copy the generated command; replace `hf-api-key` and `hf-secret` headers with your credentials.
3. Supply your prompt JSON, e.g.:
   ```json
   {
     "params": {
       "aspect_ratio": "4:3",
       "input_images": [],
       "prompt": "monkey"
     }
   }
   ```
4. Submit the request; the response includes a `job_set` ID. Poll `GET https://platform.higgsfield.ai/v1/job-sets/{job_set_id}` until job status is `completed` and asset URLs appear.
5. Track jobs in the Requests tab (`/models/nano-banana/requests`).

## Available Models
- **Text to Video**: Kling 2.1 Master, Minimax Hailuo 02, Seedance 1.0 Lite
- **Image to Video**: Kling 2.5 Turbo, Minimax Hailuo 02, Veo 3, Wan 2.5 Fast
- **Text to Image**: Nano Banana, Seedream 4.0
- **Speak / Audio**: Veo 3, Wan 2.5

## Submission Checklist
- Duration: 24-hour build window, teams of 2–4.
- Submit via `https://forms.gle/xv4NF9LURuKei4uM6` with:
  - Public GitHub repository
  - Deployed application (e.g., Vercel for frontend)
  - Optional Loom walkthrough (recommended)
- Deliver something stable, feature-complete, and ready for real use. Skip complex auth; focus on core features.

## Judging Criteria
Submissions are evaluated on functionality, technical depth, originality, and UX/design polish. Use the official docs for reference:
- Documentation hub: `https://docs.higgsfield.ai/`
- Job status reference: `https://docs.higgsfield.ai/api-reference/get-generation-results`
- Model catalogue: `https://docs.higgsfield.ai/models`
- Pricing: `https://docs.higgsfield.ai/pricing`
