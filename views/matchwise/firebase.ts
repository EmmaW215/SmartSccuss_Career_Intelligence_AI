import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

// Firebase config from Vite environment variables
// Set these in .env.local (local dev) or Vercel Environment Variables (production)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "YOUR_API_KEY_HERE",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "your-app.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "your-app",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "your-app.appspot.com",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "123456789",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:123456789:web:abcdef",
};

// Use a unique app name to avoid conflicts with any other Firebase instance in SmartSuccess.AI
const matchwiseApp = initializeApp(firebaseConfig, 'matchwise');
export const auth = getAuth(matchwiseApp);
