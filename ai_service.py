import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("focusflow.ai")

# Check for AI API keys in environment variables (Never hard-coded)
AI_API_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else ("openai" if os.getenv("OPENAI_API_KEY") else "auto"))

def is_ai_connected() -> bool:
    """Check if an external AI API key is configured."""
    return bool(AI_API_KEY and AI_API_KEY.strip())

# ===================================================================
# 1. AI Study Planner Service
# ===================================================================
async def generate_study_plan(
    subject: str,
    topics: str,
    available_time_minutes: int,
    energy_level: str,
    priority: str
) -> Dict[str, Any]:
    """
    Generate an actionable, time-blocked study plan based on student input.
    """
    if is_ai_connected():
        try:
            plan = await _call_external_ai_study_plan(subject, topics, available_time_minutes, energy_level, priority)
            if plan:
                return plan
        except Exception as e:
            logger.warning(f"External AI generation failed, falling back to mock provider: {e}")

    # Fallback to intelligent local engine
    return _generate_mock_study_plan(subject, topics, available_time_minutes, energy_level, priority)

def _generate_mock_study_plan(
    subject: str,
    topics_raw: str,
    total_minutes: int,
    energy_level: str,
    priority: str
) -> Dict[str, Any]:
    """Intelligent fallback study plan generator."""
    # Parse individual topics
    parsed_topics = [t.strip() for t in re.split(r'[,;\n]+', topics_raw) if t.strip()]
    if not parsed_topics:
        parsed_topics = [f"Core {subject} Fundamentals"]

    total_minutes = max(15, min(480, int(total_minutes)))
    energy_level = energy_level.strip() if energy_level else "Normal"
    priority = priority.strip() if priority else "Medium"

    # Energy-based allocation strategy
    energy_multiplier = {
        "Low": {"revision_ratio": 0.25, "break_mins": 5, "chunk_max": 20},
        "Normal": {"revision_ratio": 0.15, "break_mins": 5, "chunk_max": 30},
        "Good": {"revision_ratio": 0.12, "break_mins": 5, "chunk_max": 40},
        "Highly Focused": {"revision_ratio": 0.10, "break_mins": 3, "chunk_max": 50},
    }.get(energy_level, {"revision_ratio": 0.15, "break_mins": 5, "chunk_max": 30})

    # Round revision to nearest 5 minutes
    raw_rev = total_minutes * energy_multiplier["revision_ratio"]
    revision_mins = max(5, round(raw_rev / 5) * 5)
    study_mins = total_minutes - revision_mins

    num_topics = len(parsed_topics)
    # Distribute study_mins into clean 5-minute chunks across topics
    base_chunk = max(5, (study_mins // (num_topics * 5)) * 5)
    durations = [base_chunk] * num_topics
    remaining = study_mins - sum(durations)
    idx = 0
    while remaining >= 5:
        durations[idx % num_topics] += 5
        remaining -= 5
        idx += 1
    if remaining > 0:
        revision_mins += remaining

    schedule = []
    for i, topic in enumerate(parsed_topics):
        duration = durations[i]

        activity_focus = "Deep conceptual understanding & core notes"
        if energy_level == "Low":
            activity_focus = "Read summary points, flashcards & illustrative diagrams"
        elif energy_level == "Highly Focused":
            activity_focus = "Solve challenging practice problems & edge cases"

        schedule.append({
            "duration_minutes": duration,
            "duration_label": f"{duration} minutes",
            "topic": topic,
            "title": f"Study {topic}",
            "activity": activity_focus,
            "energy_target": energy_level,
            "priority": priority,
            "type": "study"
        })

    # Add quick revision at the end
    schedule.append({
        "duration_minutes": revision_mins,
        "duration_label": f"{revision_mins} minutes",
        "topic": "All Topics",
        "title": "Quick Revision & Self-Quiz",
        "activity": "Review highlighted notes, test recall, and summarize main takeaways without notes.",
        "energy_target": energy_level,
        "priority": priority,
        "type": "revision"
    })

    tips = []
    if energy_level == "Low":
        tips.append("Hydrate and eliminate background tabs; stick to short 15-minute bursts.")
        tips.append("Focus on grasping high-level intuition before memorizing formulas.")
    elif energy_level == "Highly Focused":
        tips.append("Leverage your high energy: write pseudocode or implement mini-exercises.")
        tips.append("Formulate test questions you might encounter on your BSc IT exam.")
    else:
        tips.append("Use active recall: close your notes after every section and explain it aloud.")
        tips.append("Keep a scratchpad open to jot down unfamiliar keywords.")

    return {
        "success": True,
        "provider": "FocusFlow AI Engine (Demo Mode)" if not is_ai_connected() else "Connected AI Provider",
        "subject": subject,
        "total_time_minutes": total_minutes,
        "energy_level": energy_level,
        "priority": priority,
        "summary": f"{total_minutes}-Minute Structured Study Plan for {subject}",
        "schedule": schedule,
        "tips": tips
    }

# ===================================================================
# 2. AI Explain Service
# ===================================================================
async def explain_topic(topic: str, subject: Optional[str] = None) -> Dict[str, Any]:
    """
    Explain a topic with simple explanation, important points, and a small example.
    """
    if is_ai_connected():
        try:
            res = await _call_external_ai_explain(topic, subject)
            if res:
                return res
        except Exception as e:
            logger.warning(f"External AI explanation failed, falling back to mock: {e}")

    return _generate_mock_explanation(topic, subject)

def _generate_mock_explanation(topic: str, subject: Optional[str] = None) -> Dict[str, Any]:
    """Knowledge-rich educational explanation engine."""
    clean_topic = topic.strip()
    lower_topic = clean_topic.lower()

    # Pre-crafted rich explanations for common university & BSc IT topics
    KNOWLEDGE_BASE = {
        "ipv4": {
            "title": "IPv4 (Internet Protocol Version 4)",
            "simple_explanation": "IPv4 is the foundational protocol used to identify devices on a network and route data packets. It uses a 32-bit numerical address structure, written as four decimal numbers separated by dots (e.g., 192.168.1.1).",
            "important_points": [
                "Address Length: 32 bits total (giving approximately 4.3 billion possible unique addresses).",
                "Format: 4 octets expressed in dotted-decimal notation (e.g., 172.16.254.1).",
                "Classes & CIDR: Divided into Classes A, B, C, D, and E, or managed dynamically via Classless Inter-Domain Routing (CIDR).",
                "Address Exhaustion: The rapid growth of internet devices caused IPv4 address exhaustion, prompting NAT and IPv6 adoption."
            ],
            "small_example": "Example Address Breakdown:\n192.168.1.10 /24\n• Network ID: 192.168.1.0\n• Subnet Mask: 255.255.255.0 (First 24 bits represent the network)\n• Host ID: 10 (Last 8 bits represent the specific device)"
        },
        "arp": {
            "title": "Address Resolution Protocol (ARP)",
            "simple_explanation": "ARP is a telecommunication protocol used to map a dynamic network-layer address (such as an IPv4 address) to a permanent physical machine address (such as a MAC address) on a local network.",
            "important_points": [
                "Layer Placement: Operates between the Network Layer (Layer 3) and Data Link Layer (Layer 2).",
                "Broadcast Request: When a host wants to send data to an IP, it sends an ARP Request broadcast to all hosts: 'Who has this IP? Tell me your MAC.'",
                "Unicast Reply: The target machine responds with an ARP Reply unicast: 'I have that IP, here is my MAC address.'",
                "ARP Cache: Hosts store resolved IP-to-MAC mappings in a local memory table (ARP Cache) to avoid broadcasting every time."
            ],
            "small_example": "Real-world Scenario:\nYour PC (192.168.1.5) wants to ping Gateway Router (192.168.1.1):\n1. PC checks its ARP Cache table.\n2. Not found → PC broadcasts: 'Who has 192.168.1.1? Send to 192.168.1.5'\n3. Router replies: '192.168.1.1 is at 00:1A:2B:3C:4D:5E'\n4. PC saves mapping and sends the Ethernet frame directly."
        },
        "ipv6": {
            "title": "IPv6 (Internet Protocol Version 6)",
            "simple_explanation": "IPv6 is the modern successor to IPv4, designed to overcome address exhaustion. It uses 128-bit addresses, written in hexadecimal notation separated by colons, providing virtually unlimited IP addresses for all connected devices.",
            "important_points": [
                "Address Space: 128 bits long (enabling 2^128 addresses, or ~3.4 × 10^38 unique addresses).",
                "Format: 8 groups of four hexadecimal digits (e.g., 2001:0db8:85a3:0000:0000:8a2e:0370:7334).",
                "Simplified Header: Streamlined fixed 40-byte header improves router packet processing speed.",
                "Built-in Security & Auto-configuration: Native support for IPsec and Stateless Address Autoconfiguration (SLAAC)."
            ],
            "small_example": "Address Abbreviation Example:\nOriginal: 2001:0db8:0000:0000:0000:0000:1428:57ab\nStep 1 (Remove leading zeros): 2001:db8:0:0:0:0:1428:57ab\nStep 2 (Compress consecutive zeros once with '::'): 2001:db8::1428:57ab"
        },
        "binary search tree": {
            "title": "Binary Search Tree (BST)",
            "simple_explanation": "A Binary Search Tree is a hierarchical node-based data structure where each node has at most two children. The left subtree contains only nodes with values strictly less than the node, and the right subtree contains only nodes with values strictly greater.",
            "important_points": [
                "BST Property: Left Child < Parent Node < Right Child.",
                "Search Time Complexity: Average case is O(log n). Worst case (skewed tree) is O(n).",
                "In-order Traversal: Traversing (Left, Root, Right) visits nodes in strictly sorted ascending order.",
                "Balanced Variants: AVL trees and Red-Black trees self-balance to guarantee O(log n) operations."
            ],
            "small_example": "Tree Visualization:\n      8\n     / \\\n    3   10\n   / \\\n  1   6\n\n• To search 6: Start at 8 (6 < 8, go left) → At 3 (6 > 3, go right) → Found 6 in 2 comparisons!"
        },
        "tcp 3-way handshake": {
            "title": "TCP 3-Way Handshake",
            "simple_explanation": "The 3-way handshake is the standardized mechanism TCP uses to establish a reliable, synchronized connection between a client and a server before transmitting actual data packets.",
            "important_points": [
                "Step 1 (SYN): Client sends a SYN (Synchronize) packet with an initial sequence number (ISN).",
                "Step 2 (SYN-ACK): Server replies with SYN-ACK, acknowledging the client's ISN and sending its own ISN.",
                "Step 3 (ACK): Client replies with an ACK packet acknowledging the server's sequence number.",
                "Outcome: Both sides have agreed upon initial sequence numbers and socket buffers."
            ],
            "small_example": "Handshake Sequence:\nClient ----------------------> Server : [SYN] Seq = 100\nClient <---------------------- Server : [SYN-ACK] Seq = 300, Ack = 101\nClient ----------------------> Server : [ACK] Seq = 101, Ack = 301\nConnection is now ESTABLISHED."
        }
    }

    # Match against known keywords
    for key, data in KNOWLEDGE_BASE.items():
        if key in lower_topic:
            return {
                "success": True,
                "provider": "FocusFlow AI Knowledge Engine",
                "topic": data["title"],
                "simple_explanation": data["simple_explanation"],
                "important_points": data["important_points"],
                "small_example": data["small_example"],
                "subject": subject or "Computer Science"
            }

    # Dynamic generic generator for any custom topic
    topic_capitalized = clean_topic.title()
    subj_label = f" in {subject}" if subject else ""
    return {
        "success": True,
        "provider": "FocusFlow AI Engine (Demo Mode)",
        "topic": topic_capitalized,
        "simple_explanation": (
            f"{topic_capitalized}{subj_label} is a key concept centered around organizing principles, "
            f"structured logic, and systematic execution. In computing and academic problem-solving, "
            f"it allows engineers and students to break complex processes down into predictable, verifiable components."
        ),
        "important_points": [
            f"Fundamental Role: Serves as a building block for advanced workflows in {subject or 'the field'}.",
            f"Core Mechanism: Operates by processing defined inputs through clear constraints to deliver predictable outputs.",
            "Key Trade-off: Balancing computational efficiency, memory overhead, and implementation simplicity.",
            "Exam & Interview Focus: Examiners frequently ask about practical use-cases, edge cases, and comparison with alternatives."
        ],
        "small_example": (
            f"Step-by-step Application of {topic_capitalized}:\n"
            f"1. Identify the baseline inputs and preconditions.\n"
            f"2. Apply the core algorithmic or conceptual rules of {topic_capitalized}.\n"
            f"3. Verify edge cases (null inputs, boundary conditions, or overflow).\n"
            f"4. Confirm that output matches expected theoretical specifications."
        ),
        "subject": subject or "General Studies"
    }

# ===================================================================
# 3. AI Quiz Service
# ===================================================================
async def generate_quiz(subject: str, topic: str, num_questions: int = 4) -> Dict[str, Any]:
    """
    Generate multiple-choice questions with 4 options, correct answer index, and explanation.
    """
    if is_ai_connected():
        try:
            quiz = await _call_external_ai_quiz(subject, topic, num_questions)
            if quiz:
                return quiz
        except Exception as e:
            logger.warning(f"External AI quiz generation failed, falling back to mock: {e}")

    return _generate_mock_quiz(subject, topic, num_questions)

def _generate_mock_quiz(subject: str, topic: str, num_questions: int = 4) -> Dict[str, Any]:
    """Generates an interactive, topic-accurate quiz."""
    clean_topic = topic.strip()
    lower_topic = clean_topic.lower()
    num_questions = max(1, min(10, int(num_questions)))

    # Comprehensive question banks for popular topics
    QUESTION_BANKS = {
        "ipv4": [
            {
                "question": "What is the total address length of an IPv4 address?",
                "options": ["16 bits", "32 bits", "64 bits", "128 bits"],
                "correct_answer": 1,
                "explanation": "IPv4 addresses consist of 32 bits, divided into 4 octets of 8 bits each in dotted decimal form."
            },
            {
                "question": "Which of the following is a default subnet mask for a Class C IPv4 network?",
                "options": ["255.0.0.0", "255.255.0.0", "255.255.255.0", "255.255.255.255"],
                "correct_answer": 2,
                "explanation": "Class C networks reserve the first 24 bits for the network ID, giving a default mask of 255.255.255.0 (/24)."
            },
            {
                "question": "Which IPv4 address range is designated for private local networks (RFC 1918) in Class C?",
                "options": ["10.0.0.0 to 10.255.255.255", "172.16.0.0 to 172.31.255.255", "192.168.0.0 to 192.168.255.255", "127.0.0.0 to 127.255.255.255"],
                "correct_answer": 2,
                "explanation": "192.168.0.0/16 is the standard Class C private IP range commonly used in home and campus routers."
            },
            {
                "question": "What is the primary purpose of Network Address Translation (NAT) in IPv4?",
                "options": ["To encrypt all HTTP traffic", "To allow multiple private IP devices to share a single public IP", "To assign DNS names to MAC addresses", "To convert IPv4 packets directly into IPv6 packets"],
                "correct_answer": 1,
                "explanation": "NAT helps mitigate IPv4 address exhaustion by translating many private local IP addresses into a single routable public IP."
            }
        ],
        "arp": [
            {
                "question": "What is the primary function of the Address Resolution Protocol (ARP)?",
                "options": [
                    "To map a known IPv4 address to its physical hardware MAC address",
                    "To assign dynamic IP addresses to new network clients",
                    "To route packets between different autonomous systems",
                    "To translate domain names into numerical IP addresses"
                ],
                "correct_answer": 0,
                "explanation": "ARP operates between Layers 2 and 3 to resolve a host's logical IP address to its physical Layer 2 MAC address."
            },
            {
                "question": "How is an ARP Request packet transmitted across the local area network?",
                "options": ["Unicast transmission", "Broadcast transmission (FF:FF:FF:FF:FF:FF)", "Multicast transmission", "Encrypted tunneling"],
                "correct_answer": 1,
                "explanation": "Because the sender does not yet know the recipient's MAC address, it broadcasts the ARP Request to all devices on the segment."
            },
            {
                "question": "What is an ARP Cache?",
                "options": [
                    "A disk buffer storing web pages",
                    "A temporary in-memory table storing recently resolved IP-to-MAC mappings",
                    "A firewall rule table",
                    "A DNS cache used by internet browsers"
                ],
                "correct_answer": 1,
                "explanation": "The ARP cache retains resolved IP-to-MAC mappings to eliminate the need for redundant network broadcast queries."
            },
            {
                "question": "Which network attack occurs when an attacker sends falsified ARP messages over a local network?",
                "options": ["SQL Injection", "ARP Spoofing / Poisoning", "Buffer Overflow", "Cross-Site Scripting"],
                "correct_answer": 1,
                "explanation": "ARP Spoofing allows an attacker to intercept, modify, or stop traffic by linking their MAC address with the IP of a legitimate computer or gateway."
            }
        ],
        "ipv6": [
            {
                "question": "What is the address length of an IPv6 address?",
                "options": ["32 bits", "64 bits", "128 bits", "256 bits"],
                "correct_answer": 2,
                "explanation": "IPv6 addresses are 128 bits in length, providing an enormous address space of approximately 3.4 x 10^38 addresses."
            },
            {
                "question": "How are IPv6 addresses typically represented in human-readable form?",
                "options": [
                    "4 decimal numbers separated by dots",
                    "8 groups of 4 hexadecimal digits separated by colons",
                    "6 groups of 2 octets separated by hyphens",
                    "A single 32-character binary string"
                ],
                "correct_answer": 1,
                "explanation": "IPv6 uses 8 hexadecimal blocks separated by colons (e.g., 2001:0db8:85a3:0000:0000:8a2e:0370:7334)."
            },
            {
                "question": "How many times can the double-colon ('::') abbreviation be used in a single IPv6 address?",
                "options": ["Only once", "Twice", "As many times as consecutive zeros appear", "Three times maximum"],
                "correct_answer": 0,
                "explanation": "The '::' notation can only be used once in an address to prevent ambiguity when reconstructing the full 128 bits."
            }
        ],
        "binary search tree": [
            {
                "question": "What is the average time complexity for searching a key in a balanced Binary Search Tree?",
                "options": ["O(1)", "O(log n)", "O(n)", "O(n log n)"],
                "correct_answer": 1,
                "explanation": "In a balanced BST, each comparison eliminates half the remaining nodes, giving logarithmic search time O(log n)."
            },
            {
                "question": "Which tree traversal of a Binary Search Tree produces values in strictly sorted ascending order?",
                "options": ["Pre-order (Root, Left, Right)", "In-order (Left, Root, Right)", "Post-order (Left, Right, Root)", "Level-order (Breadth-First)"],
                "correct_answer": 1,
                "explanation": "An In-order traversal visits the left subtree (smaller values), current node, then right subtree (larger values), producing sorted order."
            },
            {
                "question": "What is the worst-case search complexity in an unbalanced (skewed) Binary Search Tree?",
                "options": ["O(1)", "O(log n)", "O(n)", "O(n^2)"],
                "correct_answer": 2,
                "explanation": "When elements are inserted in already-sorted order without self-balancing, the tree degenerates into a linked list of height n, yielding O(n) search."
            }
        ]
    }

    # Check for direct match
    selected_questions = []
    for key, q_list in QUESTION_BANKS.items():
        if key in lower_topic:
            selected_questions = q_list.copy()
            break

    # If not enough questions or custom topic, dynamically synthesize plausible questions
    if len(selected_questions) < num_questions:
        needed = num_questions - len(selected_questions)
        for i in range(1, needed + 1):
            idx = len(selected_questions) + 1
            selected_questions.append({
                "question": f"In the context of {clean_topic}, which factor is most critical when evaluating system performance?",
                "options": [
                    f"A) Throughput and latency metrics under peak load for {clean_topic}",
                    "B) The physical color of the server chassis",
                    f"C) Ignoring edge cases and boundary inputs in {clean_topic}",
                    "D) Disabling protocol error checks completely"
                ],
                "correct_answer": 0,
                "explanation": f"When implementing or studying {clean_topic}, measuring throughput and latency under stress is paramount for system reliability."
            })

    # Slice to exact requested number
    final_questions = selected_questions[:num_questions]
    for idx, q in enumerate(final_questions):
        q["id"] = idx + 1

    return {
        "success": True,
        "provider": "FocusFlow AI Quiz Generator",
        "subject": subject,
        "topic": clean_topic,
        "total_questions": len(final_questions),
        "questions": final_questions
    }

# ===================================================================
# External AI Handlers (for when an API Key is supplied)
# ===================================================================
async def _call_external_ai_study_plan(subject: str, topics: str, minutes: int, energy: str, priority: str) -> Optional[Dict[str, Any]]:
    """Calls external AI provider if key configured."""
    prompt = f"""You are an expert university study coach for BSc IT students.
Create a practical, time-blocked study plan for:
Subject: {subject}
Topics: {topics}
Available Study Time: {minutes} minutes
Student Energy Level: {energy}
Priority: {priority}

Respond with valid JSON only in this format:
{{
  "summary": "Short plan title",
  "schedule": [
    {{"duration_minutes": 20, "duration_label": "20 minutes", "topic": "Topic Name", "title": "Study Topic", "activity": "Clear activity", "type": "study"}},
    {{"duration_minutes": 10, "duration_label": "10 minutes", "topic": "All", "title": "Quick Revision", "activity": "Review & self-quiz", "type": "revision"}}
  ],
  "tips": ["Tip 1", "Tip 2"]
}}"""
    res = await _call_ai_api(prompt)
    if res and "schedule" in res:
        res["success"] = True
        res["subject"] = subject
        res["total_time_minutes"] = minutes
        res["energy_level"] = energy
        res["priority"] = priority
        res["provider"] = "Live AI Provider"
        return res
    return None

async def _call_external_ai_explain(topic: str, subject: Optional[str]) -> Optional[Dict[str, Any]]:
    prompt = f"""Explain this university study topic for a BSc IT student:
Topic: {topic}
Subject: {subject or 'Computer Science'}

Respond in valid JSON only with this structure:
{{
  "topic": "{topic}",
  "simple_explanation": "2-3 sentences explaining it simply without jargon",
  "important_points": ["Point 1", "Point 2", "Point 3", "Point 4"],
  "small_example": "Concrete example, code snippet, or walkthrough"
}}"""
    res = await _call_ai_api(prompt)
    if res and "simple_explanation" in res:
        res["success"] = True
        res["subject"] = subject or "Computer Science"
        res["provider"] = "Live AI Provider"
        return res
    return None

async def _call_external_ai_quiz(subject: str, topic: str, count: int) -> Optional[Dict[str, Any]]:
    prompt = f"""Generate {count} multiple-choice quiz questions for university students on:
Subject: {subject}
Topic: {topic}

Respond with valid JSON only with this structure:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": 0,
      "explanation": "Why option A is correct"
    }}
  ]
}}"""
    res = await _call_ai_api(prompt)
    if res and "questions" in res:
        res["success"] = True
        res["subject"] = subject
        res["topic"] = topic
        res["total_questions"] = len(res["questions"])
        res["provider"] = "Live AI Provider"
        return res
    return None

async def _call_ai_api(prompt: str) -> Optional[Dict[str, Any]]:
    """Generic client calling Gemini or OpenAI depending on key format."""
    if not AI_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Check for Gemini Key
            if "gemini" in AI_PROVIDER.lower() or AI_API_KEY.startswith("AIza"):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={AI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt + "\nProvide pure JSON only, without markdown fences."}]}],
                    "generationConfig": {"temperature": 0.3}
                }
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    cleaned = re.sub(r"^```json\s*", "", raw_text)
                    cleaned = re.sub(r"```$", "", cleaned).strip()
                    return json.loads(cleaned)
            else:
                # OpenAI format
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {AI_API_KEY}"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
                r = await client.post(url, headers=headers, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    raw_text = data["choices"][0]["message"]["content"].strip()
                    cleaned = re.sub(r"^```json\s*", "", raw_text)
                    cleaned = re.sub(r"```$", "", cleaned).strip()
                    return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Error calling external AI endpoint: {e}")
    return None
