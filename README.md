<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/drive/1LWVxPRAu7KgyqvtoHyYJ3eCBzFuuu0VW

## Run Locally

**Prerequisites:**  Node.js

### Frontend

1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in `.env.local` to your Gemini API key
3. (Optional) Set `NEXT_PUBLIC_BACKEND_URL` to your backend URL (defaults to `https://smartsccuss-career-intelligence-ai.onrender.com`)
4. Run the app:
   `npm run dev`

### Backend

The backend is deployed on Render: **https://smartsccuss-career-intelligence-ai.onrender.com**

For local backend development, see [smartsuccess-interview-backend/README.md](smartsuccess-interview-backend/README.md)
