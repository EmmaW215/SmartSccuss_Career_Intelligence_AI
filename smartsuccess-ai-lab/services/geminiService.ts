import { GoogleGenAI, GenerateContentResponse } from "@google/genai";

// Initialize the API client
// Note: In a real environment, this would be process.env.API_KEY
// For this demo, we will handle the case where it's missing gracefully.
const apiKey = process.env.API_KEY || ''; 

let ai: GoogleGenAI | null = null;
if (apiKey) {
  ai = new GoogleGenAI({ apiKey });
}

export const generateAIResponse = async (
  messages: { role: string; content: string }[],
  systemInstruction?: string
): Promise<string> => {
  if (!ai) {
    // Fallback simulation if no API key is present for the demo
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve("I am a simulated AI response because no API Key was detected in the environment. In a real deployment, I would process your request using Gemini 3 Flash.");
      }, 1000);
    });
  }

  try {
    const model = 'gemini-3-flash-preview';
    
    // Convert history to prompt format suitable for generateContent
    // Since chat interfaces usually send history, we'll format it as a single context block
    // or use the chat API if maintaining state. For simplicity here, we treat it as a fresh generation.
    
    const prompt = messages[messages.length - 1].content;
    
    const response: GenerateContentResponse = await ai.models.generateContent({
      model: model,
      contents: prompt,
      config: {
        systemInstruction: systemInstruction,
      }
    });

    return response.text || "No response generated.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "Error connecting to AI service. Please try again.";
  }
};
