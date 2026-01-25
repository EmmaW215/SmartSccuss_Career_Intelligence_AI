import { Cpu, BrainCircuit, Code2, Network } from 'lucide-react';
import { Challenge } from './types';

export const CHALLENGES: Challenge[] = [
  {
    id: '1',
    title: 'RAG Implementation Logic',
    category: 'Architecture',
    difficulty: 'Advanced',
    icon: Cpu,
    description: 'Design a scalable Retrieval-Augmented Generation pipeline for a private dataset of 10M documents.',
    reward: 'Level 4 Badge',
    timeLimit: 60,
    
    scenario: "You are an AI Engineer at a legal tech company. Build a production-ready RAG pipeline to handle 10M+ legal documents (PDF, DOCX, TXT).",
    requirements: [
      "Document Processing Pipeline: Ingest documents from multiple formats, implement intelligent semantic chunking, and handle document hierarchy.",
      "Vector Store Architecture: Design for 10M+ documents (~50M+ chunks), support metadata filtering, and implement hybrid search (dense + sparse/BM25).",
      "Retrieval Strategy: Multi-query retrieval, re-ranking with cross-encoder, and context compression.",
      "Scalability Features: Batch ingestion, incremental updates, and query latency < 500ms at P95.",
      "Evaluation Framework: Implement metrics (MRR, NDCG, Recall@K) and track answer relevance."
    ],
    expectations: [
      { aspect: "Code Quality", expectation: "Production-ready, well-documented, type-hinted" },
      { aspect: "Architecture", expectation: "Modular, extensible, follows SOLID principles" },
      { aspect: "Performance", expectation: "Handles 10M scale with horizontal scaling design" },
      { aspect: "Testing", expectation: "Unit tests + integration tests + load tests" }
    ],
    minimumPass: [
      "MRR@10 > 0.5",
      "Recall@10 > 0.6",
      "P95 latency < 2s"
    ],
    timeEstimate: "6-8 hours",
    
    keyPoints: [
      "Chunking Strategy Design - Can they handle semantic boundaries vs naive splitting?",
      "Hybrid Search Implementation - Understanding of dense vs sparse retrieval trade-offs",
      "Scale Architecture - Sharding, caching, async processing patterns",
      "Evaluation Methodology - Do they know how to measure RAG quality?",
      "Production Mindset - Error handling, logging, monitoring hooks"
    ],
    expectedOutputs: `submission/
├── src/
│   ├── ingestion/ (document_processor.py, chunking_strategy.py)
│   ├── retrieval/ (hybrid_retriever.py, reranker.py)
│   ├── vector_store/ (store_manager.py)
│   └── evaluation/ (metrics.py)
├── tests/
├── architecture_diagram.png
└── DESIGN_DECISIONS.md`,
    qualificationCriteria: [
      { level: "Pass", criteria: "Basic RAG works, retrieves relevant docs", score: "60%" },
      { level: "Good", criteria: "Hybrid search + reranking implemented", score: "75%" },
      { level: "Excellent", criteria: "Full pipeline with evaluation, MRR > 0.7", score: "85%" },
      { level: "Outstanding", criteria: "Production-ready with scaling design, latency < 300ms", score: "95%" }
    ],

    initialFiles: [
      {
        id: 'main',
        name: 'pipeline.py',
        language: 'python',
        content: `# Implement your RAG pipeline here
import os

class RAGPipeline:
    def __init__(self):
        self.index = None
        
    def ingest(self, documents):
        # TODO: Implement chunking and embedding
        pass
        
    def query(self, prompt):
        # TODO: Implement retrieval and generation
        pass
`
      },
      {
        id: 'config',
        name: 'config.json',
        language: 'json',
        content: `{\n  "embedding_model": "text-embedding-3-small",\n  "chunk_size": 1024,\n  "overlap": 200\n}`
      }
    ]
  },
  {
    id: '2',
    title: 'Prompt Engineering Optimization',
    category: 'NLP',
    difficulty: 'Intermediate',
    icon: BrainCircuit,
    description: 'Optimize a system prompt to reduce hallucination rates in a customer support chatbot by at least 25%.',
    reward: 'NLP Specialist',
    timeLimit: 45,
    
    scenario: "You are optimizing a customer support chatbot for an e-commerce platform. The current system has a 32% hallucination rate. Your goal is to reduce this by at least 25% (to ≤24%).",
    requirements: [
      "Analyze the baseline prompt and identify weakness.",
      "Design an optimized prompt architecture.",
      "Implement guardrails and grounding strategies.",
      "Validate with the test dataset.",
      "Constraint: Response time < 2s, Budget < $0.01 per query."
    ],
    expectations: [
      { aspect: "Analysis", expectation: "Root cause analysis of hallucination patterns" },
      { aspect: "Prompt Design", expectation: "Structured, grounded, with clear constraints" },
      { aspect: "Validation", expectation: "Rigorous A/B testing methodology" },
      { aspect: "Documentation", expectation: "Clear reasoning for each optimization" }
    ],
    minimumPass: [
      "25% reduction in hallucination (32% → ≤24%) without degrading other metrics"
    ],
    timeEstimate: "3-4 hours",
    
    keyPoints: [
      "Hallucination Understanding - Do they know WHY models hallucinate?",
      "Grounding Techniques - Can they effectively use context/RAG?",
      "Constraint Engineering - 'If unsure, say so' patterns",
      "Output Formatting - JSON mode, structured responses"
    ],
    expectedOutputs: `submission/
├── analysis/ (baseline_analysis.md)
├── prompts/ (baseline_prompt.txt, optimized_prompt.txt)
├── prompt_components/ (system_instruction.txt, guardrails.txt)
├── evaluation/ (test_runner.py, results.json)
└── OPTIMIZATION_REPORT.md`,
    qualificationCriteria: [
      { level: "Pass", criteria: "Hallucination Rate ≤ 26%", score: "Base" },
      { level: "Good", criteria: "Hallucination Rate ≤ 22%, Latency ≤ 1.5s", score: "High" },
      { level: "Excellent", criteria: "Hallucination Rate ≤ 18%, Quality 3.8/5", score: "Top" }
    ],

    initialFiles: [
      {
        id: 'prompt',
        name: 'system_prompt.txt',
        language: 'text',
        content: `You are a helpful customer support agent. Answer the user's questions based on the knowledge base.`
      },
      {
        id: 'eval',
        name: 'evaluate.py',
        language: 'python',
        content: `# Test script to measure hallucination rate\ndef evaluate_prompt(prompt):\n    print("Running evaluation...")\n    return 0.85 # Current accuracy`
      }
    ]
  },
  {
    id: '3',
    title: 'Fine-Tuning Llama 3',
    category: 'Model Training',
    difficulty: 'Expert',
    icon: Code2,
    description: 'Select the optimal hyper-parameters for LoRA fine-tuning on a specific medical terminology dataset.',
    reward: 'Model Mastery',
    timeLimit: 90,
    
    scenario: "You are a Machine Learning Engineer at a healthcare AI company. Fine-tune Llama 3 8B using LoRA to improve medical terminology understanding and clinical note generation.",
    requirements: [
      "Data Preparation: Clean notes, design prompt templates, create splits.",
      "LoRA Configuration: Select optimal Rank (r), Alpha, Target modules, Dropout.",
      "Training Pipeline: Implement PEFT + Transformers, gradient checkpointing, mixed precision (bf16).",
      "Evaluation Suite: Measure Perplexity, Medical NER accuracy, and Clinical note quality."
    ],
    expectations: [
      { aspect: "Hyperparameter Selection", expectation: "Justified with ablation studies" },
      { aspect: "Training Stability", expectation: "Smooth loss curves, no divergence" },
      { aspect: "Evaluation Rigor", expectation: "Multiple metrics, not just loss" },
      { aspect: "Documentation", expectation: "Experiment tracking, reproducibility" }
    ],
    minimumPass: [
      "Perplexity improvement ≥ 20%",
      "Complete ablation study (at least 3 configurations)",
      "Justified hyperparameter choices with evidence"
    ],
    timeEstimate: "8-12 hours",
    
    keyPoints: [
      "LoRA Theory Understanding - Why these ranks? Why these modules?",
      "Medical Domain Knowledge - Handling sensitive/specialized text",
      "Training Optimization - Memory efficiency, convergence strategies",
      "Experiment Design - Ablations, hyperparameter search methodology"
    ],
    expectedOutputs: `submission/
├── data/ (data_preparation.py, prompt_templates.py)
├── training/ (lora_config.py, train.py)
├── evaluation/ (evaluate.py, medical_ner_eval.py)
├── experiments/ (ablation_results.csv)
└── EXPERIMENT_REPORT.md`,
    qualificationCriteria: [
      { level: "Pass", criteria: "Perplexity ≤ 12.0, NER F1 ≥ 0.72", score: "Base" },
      { level: "Good", criteria: "Perplexity ≤ 10.0, NER F1 ≥ 0.78", score: "High" },
      { level: "Excellent", criteria: "Perplexity ≤ 8.5, NER F1 ≥ 0.85", score: "Top" }
    ],

    initialFiles: [
      {
        id: 'train',
        name: 'train_lora.py',
        language: 'python',
        content: `from peft import LoraConfig, get_peft_model\n\n# Define LoRA Config\nconfig = LoraConfig(\n    r=8,\n    lora_alpha=32,\n    target_modules=["q_proj", "v_proj"],\n    lora_dropout=0.05,\n    bias="none",\n    task_type="CAUSAL_LM"\n)\n`
      }
    ]
  },
  {
    id: '4',
    title: 'AI Agent Orchestration',
    category: 'Agents',
    difficulty: 'Intermediate',
    icon: Network,
    description: 'Build a multi-agent system where a "Planner" delegates tasks to "Executors" with clear feedback loops.',
    reward: 'Architect Junior',
    timeLimit: 60,
    
    scenario: "Build a multi-agent system for automated code review. A 'Planner' agent analyzes PRs and delegates specific review tasks to specialized 'Executor' agents (Security, Style, Logic, Perf).",
    requirements: [
      "Planner Agent: Parse PR diff, determine executors, handle failures, synthesize report.",
      "Executor Agents: Implement Security, Style, Logic, and Performance executors.",
      "Communication Protocol: Structured messages, feedback loops, timeout/retry mechanisms.",
      "Observability: Trace interactions, log reasoning, measure latency and token usage."
    ],
    expectations: [
      { aspect: "Architecture", expectation: "Clean separation, extensible design" },
      { aspect: "Communication", expectation: "Well-defined protocols, error handling" },
      { aspect: "Parallelism", expectation: "Efficient concurrent execution" },
      { aspect: "Observability", expectation: "Full traceability of decisions" }
    ],
    minimumPass: [
      "Working Planner + 3 Executors",
      "Structured message protocol",
      "Basic error handling",
      "At least 60% issue detection on test PRs"
    ],
    timeEstimate: "4-6 hours",
    
    keyPoints: [
      "Agent Design Patterns - ReAct, function calling, tool use",
      "Orchestration Logic - Task decomposition, routing",
      "Error Handling - Timeouts, retries, fallbacks",
      "Feedback Loops - Iterative refinement, clarification requests"
    ],
    expectedOutputs: `submission/
├── agents/ (planner_agent.py, base_agent.py)
├── agents/executors/ (security_executor.py, etc.)
├── orchestration/ (message_protocol.py, task_router.py)
├── observability/ (tracer.py)
└── ARCHITECTURE.md`,
    qualificationCriteria: [
      { level: "Pass", criteria: "Issue Detection ≥ 60%", score: "Base" },
      { level: "Good", criteria: "Issue Detection ≥ 75%, False Positive ≤ 20%", score: "High" },
      { level: "Excellent", criteria: "Issue Detection ≥ 85%, Latency ≤ 15s", score: "Top" }
    ],

    initialFiles: [
      {
        id: 'planner',
        name: 'planner_agent.py',
        language: 'python',
        content: `class PlannerAgent:\n    def create_plan(self, goal):\n        # Break down goal into steps\n        pass`
      },
      {
        id: 'executor',
        name: 'executor_agent.py',
        language: 'python',
        content: `class ExecutorAgent:\n    def execute_step(self, step):\n        # Execute specific action\n        pass`
      }
    ]
  }
];

export const MOCK_RESULTS: Record<string, any> = {
  score: 92,
  level: 'Architect',
  breakdown: {
    planning: 95,
    promptEngineering: 88,
    toolOrchestration: 92,
    outcomeQuality: 90
  },
  strengths: [
    'Excellent breakdown of complex RAG architecture',
    'Robust error handling in ingestion pipeline',
    'Efficient use of vector store indexing'
  ],
  improvements: [
    'Consider adding hybrid search (keyword + semantic)',
    'Documentation could be more verbose on edge cases'
  ],
  summary: "Assessment completed with a score of 92/100. The candidate demonstrated proficiency showing advanced ability to orchestrate AI tools effectively."
};
