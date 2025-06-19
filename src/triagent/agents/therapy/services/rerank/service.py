import json
import os
import random
import copy
import time
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, cast
import asyncio
from triagent.config import settings
from triagent.logging import logger
from litellm import acompletion
from triagent.agents.therapy.services.rerank.prompt import group_ranking_system_prompt, group_ranking_user_prompt

class TourRankService:
    """
    Service class for document reranking using tournament-style ranking with GPT
    """
    
    def __init__(self, doc_per_group: int = 4):
        self.max_tournaments = 1
        self.doc_per_group = doc_per_group

    def sort_docs_by_relevance(self, doc_ids: List[str], relevance_scores: List[float], trials_dict: Dict[str, dict]) -> List[dict]:
        """Sort trials by relevance scores in descending order"""
        combined = list(zip(doc_ids, relevance_scores))
        sorted_combined = sorted(combined, key=lambda x: x[1], reverse=True)
        return [trials_dict[doc_id] for doc_id, _ in sorted_combined]
    
    def dcg_at_k(self, scores: List[float], k: int) -> float:
        """Calculate DCG@k"""
        scores = np.asfarray(scores)[:k]
        if scores.size:
            return np.sum(scores / np.log2(np.arange(2, scores.size + 2)))
        return 0.0
    
    def ndcg_at_k(self, scores: List[float], k: int) -> float:
        """Calculate NDCG@k"""
        dcg_max = self.dcg_at_k(sorted(scores, reverse=True), k)
        if not dcg_max:
            return 0.
        return self.dcg_at_k(scores, k) / dcg_max
    
    def group_docs(self, trials: List[dict], doc_per_group: int) -> List[List[dict]]:
        num_group = (len(trials) + doc_per_group - 1) // doc_per_group
        docs_groups = []
        for i in range(num_group):
            cur_group = []
            for j in range(doc_per_group):
                idx = j * num_group + i
                if idx < len(trials):
                    cur_group.append(trials[idx])
            if cur_group:
                docs_groups.append(cur_group)
        return docs_groups
    
    async def group_ranking(self, group_trials: List[dict], top_m: int, groups_scores: Dict[str, int], patient_info: str):
        """Process a group of documents for ranking using litellm acompletion"""
        random.shuffle(group_trials)
        
        # Prepare docs_content and N
        N = len(group_trials)
        docs_content = "\n".join([
            f"NCT ID: {trial['nct_id']}\n{json.dumps(trial, indent=2)}" for trial in group_trials
        ])
        
        # Format user prompt
        user_prompt = group_ranking_user_prompt.format(
            docs_content=docs_content,
            N=N,
            top_m=top_m,
            patient_info=patient_info,
        )
        
        messages = [
            {"role": "system", "content": group_ranking_system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await acompletion(
                model=settings.litellm_model_default,
                messages=messages,
                stream=False,
            )
            content = response.choices[0].message.content.strip()
            # Parse the NCT IDs from the response (comma-separated)
            top_trial_nct_ids = [nct_id.strip() for nct_id in content.split(",") if nct_id.strip()]
            logger.info(f"Top trial NCT IDs: {top_trial_nct_ids}")
            for nct_id in top_trial_nct_ids:
                groups_scores[nct_id] = 1
        except Exception as e:
            logger.error(f"Error during group ranking: {e}")
    
    async def tournament_ranking(self, i_tournament: int, trials: List[dict], patient_info: str) -> Dict[str, int]:
        """Process filtering through multiple tournament stages"""
        random.shuffle(trials)
        
        # Initialize the score of each doc_id (global)
        tournament_scores = {trial['nct_id']: 0 for trial in trials}
        trials_dict = {trial['nct_id']: trial for trial in trials}
        
        # Initialize ranked_list for the first stage
        ranked_list = trials
        
        # Process each stage
        doc_per_group = self.doc_per_group
        stage = 0
        while True:
            num_docs = len(ranked_list)
            if num_docs <= doc_per_group:
                # Only one group left, rank and exit
                docs_groups = [ranked_list]
                last_stage = True
            else:
                docs_groups = self.group_docs(ranked_list, doc_per_group)
                last_stage = False
            groups_scores = {}
            tasks = []

            logger.info(f"Start group ranking for stage {stage+1} with {num_docs} trials and {len(docs_groups)} groups")
            
            for group_trials in docs_groups:
                top_m = max(1, len(group_trials) // 2)
                logger.info(f"Group ranking with {len(group_trials)} trials and top_m={top_m}")
                task = self.group_ranking(group_trials, top_m, groups_scores, patient_info)
                tasks.append(task)
            
            # Wait for all group ranking tasks to complete
            await asyncio.gather(*tasks)
            
            # Combine the results
            for nct_id, score in groups_scores.items():
                tournament_scores[nct_id] += score
            
            # Get ranked list for next stage
            ranked_list = self.sort_docs_by_relevance(
                list(groups_scores.keys()),
                list(groups_scores.values()),
                trials_dict
            )
            if last_stage:
                break
            stage += 1

        # Combine the points of this tournament to global storage
        logger.info(f"Finished tournament {i_tournament+1}.")
        logger.info(f"Tournament {i_tournament+1} scores: {tournament_scores}")
        return tournament_scores

    async def rerank_trials(self, trials: List[dict], patient_info: str) -> Tuple[List[dict], Dict[str, int]]:
        
        logger.info(f"Ranking trials for patient: {patient_info}")
        
        # Run tournaments
        tasks = [self.tournament_ranking(i_tournament, trials, patient_info) for i_tournament in range(self.max_tournaments)]
        tournament_scores = await asyncio.gather(*tasks)

        # Process each tournament
        scores_list = {trial['nct_id']: 0 for trial in trials}
        trials_dict = {trial['nct_id']: trial for trial in trials}
        for i_tournament in range(len(tournament_scores)):
            tournament_score = tournament_scores[i_tournament]
            for doc_id, score in tournament_score.items():
                scores_list[doc_id] += score
            
        # Get ranked list
        ranked_list = self.sort_docs_by_relevance(
            list(scores_list.keys()), 
            list(scores_list.values()),
            trials_dict
        )
        return ranked_list, scores_list


