import json
import logging
from typing import Dict, Any, List
import httpx
from app.config import GEMINI_API_KEY
from app.models import (
    AIPlannerRequest, AIPlannerResponse, AIScheduleItem,
    AIExplainRequest, AIExplainResponse,
    AIQuizRequest, AIQuizResponse, AIQuizQuestion
)

logger = logging.getLogger(__name__)

class AIService:
    """
    Dedicated AI Service layer for FocusFlow.
    Communicates with Google Gemini API when GEMINI_API_KEY is configured,
    or falls back smoothly to high-quality, topic-aware demo responses.
    """

    @classmethod
    async def generate_study_plan(cls, request: AIPlannerRequest) -> AIPlannerResponse:
        """Generates a structured, time-blocked study schedule."""
        if GEMINI_API_KEY:
            try:
                plan = await cls._call_gemini_planner(request)
                if plan:
                    return plan
            except Exception as e:
                logger.warning(f"Gemini API planner call failed: {e}. Falling back to smart mock.")

        return cls._generate_mock_study_plan(request)

    @classmethod
    async def explain_topic(cls, request: AIExplainRequest) -> AIExplainResponse:
        """Explains a topic in simple, student-friendly terms with points and examples."""
        if GEMINI_API_KEY:
            try:
                explanation = await cls._call_gemini_explain(request)
                if explanation:
                    return explanation
            except Exception as e:
                logger.warning(f"Gemini API explain call failed: {e}. Falling back to smart mock.")

        return cls._generate_mock_explanation(request)

    @classmethod
    async def generate_quiz(cls, request: AIQuizRequest) -> AIQuizResponse:
        """Generates multiple choice questions with 4 options, correct answer, and explanation."""
        if GEMINI_API_KEY:
            try:
                quiz = await cls._call_gemini_quiz(request)
                if quiz:
                    return quiz
            except Exception as e:
                logger.warning(f"Gemini API quiz call failed: {e}. Falling back to smart mock.")

        return cls._generate_mock_quiz(request)

    # ------------------ GEMINI API INTEGRATIONS ------------------

    @classmethod
    async def _call_gemini_planner(cls, request: AIPlannerRequest) -> AIPlannerResponse:
        prompt = f"""
You are FocusFlow's study planner assistant. Create a realistic, high-yield study schedule for a student.
Subject: {request.subject}
Topics to cover: {request.topics}
Total available time: {request.available_time} minutes
Student energy level: {request.energy_level}
Priority: {request.priority}

Respond ONLY with valid JSON in this exact structure without markdown backticks:
{{
  "subject": "{request.subject}",
  "total_minutes": {request.available_time},
  "energy_level": "{request.energy_level}",
  "strategy_summary": "Short 1-2 sentence motivating strategy for this session",
  "energy_advice": "Practical tip tailored to their {request.energy_level} energy level",
  "schedule": [
    {{
      "topic": "Topic Name",
      "duration_minutes": 25,
      "activity": "Deep dive / Practice / Problem solving",
      "tips": "Tactical advice for this block"
    }}
  ]
}}
Make sure the sum of duration_minutes roughly equals {request.available_time} minutes, reserving the final 10-15% for revision/wrap-up.
"""
        raw_json = await cls._post_to_gemini(prompt)
        data = json.loads(raw_json)
        return AIPlannerResponse(**data)

    @classmethod
    async def _call_gemini_explain(cls, request: AIExplainRequest) -> AIExplainResponse:
        prompt = f"""
You are a top-tier tutor for university and college students. Explain the topic simply and clearly.
Topic: {request.topic}
Subject Context: {request.subject or 'General Studies'}

Respond ONLY with valid JSON in this exact structure without markdown backticks:
{{
  "topic": "{request.topic}",
  "simple_explanation": "A student-friendly, crystal-clear 2-4 sentence explanation without unnecessary jargon.",
  "important_points": [
    "Key takeaway or concept rule 1",
    "Key takeaway or concept rule 2",
    "Key takeaway or concept rule 3",
    "Key takeaway or concept rule 4"
  ],
  "example": "A memorable real-world analogy or concrete code/math/system scenario.",
  "memory_tip": "A quick mnemonic or mental trigger to remember this easily during exams."
}}
"""
        raw_json = await cls._post_to_gemini(prompt)
        data = json.loads(raw_json)
        return AIExplainResponse(**data)

    @classmethod
    async def _call_gemini_quiz(cls, request: AIQuizRequest) -> AIQuizResponse:
        prompt = f"""
Generate {request.num_questions} high-quality Multiple Choice Questions (MCQs) for student revision.
Subject: {request.subject}
Topic: {request.topic}

Respond ONLY with valid JSON in this exact structure without markdown backticks:
{{
  "subject": "{request.subject}",
  "topic": "{request.topic}",
  "questions": [
    {{
      "id": 1,
      "topic_tag": "Specific subtopic or concept tag (e.g. IPv4, ARP, TCP)",
      "question": "Clear, challenging question prompt?",
      "options": [
        "A) First realistic option",
        "B) Second realistic option",
        "C) Third realistic option",
        "D) Fourth realistic option"
      ],
      "correct_answer": 0,
      "explanation": "Clear explanation of why this answer is correct and others are not."
    }}
  ]
}}
Note: correct_answer must be an integer index (0 for option A, 1 for B, 2 for C, 3 for D).
"""
        raw_json = await cls._post_to_gemini(prompt)
        data = json.loads(raw_json)
        return AIQuizResponse(**data)

    @classmethod
    async def _post_to_gemini(cls, prompt_text: str) -> str:
        # Check standard Gemini models
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json"
            }
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            res_data = response.json()
            raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean possible markdown wrapping
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            return raw_text.strip()

    # ------------------ SMART DEMO / MOCK GENERATORS ------------------

    @classmethod
    def _generate_mock_study_plan(cls, request: AIPlannerRequest) -> AIPlannerResponse:
        """Intelligent offline plan calculation that splits topics and times practically."""
        raw_topics = [t.strip() for t in request.topics.replace("\n", ",").split(",") if t.strip()]
        if not raw_topics:
            raw_topics = ["Core Concepts", "Practice Questions"]

        total_time = request.available_time
        
        # Energy advice
        energy_tips = {
            "Low": "Energy is low: Take active 5-minute pauses, drink water, and focus on review rather than tackling heavy new theory.",
            "Normal": "Solid energy level: Stick to steady 25-minute Pomodoro bursts with consistent pace.",
            "Good": "Great momentum: Attack the most challenging topic first while focus is sharp.",
            "Highly Focused": "Peak focus mode: Dive deep with minimal interruptions. Push through advanced concepts!"
        }
        energy_advice = energy_tips.get(request.energy_level, energy_tips["Normal"])

        # Time allocation
        # Reserve ~15% for revision (at least 5 min, at most 20 min)
        revision_time = max(5, min(20, round(total_time * 0.15 / 5) * 5))
        study_time = max(10, total_time - revision_time)

        num_topics = len(raw_topics)
        base_slot = study_time // num_topics
        remainder = study_time % num_topics

        schedule: List[AIScheduleItem] = []
        for i, topic in enumerate(raw_topics):
            slot_duration = base_slot + (remainder if i == 0 else 0)
            if slot_duration <= 0:
                slot_duration = 10
            
            activity = "Core Study & Notes" if i == 0 else "Analysis & Application"
            tips = f"Focus on understanding fundamental principles of {topic}." if i == 0 else f"Solve 2-3 practical problems related to {topic}."
            
            schedule.append(AIScheduleItem(
                topic=topic,
                duration_minutes=slot_duration,
                activity=activity,
                tips=tips
            ))

        # Add revision item
        schedule.append(AIScheduleItem(
            topic="Quick Revision & Self-Test",
            duration_minutes=revision_time,
            activity="Active Recall & Flash Review",
            tips="Close notes and summarize the main formulas or definitions from memory."
        ))

        strategy_summary = (
            f"Tailored {total_time}-minute plan for {request.subject} optimized for {request.energy_level.lower()} energy. "
            f"Focuses primarily on {raw_topics[0]} with a dedicated revision buffer."
        )

        return AIPlannerResponse(
            subject=request.subject,
            total_minutes=total_time,
            energy_level=request.energy_level,
            strategy_summary=strategy_summary,
            schedule=schedule,
            energy_advice=energy_advice
        )

    @classmethod
    def _generate_mock_explanation(cls, request: AIExplainRequest) -> AIExplainResponse:
        """Intelligent offline explanation generator customized to the requested topic."""
        topic_lower = request.topic.lower()
        sub = request.subject or "Computer Science / IT"

        # Topic-tailored responses for common academic and IT concepts
        if any(w in topic_lower for w in ["ipv4", "ipv6", "ip address", "network", "arp"]):
            return AIExplainResponse(
                topic=request.topic,
                simple_explanation=(
                    f"{request.topic} is a foundational networking standard that enables devices to identify each other "
                    "and exchange packets of data reliably across local networks and the global internet."
                ),
                important_points=[
                    "Provides logical hierarchical addressing so routers can direct traffic.",
                    "Divided into network portion and host portion using subnet masks.",
                    "Essential for end-to-end transport layer communication (TCP/UDP).",
                    "Crucial for routing tables, ARP resolution, and packet forwarding."
                ],
                example=(
                    "Think of an IP address like your house's postal mailing address. Just as a courier uses your postal code "
                    "and street number to deliver a package to your door, routers use the IP address to route web packets to your laptop."
                ),
                memory_tip="Mnemonic: IP = Internet Postal service (it delivers your packets to the right home address!)."
            )
        elif any(w in topic_lower for w in ["database", "sql", "normalization", "acid", "relational"]):
            return AIExplainResponse(
                topic=request.topic,
                simple_explanation=(
                    f"{request.topic} provides organized mechanisms to store, manage, and query structured data "
                    "safely, ensuring high integrity, quick access, and minimal duplication."
                ),
                important_points=[
                    "Enforces relational integrity via primary and foreign key constraints.",
                    "Guarantees ACID properties (Atomicity, Consistency, Isolation, Durability) for transactions.",
                    "Minimizes anomalies (insertion, update, deletion) through normal forms (1NF, 2NF, 3NF).",
                    "Supports declarative querying through standardized SQL statements."
                ],
                example=(
                    "Imagine a university registry: Instead of writing a student's full address and phone number on every exam paper, "
                    "the university assigns a Student ID (Primary Key) and links course enrollments to it (Foreign Key)."
                ),
                memory_tip="Remember: Tables are spreadsheets on steroids, and Keys are the glue that connects them!"
            )
        else:
            return AIExplainResponse(
                topic=request.topic,
                simple_explanation=(
                    f"{request.topic} is an essential concept in {sub}. It represents a structured approach "
                    "to solving specific problems efficiently by breaking them down into logical, reproducible steps."
                ),
                important_points=[
                    f"Core Purpose: Establishes clear rules and workflows for handling {request.topic}.",
                    "Efficiency: Balances processing speed, resource consumption, and reliability.",
                    "Modularity: Allows complex systems to be maintained and debugged in manageable units.",
                    "Industry Standard: Widely tested and adopted across software, engineering, and academic practice."
                ],
                example=(
                    f"Consider preparing a recipe: {request.topic} works like a standardized culinary recipe where "
                    "each ingredient (input) is combined in precise sequence to yield a consistent, delicious dish (desired output)."
                ),
                memory_tip=f"Key Rule: Break '{request.topic}' into: 1. Input, 2. Process, 3. Output!"
            )

    @classmethod
    def _generate_mock_quiz(cls, request: AIQuizRequest) -> AIQuizResponse:
        """Intelligent offline quiz generator with 4 options per question, correct answer, and explanation."""
        topic_lower = request.topic.lower()
        questions: List[AIQuizQuestion] = []
        n = request.num_questions

        if any(w in topic_lower for w in ["network", "ipv4", "ipv6", "arp", "tcp"]):
            all_bank = [
                AIQuizQuestion(
                    id=1,
                    topic_tag="OSI Model & Routing",
                    question=f"Which layer of the OSI model does {request.topic} primarily operate in?",
                    options=[
                        "A) Network Layer (Layer 3)",
                        "B) Data Link Layer (Layer 2)",
                        "C) Transport Layer (Layer 4)",
                        "D) Application Layer (Layer 7)"
                    ],
                    correct_answer=0,
                    explanation="IP addressing and packet routing are core functions of the OSI Network Layer (Layer 3)."
                ),
                AIQuizQuestion(
                    id=2,
                    topic_tag="ARP Protocol",
                    question="What is the primary purpose of ARP (Address Resolution Protocol)?",
                    options=[
                        "A) Encrypting web traffic between client and server",
                        "B) Resolving an IP address to a physical MAC address",
                        "C) Assigning domain names to IP addresses",
                        "D) Establishing a three-way TCP handshake"
                    ],
                    correct_answer=1,
                    explanation="ARP maps an known IPv4 address to its corresponding Layer 2 physical MAC address on a local network."
                ),
                AIQuizQuestion(
                    id=3,
                    topic_tag="IPv4 vs IPv6",
                    question="How many bits are used in an IPv4 address versus an IPv6 address?",
                    options=[
                        "A) IPv4 uses 16 bits; IPv6 uses 64 bits",
                        "B) IPv4 uses 64 bits; IPv6 uses 256 bits",
                        "C) IPv4 uses 32 bits; IPv6 uses 128 bits",
                        "D) Both use 128 bits"
                    ],
                    correct_answer=2,
                    explanation="IPv4 addresses are 32 bits long (4 octets), whereas IPv6 addresses are 128 bits long (hexadecimal format)."
                ),
                AIQuizQuestion(
                    id=4,
                    topic_tag="IPv4 Subnetting",
                    question="Which of the following is a private IPv4 address range as specified in RFC 1918?",
                    options=[
                        "A) 192.168.0.0 to 192.168.255.255",
                        "B) 8.8.8.0 to 8.8.8.255",
                        "C) 1.1.1.0 to 1.1.1.255",
                        "D) 255.255.255.0 to 255.255.255.255"
                    ],
                    correct_answer=0,
                    explanation="192.168.0.0/16 is one of the designated RFC 1918 private IPv4 ranges (along with 10.0.0.0/8 and 172.16.0.0/12)."
                ),
                AIQuizQuestion(
                    id=5,
                    topic_tag="TCP Transport",
                    question="What protocol guarantees reliable, ordered packet delivery over an IP network?",
                    options=[
                        "A) UDP",
                        "B) ICMP",
                        "C) TCP",
                        "D) DNS"
                    ],
                    correct_answer=2,
                    explanation="TCP provides connection-oriented, reliable, and sequenced delivery with flow control and retransmissions."
                )
            ]
        elif any(w in topic_lower for w in ["database", "sql", "normalization", "acid"]):
            all_bank = [
                AIQuizQuestion(
                    id=1,
                    topic_tag="Primary Keys",
                    question=f"In relational databases, what does a Primary Key ensure for {request.topic}?",
                    options=[
                        "A) That each record in the table is uniquely identifiable",
                        "B) That all values are encrypted with a hash",
                        "C) That data is backed up to a secondary server",
                        "D) That foreign keys can be null"
                    ],
                    correct_answer=0,
                    explanation="A Primary Key enforces entity integrity by uniquely identifying every single row without duplicates or nulls."
                ),
                AIQuizQuestion(
                    id=2,
                    topic_tag="ACID Transactions",
                    question="What does the 'A' stand for in the ACID properties of database transactions?",
                    options=[
                        "A) Availability",
                        "B) Atomicity",
                        "C) Authentication",
                        "D) Asynchrony"
                    ],
                    correct_answer=1,
                    explanation="Atomicity guarantees that all operations in a transaction succeed completely or none do ('all or nothing')."
                ),
                AIQuizQuestion(
                    id=3,
                    topic_tag="Database Normalization",
                    question="Which Normal Form requires eliminating transitive dependencies?",
                    options=[
                        "A) First Normal Form (1NF)",
                        "B) Second Normal Form (2NF)",
                        "C) Third Normal Form (3NF)",
                        "D) Boyce-Codd Normal Form (BCNF)"
                    ],
                    correct_answer=2,
                    explanation="3NF requires the table to be in 2NF and have no non-prime attribute transitively dependent on the candidate key."
                ),
                AIQuizQuestion(
                    id=4,
                    topic_tag="SQL Aggregations",
                    question="Which SQL clause is used to filter records after an aggregate GROUP BY operation?",
                    options=[
                        "A) WHERE",
                        "B) HAVING",
                        "C) ORDER BY",
                        "D) LIMIT"
                    ],
                    correct_answer=1,
                    explanation="HAVING filters grouped summary data, whereas WHERE filters individual rows before grouping."
                ),
                AIQuizQuestion(
                    id=5,
                    topic_tag="Relational Joins",
                    question="What is the result of an INNER JOIN between two tables?",
                    options=[
                        "A) All records from the left table and matching from the right",
                        "B) Only the records that have matching values in both tables",
                        "C) All records from both tables regardless of match",
                        "D) A Cartesian product of all rows"
                    ],
                    correct_answer=1,
                    explanation="INNER JOIN selects only rows where the specified join predicate matches in both tables."
                )
            ]
        else:
            all_bank = [
                AIQuizQuestion(
                    id=1,
                    topic_tag=f"{request.topic} Fundamentals",
                    question=f"What is the primary characteristic or objective of {request.topic}?",
                    options=[
                        f"A) Providing a structured and validated approach to {request.topic}",
                        f"B) Eliminating all computer memory usage during execution",
                        f"C) Bypassing network and operating system security checks",
                        f"D) Replacing hardware architecture with software emulators"
                    ],
                    correct_answer=0,
                    explanation=f"The primary goal of {request.topic} is providing an organized, reliable, and testable framework."
                ),
                AIQuizQuestion(
                    id=2,
                    topic_tag=f"{request.topic} Architecture",
                    question=f"When analyzing {request.topic}, why is modularity an advantage?",
                    options=[
                        "A) It makes debugging and maintenance significantly simpler",
                        "B) It prevents any other code from ever running",
                        "C) It replaces the compiler entirely",
                        "D) It increases execution time exponentially"
                    ],
                    correct_answer=0,
                    explanation="Modularity isolates components, making systems easier to read, test, debug, and scale independently."
                ),
                AIQuizQuestion(
                    id=3,
                    topic_tag="Best Practices",
                    question=f"Which best practice should a student apply when studying {request.topic}?",
                    options=[
                        "A) Memorizing code without understanding basic logic",
                        "B) Applying active recall, concept mapping, and practice questions",
                        "C) Ignoring practical lab exercises",
                        "D) Studying only five minutes before the final exam"
                    ],
                    correct_answer=1,
                    explanation="Active recall and practical application form the gold standard for long-term comprehension and retention."
                ),
                AIQuizQuestion(
                    id=4,
                    topic_tag="Trade-offs & Performance",
                    question=f"What trade-off is commonly evaluated when implementing {request.topic}?",
                    options=[
                        "A) Time complexity vs Space complexity",
                        "B) Keyboard color vs Mouse DPI",
                        "C) Screen resolution vs Audio volume",
                        "D) Font family vs CSS padding"
                    ],
                    correct_answer=0,
                    explanation="In computer science, engineering trade-offs usually balance computational speed (time) against memory consumption (space)."
                ),
                AIQuizQuestion(
                    id=5,
                    topic_tag="Verification & Testing",
                    question=f"How does a developer verify the correctness of a feature related to {request.topic}?",
                    options=[
                        "A) By running comprehensive unit, integration, and user tests",
                        "B) By guessing and pushing directly to production",
                        "C) By deleting logs and documentation",
                        "D) By restarting the computer repeatedly"
                    ],
                    correct_answer=0,
                    explanation="Automated and structured testing validates that logic fulfills requirements without unexpected regressions."
                )
            ]

        selected = all_bank[:min(n, len(all_bank))]
        return AIQuizResponse(
            subject=request.subject,
            topic=request.topic,
            questions=selected
        )
