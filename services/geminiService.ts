import { GoogleGenAI } from "@google/genai";
import { InterviewType } from "../types";

// Initialize the client
// The API key must be provided in the environment variable.
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });

const SYSTEM_PROMPTS: Record<InterviewType, string> = {
  [InterviewType.SCREENING]: "You are an AI interviewer conducting a screening interview. Focus on the candidate's self-introduction, background, and general situation. Be professional but welcoming. Ask one question at a time.",
  [InterviewType.BEHAVIORAL]: "You are an AI interviewer conducting a behavioral interview. Focus on soft skills, leadership, and STAR method responses. Ask situational questions. Be critical but constructive. Ask one question at a time.",
  [InterviewType.TECHNICAL]: "You are a senior technical interviewer for an AI Engineering role. Focus on Python, Machine Learning, System Design, and AIOps. Ask deep technical questions. Verify technical accuracy. Ask one question at a time.",
  [InterviewType.CUSTOMIZE]: "You are a versatile AI interviewer. Adapt to the user's specific request for personalized technical skills. Ask one question at a time."
};

export const generateInterviewResponse = async (
  history: { role: string; parts: { text: string }[] }[],
  message: string,
  type: InterviewType
): Promise<string> => {
  try {
    const modelId = 'gemini-3-flash-preview'; 
    
    // Construct the conversation history for context
    // We add the system instruction as a preamble if the history is empty or short
    let systemInstruction = SYSTEM_PROMPTS[type];

    const chat = ai.chats.create({
      model: modelId,
      config: {
        systemInstruction: systemInstruction,
        temperature: 0.7,
      },
      history: history,
    });

    const result = await chat.sendMessage({ message: message });
    return result.text || "I apologize, I didn't catch that. Could you repeat?";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "I am having trouble connecting to the interview server. Please check your API key.";
  }
};

export const analyzeResume = async (resumeText: string, jobUrl: string): Promise<string> => {
    try {
        const modelId = 'gemini-3-flash-preview';
        const prompt = `
        Please analyze the following resume against the job description found at this URL: ${jobUrl}.
        
        Resume Content:
        ${resumeText.substring(0, 5000)}... (truncated)

        Provide a structured output with:
        1. Match Score (0-100%)
        2. Job Summary
        3. Resume Summary
        4. Tailored Work Experience suggestions
        5. A brief Cover Letter draft.
        `;

        const response = await ai.models.generateContent({
            model: modelId,
            contents: prompt
        });

        return response.text || "Could not generate analysis.";

    } catch (error) {
        console.error("Gemini Analysis Error", error);
        return "Failed to analyze resume.";
    }
}

// ============================================
// Lab-specific functions (AI Skills Lab)
// ============================================

export const generateLabAIResponse = async (
  messages: { role: string; content: string }[],
  systemInstruction?: string
): Promise<string> => {
  if (!ai || !process.env.API_KEY) {
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
    
    const response = await ai.models.generateContent({
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