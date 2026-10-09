"""
F1 Simgent - Pit Wall Agent RAG & Memory Subsystem
Persistent knowledge retrieval and autonomous feedback learning system.
Allows user thumbs up / thumbs down feedback to review, update, and ground
the agent's memory for improved, verified telemetry answers.
"""

import copy
import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_DIR = os.environ.get("SIMGENT_RUNTIME_DIR", os.path.join(ROOT, "data", "runtime"))
MEMORY_FILE = os.path.join(RUNTIME_DIR, "agent_memory.json")
FEEDBACK_FILE = os.path.join(RUNTIME_DIR, "agent_feedback.json")

logger = logging.getLogger("AgentMemory")

SEED_FILE = os.path.join(ROOT, "data", "seed", "agent_memory.json")
with open(SEED_FILE, encoding="utf-8") as seed_file:
    DEFAULT_MEMORIES = json.load(seed_file)


_DATA_ANSWERABLE = re.compile(
    r"\b(who won|winner|won the|who finished|finished (?:in )?(?:p\s*)?\d+|"
    r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) place|"
    r"who (?:finished|came|placed) (?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)|"
    r"runner[- ]?up|podium|pole|p[1-9]|standings|champion|championship|leader|leading|leads|"
    r"points|starting grid|qualif\w*)\b"
)


def is_data_answerable(query: str) -> bool:
    """True for factual result/standings questions the official results data answers."""
    return bool(_DATA_ANSWERABLE.search((query or "").lower()))


class AgentMemory:
    """
    RAG Memory Manager & Autonomous Feedback Learning Engine.
    Maintains persistent memory facts and user feedback evaluations.
    """

    def __init__(self, memory_file: str = MEMORY_FILE, feedback_file: str = FEEDBACK_FILE):
        self.memory_file = memory_file
        self.feedback_file = feedback_file
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w") as f:
                json.dump([], f, indent=2)

        os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
        if not os.path.exists(self.feedback_file):
            with open(self.feedback_file, "w") as f:
                json.dump([], f, indent=2)

    def load_memories(self) -> List[Dict[str, Any]]:
        try:
            with open(self.memory_file, "r") as f:
                learned = json.load(f)
            overridden = {m["id"] for m in learned}
            return learned + [copy.deepcopy(m) for m in DEFAULT_MEMORIES if m["id"] not in overridden]
        except Exception as e:
            logger.error(f"Error loading memories: {e}")
            return copy.deepcopy(DEFAULT_MEMORIES)

    def save_memories(self, memories: List[Dict[str, Any]]) -> bool:
        try:
            with open(self.memory_file, "w") as f:
                json.dump([m for m in memories if m not in DEFAULT_MEMORIES], f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving memories: {e}")
            return False

    def store(
        self,
        query: str,
        response_text: str,
        topic: Optional[str] = None,
        verified: bool = True,
        source: str = "verified_f1_ground_truth",
        a2ui_card: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Directly stores or updates a verified ground-truth memory entry.
        """
        memories = self.load_memories()
        clean_q = query.lower().strip()
        t_slug = topic or re.sub(r'[^a-z0-9]+', '_', clean_q)[:32]
        words = list(set(re.findall(r'\b[a-z0-9]{3,}\b', clean_q)))

        existing = next((m for m in memories if m.get("topic") == t_slug or clean_q in m.get("patterns", [])), None)
        if existing:
            existing["answer"] = response_text
            existing["confidence"] = 1.0
            existing["verified"] = verified
            existing["source"] = source
            if clean_q not in existing.get("patterns", []):
                existing.setdefault("patterns", []).append(clean_q)
            if a2ui_card:
                existing["a2ui_card"] = a2ui_card
            entry = existing
        else:
            entry = {
                "id": f"mem_{uuid.uuid4().hex[:8]}",
                "topic": t_slug,
                "patterns": [clean_q],
                "keywords": words,
                "answer": response_text,
                "source": source,
                "confidence": 1.0,
                "verified": verified,
            }
            if a2ui_card:
                entry["a2ui_card"] = a2ui_card
            memories.append(entry)

        self.save_memories(memories)
        logger.info("Stored memory entry")
        return entry

    def load_feedback(self) -> List[Dict[str, Any]]:
        try:
            with open(self.feedback_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading feedback: {e}")
            return []

    def save_feedback(self, feedback_list: List[Dict[str, Any]]) -> bool:
        try:
            with open(self.feedback_file, "w") as f:
                json.dump(feedback_list, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            return False

    def retrieve(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        defer_to_data: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves relevant grounded memory if query matches known high-confidence patterns.
        Supports multi-turn context resolution via conversation history.

        defer_to_data=True: return None for questions the official results data can answer
        (winners, positions, poles, standings, champions), so stored text can never
        override or go stale against the data.
        """
        if defer_to_data and is_data_answerable(query):
            return None
        q = query.lower().strip()
        q_words = set(re.findall(r'\b[a-z0-9]+\b', q))

        # Check if query contains anaphoric pronouns (e.g. "he", "his", "their", "did he")
        has_pronoun = any(w in q_words for w in ["he", "his", "him", "they", "their"]) or "did he" in q or "was he" in q

        memories = self.load_memories()
        best_match = None
        best_score = 0.0

        def _evaluate_match(search_text, search_words):
            nonlocal best_match, best_score
            for mem in memories:
                # Context driver check
                mem_driver = mem.get("driver")
                if mem_driver and context:
                    sel = context.get("selected") or context.get("driver")
                    if sel:
                        sel_l = str(sel).lower()
                        mem_drv_l = str(mem_driver).lower()
                        if mem_drv_l not in search_text and mem_drv_l[:3] not in search_text and sel_l not in mem_drv_l and mem_drv_l not in sel_l:
                            continue

                patterns = mem.get("patterns", [])
                keywords = mem.get("keywords", [])

                # 1. Exact phrase match
                for pat in patterns:
                    pat_lower = pat.lower()
                    if pat_lower == search_text or pat_lower in search_text or search_text in pat_lower:
                        score = 1.0 + (len(pat_lower) / 100.0)
                        if score > best_score:
                            best_score = score
                            best_match = mem

                # 2. Keyword density match
                if keywords:
                    match_count = sum(1 for kw in keywords if kw.lower() in search_words)
                    ratio = match_count / len(keywords)
                    if ratio >= 0.7:
                        score = 0.8 + (ratio * 0.19)
                        if score > best_score:
                            best_score = score
                            best_match = mem

        _evaluate_match(q, q_words)

        # Multi-turn resolution: if query didn't match and we have history with pronouns
        if (not best_match or best_score < 0.85) and history and has_pronoun:
            # Extract keywords from the most recent assistant or user turn
            recent_turns = [t.get("content") or t.get("text") or "" for t in history[-2:]]
            recent_text = " ".join(recent_turns).lower()
            combined_text = f"{recent_text} {q}"
            combined_words = set(re.findall(r'\b[a-z0-9]+\b', combined_text))
            _evaluate_match(combined_text, combined_words)

        if best_match and best_score >= 0.85:
            logger.info("Retrieved memory entry")
            return {
                "role": "assistant",
                "text": best_match["answer"],
                "provider": "Pit Wall Telemetry Engine (RAG Grounded)",
                "tier": "Verified Memory Bank",
                "tool": "telemetry_memory_retrieval",
                "intent": f"Grounded Recall: {best_match.get('topic', 'General Telemetry')}",
                "memory_id": best_match.get("id"),
                "confidence": best_match.get("confidence", 1.0),
                "a2ui_card": best_match.get("a2ui_card")
            }

        return None

    def record_feedback(
        self,
        query: str,
        response_text: str,
        rating: str,
        comment: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Records user feedback (thumbs up or thumbs down).
        Learning is deferred to authenticated administrator review.
        """
        feedback_list = self.load_feedback()
        fid = f"fb_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        entry = {
            "id": fid,
            "query": query,
            "response_text": response_text,
            "rating": "up" if rating.lower() in ("up", "thumbs_up", "+1") else "down",
            "comment": (comment or "").strip(),
            "context": context or {},
            "timestamp": time.time(),
            "reviewed": False,
            "learned_memory_id": None
        }

        memory_updated = False
        learned_topic = None


        feedback_list.append(entry)
        self.save_feedback(feedback_list)

        return {
            "status": "success",
            "feedback_id": fid,
            "rating": entry["rating"],
            "memory_updated": memory_updated,
            "learned_topic": learned_topic,
            "message": "Feedback recorded. Agent memory reviewed and updated." if memory_updated else "Feedback recorded successfully."
        }

    def review_single_feedback(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reviews a single negative feedback entry and extracts/learns authoritative facts.
        """
        q = entry.get("query", "").lower()
        comment = entry.get("comment", "")
        memories = self.load_memories()

        # Case 1: Championship Leaders / Standings
        if any(w in q for w in ["leader", "leading", "standings", "first place", "wdc", "wcc"]):
            year = 2026
            m_year = re.search(r'\b(202\d|19\d\d)\b', q)
            if m_year:
                year = int(m_year.group(1))

            from app.tools import race_replay
            try:
                st = race_replay.standings(year)
                d_top = st.get("drivers", [])[:4]
                c_top = st.get("constructors", [])[:4]

                if d_top:
                    leader_d = d_top[0]
                    leader_c = c_top[0] if c_top else None

                    wins_str = f" across {leader_d['wins']} race wins" if leader_d.get('wins') else ""
                    p2_str = f", with teammate {d_top[1]['driver']} in P2 ({d_top[1]['points']:.0f} pts)" if len(d_top) > 1 else ""
                    wcc_str = f" {leader_c['team']} commands the Constructors' title with {leader_c['points']:.0f} points." if leader_c else ""
                    answer = f"**{leader_d['driver']}** currently leads the {year} Drivers' World Championship with **{leader_d['points']:.0f} points** for {leader_d['team']}{wins_str}{p2_str}.{wcc_str}"


                    new_mem = {
                        "id": f"mem_{year}_championship_leaders",
                        "topic": f"{year}_championship_leaders",
                        "patterns": [
                            f"who is currently the leader of the {year} season",
                            f"who is currently leading in the {year} season",
                            f"who is leading the {year} season",
                            f"who is leading {year}",
                            f"who leads {year}",
                            f"{year} championship leader",
                            f"leader of {year}",
                            f"who is in first place {year}",
                            f"wdc leader {year}",
                            f"current leader of {year}"
                        ],
                        "keywords": ["leader", "leading", str(year), "season", "championship"],
                        "answer": answer,
                        "source": "feedback_review_reconciled",
                        "confidence": 1.0,
                        "a2ui_card": {
                            "type": "championship_card",
                            "title": f"{year} FIA World Championship Leaders",
                            "metrics": [
                                {"label": "WDC Leader", "value": leader_d['driver'], "color": "#00F5D4"},
                                {"label": "WDC Points", "value": f"{leader_d['points']} pts", "color": "#FFFFFF"},
                                {"label": "WCC Leader", "value": leader_c['team'] if leader_c else 'TBD', "color": "#27F4D2"},
                                {"label": "WCC Points", "value": f"{leader_c['points']} pts" if leader_c else '—', "color": "#FFB703"}
                            ],
                            "action": f"OPEN {year} STANDINGS",
                            "target": {
                                "action_type": "open_standings",
                                "year": year
                            }
                        }
                    }

                    # Replace or append
                    memories = [m for m in memories if m["id"] != new_mem["id"]]
                    memories.insert(0, new_mem)
                    self.save_memories(memories)
                    return {"updated": True, "memory_id": new_mem["id"], "topic": new_mem["topic"]}
            except Exception as e:
                logger.error(f"Error reviewing championship feedback: {e}")

        # Case 2: User provided comment / correction
        if comment and len(comment.strip()) >= 5:
            comment_lower = comment.lower()
            is_complaint = any(term in comment_lower for term in [
                "incorrect", "wrong", "didn't", "did not", "error", "false", "bug",
                "why is", "why did", "why doesn't", "asked about", "not working",
                "fails", "doesn't", "bad", "garbage", "slop"
            ])
            
            # If user filed a complaint, attempt autonomous telemetry fact reconciliation
            if is_complaint:
                ctx = entry.get("context", {})
                try:
                    from app.tools import race_replay
                    year = ctx.get("year", 2026)
                    round_no = ctx.get("round", 16)
                    if any(w in q for w in ["tire", "tires", "tyre", "tyres", "pit", "medium", "soft", "hard", "stint", "box"]):
                        from app.tools import race_agent
                        res = race_agent.answer_race_engineer_query(entry.get("query", ""), context=ctx)
                        if res and res.get("text") and "active for the" not in res.get("text"):
                            mem_id = f"mem_reconciled_{int(time.time())}"
                            new_mem = {
                                "id": mem_id,
                                "topic": f"reconciled_telemetry_{year}_r{round_no}",
                                "patterns": [q],
                                "keywords": [w for w in re.findall(r'\b[a-z0-9]+\b', q) if len(w) > 3],
                                "answer": res["text"],
                                "source": "autonomous_telemetry_reconciliation",
                                "confidence": 1.0,
                                "a2ui_card": res.get("a2ui_card")
                            }
                            memories = [m for m in memories if m["id"] != mem_id]
                            memories.insert(0, new_mem)
                            self.save_memories(memories)
                            return {"updated": True, "memory_id": mem_id, "topic": new_mem["topic"]}
                except Exception as err:
                    logger.error(f"Error autonomously reconciling feedback: {err}")

                logger.info("Feedback complaint logged without updating memory")
                return {"updated": False, "reason": "comment_is_meta_complaint"}

            # Genuine factual correction provided by user
            custom_id = f"mem_learned_{int(time.time())}"
            new_mem = {
                "id": custom_id,
                "topic": "user_verified_correction",
                "patterns": [q],
                "keywords": [w for w in re.findall(r'\b[a-z0-9]+\b', q) if len(w) > 3],
                "answer": f"**Pit Wall Verified Fact**:\n\n{comment.strip()}",
                "source": "user_feedback_correction",
                "confidence": 0.95,
                "a2ui_card": None
            }
            memories.insert(0, new_mem)
            self.save_memories(memories)
            return {"updated": True, "memory_id": custom_id, "topic": "user_verified_correction"}

        return {"updated": False}

    def review_all_pending_feedback(self) -> Dict[str, Any]:
        """
        Scans all unreviewed feedback and applies memory learning.
        """
        feedback_list = self.load_feedback()
        updated_count = 0
        for entry in feedback_list:
            if not entry.get("reviewed") and entry.get("rating") == "down":
                res = self.review_single_feedback(entry)
                if res.get("updated"):
                    entry["reviewed"] = True
                    entry["learned_memory_id"] = res.get("memory_id")
                    updated_count += 1
        self.save_feedback(feedback_list)
        return {
            "total_feedback": len(feedback_list),
            "memories_updated": updated_count,
            "active_memories": len(self.load_memories())
        }

    def get_stats(self) -> Dict[str, Any]:
        """Returns stats on memories and feedback ratings."""
        feedback_list = self.load_feedback()
        up_count = sum(1 for f in feedback_list if f.get("rating") == "up")
        down_count = sum(1 for f in feedback_list if f.get("rating") == "down")
        total = len(feedback_list)
        approval_rate = (up_count / total * 100.0) if total > 0 else 100.0
        return {
            "total_memories": len(self.load_memories()),
            "total_feedback_logged": total,
            "thumbs_up": up_count,
            "thumbs_down": down_count,
            "approval_rate_pct": round(approval_rate, 1),
        }


# Global singleton instance
memory_manager = AgentMemory()
