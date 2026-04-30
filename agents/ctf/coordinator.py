"""
CTF Team Coordinator
Coordinate team efforts in CTF competitions
"""

from typing import Dict, Any, List
from agents.ctf.workflow_manager import CTFChallenge


class CTFTeamCoordinator:
    """Coordinate team efforts in CTF competitions"""

    def __init__(self):
        self.team_members = {}
        self.challenge_assignments = {}
        self.team_communication = []
        self.shared_resources = {}

    def optimize_team_strategy(self, challenges: List[CTFChallenge], team_skills: Dict[str, List[str]]) -> Dict[str, Any]:
        """Optimize team strategy based on member skills and challenge types"""
        strategy = {
            "assignments": {},
            "priority_queue": [],
            "collaboration_opportunities": [],
            "resource_sharing": {},
            "estimated_total_score": 0,
            "time_allocation": {}
        }

        # Analyze team skills
        skill_matrix = {}
        for member, skills in team_skills.items():
            skill_matrix[member] = {
                "web": "web" in skills or "webapp" in skills,
                "crypto": "crypto" in skills or "cryptography" in skills,
                "pwn": "pwn" in skills or "binary" in skills,
                "forensics": "forensics" in skills or "investigation" in skills,
                "rev": "reverse" in skills or "reversing" in skills,
                "osint": "osint" in skills or "intelligence" in skills,
                "misc": True  # Everyone can handle misc
            }

        # Score challenges for each team member
        member_challenge_scores = {}
        for member in team_skills.keys():
            member_challenge_scores[member] = []

            for challenge in challenges:
                base_score = challenge.points
                skill_multiplier = 1.0

                if skill_matrix[member].get(challenge.category, False):
                    skill_multiplier = 1.5  # 50% bonus for skill match

                difficulty_penalty = {
                    "easy": 1.0,
                    "medium": 0.9,
                    "hard": 0.7,
                    "insane": 0.5,
                    "unknown": 0.8
                }[challenge.difficulty]

                final_score = base_score * skill_multiplier * difficulty_penalty

                member_challenge_scores[member].append({
                    "challenge": challenge,
                    "score": final_score,
                    "estimated_time": self._estimate_solve_time(challenge, skill_matrix[member])
                })

        # Assign challenges using Hungarian algorithm approximation
        assignments = self._assign_challenges_optimally(member_challenge_scores)
        strategy["assignments"] = assignments

        # Create priority queue
        all_assignments = []
        for member, challenges in assignments.items():
            for challenge_info in challenges:
                all_assignments.append({
                    "member": member,
                    "challenge": challenge_info["challenge"].name,
                    "priority": challenge_info["score"],
                    "estimated_time": challenge_info["estimated_time"]
                })

        strategy["priority_queue"] = sorted(all_assignments, key=lambda x: x["priority"], reverse=True)

        # Identify collaboration opportunities
        strategy["collaboration_opportunities"] = self._identify_collaboration_opportunities(challenges, team_skills)

        return strategy

    def _estimate_solve_time(self, challenge: CTFChallenge, member_skills: Dict[str, bool]) -> int:
        """Estimate solve time for a challenge based on member skills"""
        base_times = {
            "easy": 1800,    # 30 minutes
            "medium": 3600,  # 1 hour
            "hard": 7200,    # 2 hours
            "insane": 14400, # 4 hours
            "unknown": 5400  # 1.5 hours
        }

        base_time = base_times[challenge.difficulty]

        # Skill bonus
        if member_skills.get(challenge.category, False):
            base_time = int(base_time * 0.7)  # 30% faster with relevant skills

        return base_time

    def _assign_challenges_optimally(self, member_challenge_scores: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Assign challenges to team members optimally"""
        assignments = {member: [] for member in member_challenge_scores.keys()}
        assigned_challenges = set()

        # Simple greedy assignment (in practice, would use Hungarian algorithm)
        for _ in range(len(member_challenge_scores)):
            best_assignment = None
            best_score = -1

            for member, challenge_scores in member_challenge_scores.items():
                for challenge_info in challenge_scores:
                    challenge_name = challenge_info["challenge"].name
                    if challenge_name not in assigned_challenges:
                        if challenge_info["score"] > best_score:
                            best_score = challenge_info["score"]
                            best_assignment = (member, challenge_info)

            if best_assignment:
                member, challenge_info = best_assignment
                assignments[member].append(challenge_info)
                assigned_challenges.add(challenge_info["challenge"].name)

        return assignments

    def _identify_collaboration_opportunities(self, challenges: List[CTFChallenge], team_skills: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Identify challenges that would benefit from team collaboration"""
        collaboration_opportunities = []

        for challenge in challenges:
            if challenge.difficulty in ["hard", "insane"]:
                # High-difficulty challenges benefit from collaboration
                relevant_members = []
                for member, skills in team_skills.items():
                    if challenge.category in [skill.lower() for skill in skills]:
                        relevant_members.append(member)

                if len(relevant_members) >= 2:
                    collaboration_opportunities.append({
                        "challenge": challenge.name,
                        "recommended_team": relevant_members,
                        "reason": f"High-difficulty {challenge.category} challenge benefits from collaboration"
                    })

        return collaboration_opportunities
